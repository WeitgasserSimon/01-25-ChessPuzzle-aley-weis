-- Schema für positions.db, gilt für Pipeline und App (siehe docs/architektur.md).
-- Wer hier etwas ändert, erhöht user_version am Ende und sagt es dem anderen.
-- Alle Tabellen sind in 3. Normalform: keine Listen in Spalten, nichts doppelt gespeichert.

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

-- Eröffnungen aus dem ECO-Datensatz. Ein ECO-Code hat mehrere Varianten mit eigenem Namen.
CREATE TABLE eroeffnung (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    eco  TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (eco, name)
);

-- Eine Stellung pro FEN. Die Analysefelder bleiben NULL, bis Stockfish die Stellung
-- angeschaut hat (#2, #19), analysiert_am IS NULL heißt also "noch nicht analysiert".
-- evaluation in Bauern aus Sicht der Seite am Zug, bei Matt steht stattdessen mate
-- (positiv = Seite am Zug setzt matt).
CREATE TABLE position (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fen            TEXT    NOT NULL UNIQUE,
    eroeffnung_id  INTEGER REFERENCES eroeffnung(id),
    evaluation     REAL,
    mate           INTEGER,
    analyse_tiefe  INTEGER,
    analyse_engine TEXT,
    analysiert_am  TEXT,
    schwierigkeit  INTEGER CHECK (schwierigkeit BETWEEN 1 AND 5),
    qualitaet      INTEGER CHECK (qualitaet BETWEEN 1 AND 5),
    erstellt_am    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Hauptvariante von Stockfish, ein Zug (UCI) pro Zeile. nr 1 ist der Bestzug.
CREATE TABLE hauptvariante_zug (
    position_id INTEGER NOT NULL REFERENCES position(id) ON DELETE CASCADE,
    nr          INTEGER NOT NULL CHECK (nr >= 1),
    zug         TEXT    NOT NULL,
    PRIMARY KEY (position_id, nr)
);

-- kategorie z. B. phase, material, bauernstruktur, motiv, raetsel_thema (Katalog in #33)
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

-- Trainingskarte eines Nutzers für eine Stellung. stufe 0 = neu, 1–5 = Wiederholungsstufe (#24).
CREATE TABLE karte (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nutzer_id   INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE,
    position_id INTEGER NOT NULL REFERENCES position(id),
    stufe       INTEGER NOT NULL DEFAULT 0 CHECK (stufe BETWEEN 0 AND 5),
    faellig_am  TEXT    NOT NULL DEFAULT (date('now')),
    erstellt_am TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (nutzer_id, position_id)
);

-- Jeder bestätigte Zug (#20). Der Nutzer ergibt sich über die Karte.
-- gewertet = 0 bei "Nochmal versuchen" und beim zweiten Durchgang (#46, #24).
CREATE TABLE versuch (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    karte_id  INTEGER NOT NULL REFERENCES karte(id) ON DELETE CASCADE,
    zug       TEXT    NOT NULL,
    urteil    TEXT    NOT NULL CHECK (urteil IN ('richtig', 'gut', 'fehler')),
    zeit_ms   INTEGER CHECK (zeit_ms >= 0),
    hinweise  INTEGER NOT NULL DEFAULT 0 CHECK (hinweise >= 0),
    gewertet  INTEGER NOT NULL DEFAULT 1 CHECK (gewertet IN (0, 1)),
    zeitpunkt TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Eröffnungen, die ein Nutzer spielt. quelle: selbst eingetragen oder aus eigenen Partien.
CREATE TABLE repertoire_eintrag (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nutzer_id     INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE,
    eroeffnung_id INTEGER NOT NULL REFERENCES eroeffnung(id),
    farbe         TEXT    NOT NULL CHECK (farbe IN ('weiss', 'schwarz')),
    quelle        TEXT    NOT NULL DEFAULT 'manuell' CHECK (quelle IN ('manuell', 'partien')),
    UNIQUE (nutzer_id, eroeffnung_id, farbe)
);

-- Importierte eigene Partien (#5). nutzer_farbe ist die Seite, die der Nutzer gespielt hat.
CREATE TABLE partie (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nutzer_id     INTEGER REFERENCES nutzer(id) ON DELETE CASCADE,
    nutzer_farbe  TEXT    CHECK (nutzer_farbe IN ('weiss', 'schwarz')),
    weiss         TEXT,
    schwarz       TEXT,
    ergebnis      TEXT    CHECK (ergebnis IN ('1-0', '0-1', '1/2-1/2', '*')),
    event         TEXT,
    gespielt_am   TEXT,
    quelle        TEXT,
    importiert_am TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Stellung vor Halbzug ply (0 = Startstellung) und der Zug, der dort gespielt wurde (UCI).
-- Nach dem letzten Zug ist zug NULL.
CREATE TABLE partie_position (
    partie_id   INTEGER NOT NULL REFERENCES partie(id) ON DELETE CASCADE,
    ply         INTEGER NOT NULL CHECK (ply >= 0),
    position_id INTEGER NOT NULL REFERENCES position(id),
    zug         TEXT,
    PRIMARY KEY (partie_id, ply)
);

-- Lichess-Rätsel. position ist die Stellung, die der Löser sieht, vorzug der Zug
-- des Gegners davor (zum Anzeigen). beliebtheit geht bei Lichess von -100 bis 100.
CREATE TABLE raetsel (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    lichess_id        TEXT    NOT NULL UNIQUE,
    position_id       INTEGER NOT NULL REFERENCES position(id),
    vorzug            TEXT,
    rating            INTEGER NOT NULL,
    rating_abweichung INTEGER,
    beliebtheit       INTEGER CHECK (beliebtheit BETWEEN -100 AND 100),
    anzahl_gespielt   INTEGER CHECK (anzahl_gespielt >= 0)
);

-- Lösung des Rätsels, ein Zug (UCI) pro Zeile, abwechselnd Löser und Gegner. nr 1 ist der erste Zug des Lösers.
CREATE TABLE raetsel_zug (
    raetsel_id INTEGER NOT NULL REFERENCES raetsel(id) ON DELETE CASCADE,
    nr         INTEGER NOT NULL CHECK (nr >= 1),
    zug        TEXT    NOT NULL,
    PRIMARY KEY (raetsel_id, nr)
);

-- Lichess-Themen eines Rätsels (mateIn2, fork, ...), als Tags mit kategorie 'raetsel_thema'.
CREATE TABLE raetsel_tag (
    raetsel_id INTEGER NOT NULL REFERENCES raetsel(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (raetsel_id, tag_id)
);

CREATE INDEX idx_position_eroeffnung ON position(eroeffnung_id);
CREATE INDEX idx_position_nicht_analysiert ON position(id) WHERE analysiert_am IS NULL;
CREATE INDEX idx_position_tag_tag ON position_tag(tag_id, position_id);
CREATE INDEX idx_tag_kategorie ON tag(kategorie);
CREATE INDEX idx_karte_faellig ON karte(nutzer_id, faellig_am);
CREATE INDEX idx_karte_position ON karte(position_id);
CREATE INDEX idx_versuch_karte ON versuch(karte_id);
CREATE INDEX idx_repertoire_eroeffnung ON repertoire_eintrag(eroeffnung_id);
CREATE INDEX idx_partie_nutzer ON partie(nutzer_id);
CREATE INDEX idx_partie_position_position ON partie_position(position_id);
CREATE INDEX idx_raetsel_position ON raetsel(position_id);
CREATE INDEX idx_raetsel_rating ON raetsel(rating);
CREATE INDEX idx_raetsel_tag_tag ON raetsel_tag(tag_id, raetsel_id);

PRAGMA user_version = 1;
