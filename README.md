# ChessPuzzle

Schach-Trainer mit Trainingskarten, Rätseln und Stockfish-Bewertung. ITP2-Projekt von Simon Weitgasser und Yohannes.

Die App ist in Unity (C#) geschrieben. Positionen, Tags und Rätsel werden vorher mit einer Python-Pipeline in eine SQLite-Datenbank geladen, die die App dann liest. Genauer beschrieben in [docs/architektur.md](docs/architektur.md).

## Ordner

| Ordner | Inhalt |
|---|---|
| `unity/ChessTrainer/` | Unity-Projekt. Scripts unter `Assets/Scripts/`: `UI` und `Chess` (Frontend), `Data`, `Engine`, `Training` (Backend) |
| `pipeline/` | Python: PGN- und Rätsel-Import, Tagging |
| `db/` | `schema.sql` für die Datenbank |
| `data/` | kleine Beispieldaten, große Downloads kommen nach `data/downloads/` (nicht im Repo) |
| `docs/` | Dokumentation |

## Voraussetzungen

- Unity 6000.3.24f1 (über Unity Hub installieren)
- Python 3.12
- Stockfish für Windows von https://stockfishchess.org/download/, die exe nach `unity/ChessTrainer/Assets/StreamingAssets/stockfish/` legen

## Starten

1. Repo klonen
2. Python-Umgebung einrichten:
   ```
   cd pipeline
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. In Unity Hub „Add project from disk“ und `unity/ChessTrainer` auswählen
4. Szene `Assets/Scenes/Main.unity` öffnen und Play drücken

Die Schritte zum Befüllen der Datenbank kommen dazu, sobald die Pipeline steht (#1, #2).
