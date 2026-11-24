import sqlite3

import pytest

from pipeline import db
from pipeline.__main__ import main


@pytest.fixture
def conn(tmp_path):
    pfad = tmp_path / "test.db"
    db.init_db(pfad)
    c = db.connect(pfad)
    yield c
    c.close()


def test_init_db_legt_datei_an(tmp_path):
    pfad = tmp_path / "sub" / "test.db"
    db.init_db(pfad)
    assert pfad.exists()


def test_schema_version(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_init_db_ueberschreibt_nicht_ohne_force(tmp_path):
    pfad = tmp_path / "test.db"
    db.init_db(pfad)
    with pytest.raises(FileExistsError):
        db.init_db(pfad)


def test_init_db_force_erzeugt_neu(tmp_path):
    pfad = tmp_path / "test.db"
    db.init_db(pfad)
    c = db.connect(pfad)
    c.execute("INSERT INTO nutzer (name) VALUES ('Simon')")
    c.commit()
    c.close()

    db.init_db(pfad, force=True)
    c = db.connect(pfad)
    assert c.execute("SELECT COUNT(*) FROM nutzer").fetchone()[0] == 0
    c.close()


def test_mehrere_nutzer(conn):
    conn.execute("INSERT INTO nutzer (name, niveau, niveau_quelle) VALUES ('Simon', 1500, 'rating')")
    conn.execute("INSERT INTO nutzer (name, niveau, niveau_quelle) VALUES ('Yohannes', 1100, 'fragebogen')")
    rows = conn.execute("SELECT name, niveau, niveau_quelle FROM nutzer ORDER BY id").fetchall()
    assert rows == [("Simon", 1500, "rating"), ("Yohannes", 1100, "fragebogen")]


def test_nutzer_standardwerte(conn):
    conn.execute("INSERT INTO nutzer (name) VALUES ('Simon')")
    niveau, quelle, erstellt = conn.execute("SELECT niveau, niveau_quelle, erstellt_am FROM nutzer").fetchone()
    assert niveau == 1200
    assert quelle == "selbsteinschaetzung"
    assert erstellt is not None


def test_nutzer_name_eindeutig(conn):
    conn.execute("INSERT INTO nutzer (name) VALUES ('Simon')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO nutzer (name) VALUES ('Simon')")


def test_niveau_quelle_nur_erlaubte_werte(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO nutzer (name, niveau_quelle) VALUES ('Simon', 'geraten')")


def test_cli_init_db(tmp_path, capsys):
    pfad = tmp_path / "cli.db"
    assert main(["init-db", "--db", str(pfad)]) == 0
    assert '"type": "result"' in capsys.readouterr().out

    assert main(["init-db", "--db", str(pfad)]) == 1
    assert '"type": "error"' in capsys.readouterr().out

    assert main(["init-db", "--db", str(pfad), "--force"]) == 0
