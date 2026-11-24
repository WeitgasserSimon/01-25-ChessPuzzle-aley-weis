-- Schema für positions.db, gilt für Pipeline und App (siehe docs/architektur.md).
-- Wer hier etwas ändert, erhöht user_version am Ende und sagt es dem anderen.

PRAGMA foreign_keys = ON;

-- Lokale Profile ohne Login. niveau ist eine Zahl auf der Lichess-Skala (#42).
CREATE TABLE nutzer (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    niveau        INTEGER NOT NULL DEFAULT 1200,
    niveau_quelle TEXT    NOT NULL DEFAULT 'selbsteinschaetzung'
                  CHECK (niveau_quelle IN ('rating', 'selbsteinschaetzung', 'fragebogen', 'einstufungstest')),
    erstellt_am   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Eine Stellung pro FEN. Die Analysefelder bleiben NULL, bis Stockfish die Stellung
-- angeschaut hat (#2, #19). evaluation in Bauern aus Sicht der Seite am Zug,
-- bei Matt steht stattdessen mate (positiv =  Seite am Zug setzt matt).
-- hauptvariante sind UCI-Züge mit Leerzeichen getrennt.
CREATE TABLE position (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fen            TEXT    NOT NULL UNIQUE,
    eco            TEXT,
    eroeffnung     TEXT,
    best_move      TEXT,
    evaluation     REAL,
    mate           INTEGER,
    hauptvariante  TEXT,
    analyse_tiefe  INTEGER,
    analyse_engine TEXT,
    analysiert_am  TEXT,
    schwierigkeit  INTEGER CHECK (schwierigkeit BETWEEN 1 AND 5),
    qualitaet      INTEGER CHECK (qualitaet BETWEEN 1 AND 5),
    erstellt_am    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- kategorie z. B. phase, material, bauernstruktur, motiv (Katalog in #33)
CREATE TABLE tag (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    kategorie TEXT NOT NULL,
    UNIQUE (name, kategorie)
);

CREATE TABLE position_tag (
    position_id INTEGER NOT NULL REFERENCES position(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (position_id, tag_id)
);

CREATE INDEX idx_position_eco ON position(eco);
CREATE INDEX idx_position_nicht_analysiert ON position(id) WHERE best_move IS NULL;
CREATE INDEX idx_position_tag_tag ON position_tag(tag_id, position_id);
CREATE INDEX idx_tag_kategorie ON tag(kategorie);

PRAGMA user_version = 1;
