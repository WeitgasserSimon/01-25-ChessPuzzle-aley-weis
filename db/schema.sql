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

PRAGMA user_version = 1;
