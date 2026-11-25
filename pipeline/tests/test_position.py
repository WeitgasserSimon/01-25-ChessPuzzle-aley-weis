import sqlite3

import pytest

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def neue_position(conn, fen=START_FEN):
    return conn.execute("INSERT INTO position (fen) VALUES (?)", (fen,)).lastrowid


def neuer_tag(conn, name, kategorie):
    return conn.execute("INSERT INTO tag (name, kategorie) VALUES (?, ?)", (name, kategorie)).lastrowid


def test_position_mit_analyse(conn):
    e = conn.execute("INSERT INTO eroeffnung (eco, name) VALUES ('C20', 'King''s Pawn Game')").lastrowid
    p = conn.execute(
        """INSERT INTO position (fen, eroeffnung_id, evaluation, analyse_tiefe, analyse_engine,
                                 analysiert_am, schwierigkeit, qualitaet)
           VALUES (?, ?, -0.3, 18, 'Stockfish 17', datetime('now'), 2, 4)""",
        (E4_FEN, e),
    ).lastrowid
    conn.executemany(
        "INSERT INTO hauptvariante_zug (position_id, nr, zug) VALUES (?, ?, ?)",
        [(p, 1, "e7e5"), (p, 2, "g1f3"), (p, 3, "b8c6")],
    )

    row = conn.execute(
        """SELECT e.eco, e.name, p.evaluation, p.schwierigkeit, p.qualitaet FROM position p
           JOIN eroeffnung e ON e.id = p.eroeffnung_id"""
    ).fetchone()
    assert row == ("C20", "King's Pawn Game", -0.3, 2, 4)

    zuege = conn.execute("SELECT zug FROM hauptvariante_zug WHERE position_id = ? ORDER BY nr", (p,)).fetchall()
    assert [z for (z,) in zuege] == ["e7e5", "g1f3", "b8c6"]
    bestzug = conn.execute("SELECT zug FROM hauptvariante_zug WHERE position_id = ? AND nr = 1", (p,)).fetchone()[0]
    assert bestzug == "e7e5"


def test_hauptvariante_nr_eindeutig_und_ab_1(conn):
    p = neue_position(conn)
    conn.execute("INSERT INTO hauptvariante_zug (position_id, nr, zug) VALUES (?, 1, 'e2e4')", (p,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO hauptvariante_zug (position_id, nr, zug) VALUES (?, 1, 'd2d4')", (p,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO hauptvariante_zug (position_id, nr, zug) VALUES (?, 0, 'd2d4')", (p,))


def test_eroeffnung_eindeutig(conn):
    conn.execute("INSERT INTO eroeffnung (eco, name) VALUES ('C50', 'Italian Game')")
    conn.execute("INSERT INTO eroeffnung (eco, name) VALUES ('C50', 'Italian Game: Giuoco Pianissimo')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO eroeffnung (eco, name) VALUES ('C50', 'Italian Game')")


def test_position_eroeffnung_fremdschluessel(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO position (fen, eroeffnung_id) VALUES (?, 999)", (START_FEN,))


def test_fen_eindeutig(conn):
    neue_position(conn)
    with pytest.raises(sqlite3.IntegrityError):
        neue_position(conn)


@pytest.mark.parametrize("spalte", ["schwierigkeit", "qualitaet"])
@pytest.mark.parametrize("wert", [0, 6])
def test_werte_nur_1_bis_5(conn, spalte, wert):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO position (fen, {spalte}) VALUES (?, ?)", (START_FEN, wert))


def test_nicht_analysierte_erkennbar(conn):
    neue_position(conn, START_FEN)
    conn.execute("INSERT INTO position (fen, evaluation, analysiert_am) VALUES (?, -0.3, datetime('now'))", (E4_FEN,))
    offen = conn.execute("SELECT fen FROM position WHERE analysiert_am IS NULL").fetchall()
    assert offen == [(START_FEN,)]


def test_tag_eindeutig_je_kategorie(conn):
    neuer_tag(conn, "eroeffnung", "phase")
    neuer_tag(conn, "eroeffnung", "motiv")
    with pytest.raises(sqlite3.IntegrityError):
        neuer_tag(conn, "eroeffnung", "phase")


def test_position_tag_n_zu_m(conn):
    p1 = neue_position(conn, START_FEN)
    p2 = neue_position(conn, E4_FEN)
    t1 = neuer_tag(conn, "eroeffnung", "phase")
    t2 = neuer_tag(conn, "quiet", "motiv")
    conn.executemany(
        "INSERT INTO position_tag (position_id, tag_id) VALUES (?, ?)",
        [(p1, t1), (p2, t1), (p2, t2)],
    )
    tags_p2 = conn.execute(
        """SELECT t.name FROM tag t JOIN position_tag pt ON pt.tag_id = t.id
           WHERE pt.position_id = ? ORDER BY t.name""",
        (p2,),
    ).fetchall()
    assert tags_p2 == [("eroeffnung",), ("quiet",)]

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO position_tag (position_id, tag_id) VALUES (?, ?)", (p1, t1))


def test_position_tag_fremdschluessel(conn):
    t = neuer_tag(conn, "quiet", "motiv")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO position_tag (position_id, tag_id) VALUES (999, ?)", (t,))


def test_position_loeschen_entfernt_tags_und_hauptvariante(conn):
    p = neue_position(conn)
    t = neuer_tag(conn, "quiet", "motiv")
    conn.execute("INSERT INTO position_tag (position_id, tag_id) VALUES (?, ?)", (p, t))
    conn.execute("INSERT INTO hauptvariante_zug (position_id, nr, zug) VALUES (?, 1, 'e2e4')", (p,))
    conn.execute("DELETE FROM position WHERE id = ?", (p,))
    assert conn.execute("SELECT COUNT(*) FROM position_tag").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM hauptvariante_zug").fetchone()[0] == 0
