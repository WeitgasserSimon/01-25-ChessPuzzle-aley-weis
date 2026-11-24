import sqlite3

import pytest

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


@pytest.fixture
def ids(conn):
    nutzer = conn.execute("INSERT INTO nutzer (name) VALUES ('Simon')").lastrowid
    position = conn.execute("INSERT INTO position (fen) VALUES (?)", (START_FEN,)).lastrowid
    return nutzer, position


def neue_karte(conn, nutzer, position):
    return conn.execute(
        "INSERT INTO karte (nutzer_id, position_id) VALUES (?, ?)", (nutzer, position)
    ).lastrowid


def test_karte_standardwerte(conn, ids):
    k = neue_karte(conn, *ids)
    stufe, faellig = conn.execute("SELECT stufe, faellig_am FROM karte WHERE id = ?", (k,)).fetchone()
    assert stufe == 0
    assert faellig == conn.execute("SELECT date('now')").fetchone()[0]


@pytest.mark.parametrize("stufe", [-1, 6])
def test_karte_stufe_nur_0_bis_5(conn, ids, stufe):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO karte (nutzer_id, position_id, stufe) VALUES (?, ?, ?)", (*ids, stufe))


def test_karte_einmal_pro_nutzer_und_position(conn, ids):
    neue_karte(conn, *ids)
    with pytest.raises(sqlite3.IntegrityError):
        neue_karte(conn, *ids)

    anderer = conn.execute("INSERT INTO nutzer (name) VALUES ('Yohannes')").lastrowid
    neue_karte(conn, anderer, ids[1])


def test_karte_braucht_nutzer_und_position(conn, ids):
    with pytest.raises(sqlite3.IntegrityError):
        neue_karte(conn, 999, ids[1])
    with pytest.raises(sqlite3.IntegrityError):
        neue_karte(conn, ids[0], 999)


def test_versuch_speichern(conn, ids):
    k = neue_karte(conn, *ids)
    conn.execute(
        "INSERT INTO versuch (karte_id, zug, urteil, zeit_ms, hinweise) VALUES (?, 'e2e4', 'richtig', 4200, 1)",
        (k,),
    )
    conn.execute(
        "INSERT INTO versuch (karte_id, zug, urteil, gewertet) VALUES (?, 'd2d4', 'gut', 0)",
        (k,),
    )
    rows = conn.execute("SELECT zug, urteil, zeit_ms, hinweise, gewertet FROM versuch ORDER BY id").fetchall()
    assert rows == [("e2e4", "richtig", 4200, 1, 1), ("d2d4", "gut", None, 0, 0)]


@pytest.mark.parametrize(
    "spalte, wert",
    [("urteil", "super"), ("hinweise", -1), ("gewertet", 2), ("zeit_ms", -5)],
)
def test_versuch_ungueltige_werte(conn, ids, spalte, wert):
    k = neue_karte(conn, *ids)
    werte = {"karte_id": k, "zug": "e2e4", "urteil": "richtig", spalte: wert}
    spalten = ", ".join(werte)
    platzhalter = ", ".join("?" * len(werte))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO versuch ({spalten}) VALUES ({platzhalter})", tuple(werte.values()))


def test_versuch_braucht_karte(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO versuch (karte_id, zug, urteil) VALUES (999, 'e2e4', 'richtig')")


def test_versuche_gehoeren_zum_nutzer(conn, ids):
    k = neue_karte(conn, *ids)
    conn.execute("INSERT INTO versuch (karte_id, zug, urteil) VALUES (?, 'e2e4', 'richtig')", (k,))
    nutzer = conn.execute(
        "SELECT k.nutzer_id FROM versuch v JOIN karte k ON k.id = v.karte_id"
    ).fetchone()[0]
    assert nutzer == ids[0]


def test_repertoire_eintrag(conn, ids):
    conn.execute(
        "INSERT INTO repertoire_eintrag (nutzer_id, farbe, eco, eroeffnung) VALUES (?, 'weiss', 'C50', 'Italian Game')",
        (ids[0],),
    )
    assert conn.execute("SELECT farbe, eco, quelle FROM repertoire_eintrag").fetchone() == ("weiss", "C50", "manuell")


def test_repertoire_braucht_eco_oder_name(conn, ids):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO repertoire_eintrag (nutzer_id, farbe) VALUES (?, 'weiss')", (ids[0],))


def test_repertoire_farbe(conn, ids):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO repertoire_eintrag (nutzer_id, farbe, eco) VALUES (?, 'rot', 'C50')", (ids[0],))


def test_nutzer_loeschen_loescht_lernfortschritt(conn, ids):
    k = neue_karte(conn, *ids)
    conn.execute("INSERT INTO versuch (karte_id, zug, urteil) VALUES (?, 'e2e4', 'richtig')", (k,))
    conn.execute("INSERT INTO repertoire_eintrag (nutzer_id, farbe, eco) VALUES (?, 'weiss', 'C50')", (ids[0],))

    conn.execute("DELETE FROM nutzer WHERE id = ?", (ids[0],))
    for tabelle in ("karte", "versuch", "repertoire_eintrag"):
        assert conn.execute(f"SELECT COUNT(*) FROM {tabelle}").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position").fetchone()[0] == 1
