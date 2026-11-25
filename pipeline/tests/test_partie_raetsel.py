import sqlite3

import pytest

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def neue_position(conn, fen):
    return conn.execute("INSERT INTO position (fen) VALUES (?)", (fen,)).lastrowid


def neue_partie(conn, nutzer=None):
    return conn.execute(
        """INSERT INTO partie (nutzer_id, nutzer_farbe, weiss, schwarz, ergebnis, quelle)
           VALUES (?, 'weiss', 'Simon', 'Yohannes', '1-0', 'test.pgn')""",
        (nutzer,),
    ).lastrowid


def neues_raetsel(conn, position, lichess_id="00008", **werte):
    daten = {"lichess_id": lichess_id, "position_id": position, "rating": 1800}
    daten.update(werte)
    spalten = ", ".join(daten)
    platzhalter = ", ".join("?" * len(daten))
    return conn.execute(f"INSERT INTO raetsel ({spalten}) VALUES ({platzhalter})", tuple(daten.values())).lastrowid


def test_partie_mit_positionen(conn):
    nutzer = conn.execute("INSERT INTO nutzer (name) VALUES ('Simon')").lastrowid
    p0 = neue_position(conn, START_FEN)
    p1 = neue_position(conn, E4_FEN)
    partie = neue_partie(conn, nutzer)
    conn.executemany(
        "INSERT INTO partie_position (partie_id, ply, position_id, zug) VALUES (?, ?, ?, ?)",
        [(partie, 0, p0, "e2e4"), (partie, 1, p1, None)],
    )
    rows = conn.execute(
        """SELECT pp.ply, p.fen, pp.zug FROM partie_position pp
           JOIN position p ON p.id = pp.position_id
           WHERE pp.partie_id = ? ORDER BY pp.ply""",
        (partie,),
    ).fetchall()
    assert rows == [(0, START_FEN, "e2e4"), (1, E4_FEN, None)]


def test_partie_ohne_nutzer_erlaubt(conn):
    neue_partie(conn, None)


def test_partie_ergebnis_pruefen(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO partie (ergebnis) VALUES ('2-0')")


def test_gleiche_stellung_in_mehreren_partien(conn):
    p0 = neue_position(conn, START_FEN)
    a = neue_partie(conn)
    b = neue_partie(conn)
    conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, ?)", (a, p0))
    conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, ?)", (b, p0))
    assert conn.execute("SELECT COUNT(*) FROM position").fetchone()[0] == 1


def test_ply_pro_partie_eindeutig(conn):
    p0 = neue_position(conn, START_FEN)
    a = neue_partie(conn)
    conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, ?)", (a, p0))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, ?)", (a, p0))


def test_partie_position_fremdschluessel(conn):
    p0 = neue_position(conn, START_FEN)
    a = neue_partie(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (999, 0, ?)", (p0,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, 999)", (a,))


def test_partie_loeschen_behaelt_positionen(conn):
    p0 = neue_position(conn, START_FEN)
    a = neue_partie(conn)
    conn.execute("INSERT INTO partie_position (partie_id, ply, position_id) VALUES (?, 0, ?)", (a, p0))
    conn.execute("DELETE FROM partie WHERE id = ?", (a,))
    assert conn.execute("SELECT COUNT(*) FROM partie_position").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position").fetchone()[0] == 1


def test_raetsel_speichern(conn):
    p = neue_position(conn, E4_FEN)
    r = neues_raetsel(conn, p, vorzug="e2e4", beliebtheit=94, rating_abweichung=75, anzahl_gespielt=600)
    conn.executemany(
        "INSERT INTO raetsel_zug (raetsel_id, nr, zug) VALUES (?, ?, ?)",
        [(r, 1, "f2g3"), (r, 2, "e6e7"), (r, 3, "b2b1")],
    )
    for thema in ("mate", "mateIn2"):
        t = conn.execute("INSERT INTO tag (name, kategorie) VALUES (?, 'raetsel_thema')", (thema,)).lastrowid
        conn.execute("INSERT INTO raetsel_tag (raetsel_id, tag_id) VALUES (?, ?)", (r, t))

    assert conn.execute("SELECT rating, beliebtheit, vorzug FROM raetsel").fetchone() == (1800, 94, "e2e4")
    loesung = conn.execute("SELECT zug FROM raetsel_zug WHERE raetsel_id = ? ORDER BY nr", (r,)).fetchall()
    assert [z for (z,) in loesung] == ["f2g3", "e6e7", "b2b1"]
    themen = conn.execute(
        """SELECT t.name FROM raetsel_tag rt JOIN tag t ON t.id = rt.tag_id
           WHERE rt.raetsel_id = ? ORDER BY t.name""",
        (r,),
    ).fetchall()
    assert themen == [("mate",), ("mateIn2",)]


def test_raetsel_zug_nr_eindeutig(conn):
    r = neues_raetsel(conn, neue_position(conn, E4_FEN))
    conn.execute("INSERT INTO raetsel_zug (raetsel_id, nr, zug) VALUES (?, 1, 'f2g3')", (r,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO raetsel_zug (raetsel_id, nr, zug) VALUES (?, 1, 'e6e7')", (r,))


def test_raetsel_loeschen_loescht_loesung_und_themen(conn):
    r = neues_raetsel(conn, neue_position(conn, E4_FEN))
    t = conn.execute("INSERT INTO tag (name, kategorie) VALUES ('fork', 'raetsel_thema')").lastrowid
    conn.execute("INSERT INTO raetsel_zug (raetsel_id, nr, zug) VALUES (?, 1, 'f2g3')", (r,))
    conn.execute("INSERT INTO raetsel_tag (raetsel_id, tag_id) VALUES (?, ?)", (r, t))
    conn.execute("DELETE FROM raetsel WHERE id = ?", (r,))
    assert conn.execute("SELECT COUNT(*) FROM raetsel_zug").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM raetsel_tag").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM tag").fetchone()[0] == 1


def test_raetsel_lichess_id_eindeutig(conn):
    p = neue_position(conn, E4_FEN)
    neues_raetsel(conn, p)
    with pytest.raises(sqlite3.IntegrityError):
        neues_raetsel(conn, p)
    neues_raetsel(conn, p, lichess_id="0000D")


@pytest.mark.parametrize("wert", [-101, 101])
def test_raetsel_beliebtheit_bereich(conn, wert):
    p = neue_position(conn, E4_FEN)
    with pytest.raises(sqlite3.IntegrityError):
        neues_raetsel(conn, p, beliebtheit=wert)


def test_raetsel_braucht_position(conn):
    with pytest.raises(sqlite3.IntegrityError):
        neues_raetsel(conn, 999)


def test_alle_tabellen_da(conn):
    tabellen = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {
        "nutzer", "eroeffnung", "position", "hauptvariante_zug", "tag", "position_tag",
        "karte", "versuch", "repertoire_eintrag", "partie", "partie_position",
        "raetsel", "raetsel_zug", "raetsel_tag",
    } <= tabellen
