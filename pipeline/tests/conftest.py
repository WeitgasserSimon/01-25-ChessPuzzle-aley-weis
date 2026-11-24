import pytest

from pipeline import db


@pytest.fixture
def conn(tmp_path):
    pfad = tmp_path / "test.db"
    db.init_db(pfad)
    c = db.connect(pfad)
    yield c
    c.close()
