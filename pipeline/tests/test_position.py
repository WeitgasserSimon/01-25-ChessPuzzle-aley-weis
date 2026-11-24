import sqlite3

import pytest

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def neue_position(conn, fen=START_FEN):
    return conn.execute("INSERT INTO position (fen) VALUES (?)", (fen,)).lastrowid


def neuer_tag(conn, name, kategorie):
    return conn.execute("INSERT INTO tag (name, kategorie) VALUES (?, ?)", (name, kategorie)).lastrowid


def test_position_mit_analyse(conn):
    conn.execute(
        """INSERT INTO position (fen, eco, eroeffnung, best_move, evaluation, hauptvariante,
                                 analyse_tiefe, analyse_engine, schwierigkeit, qualitaet)
           VALUES (?, 'C20', 'King''s Pawn Game', 'e7e5', -0.3, 'e7e5 g1f3 b8c6', 18, 'Stockfish 17', 2, 4)""",
        (E4_FEN,),
    )
    row = conn.execute("SELECT best_move, evaluation, hauptvariante, schwierigkeit, qualitaet FROM position").fetchone()
    assert row == ("e7e5", -0.3, "e7e5 g1f3 b8c6", 2, 4)


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
    conn.execute("INSERT INTO position (fen, best_move, evaluation) VALUES (?, 'e7e5', -0.3)", (E4_FEN,))
    offen = conn.execute("SELECT fen FROM position WHERE best_move IS NULL").fetchall()
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


def test_position_loeschen_entfernt_tags(conn):
    p = neue_position(conn)
    t = neuer_tag(conn, "quiet", "motiv")
    conn.execute("INSERT INTO position_tag (position_id, tag_id) VALUES (?, ?)", (p, t))
    conn.execute("DELETE FROM position WHERE id = ?", (p,))
    assert conn.execute("SELECT COUNT(*) FROM position_tag").fetchone()[0] == 0
