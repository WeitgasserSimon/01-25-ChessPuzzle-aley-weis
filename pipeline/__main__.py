import argparse
import json
import sys

from pipeline import db


def melde(typ, **daten):
    print(json.dumps({"type": typ, **daten}, ensure_ascii=False), flush=True)


def cmd_init_db(args):
    db.init_db(args.db, force=args.force)
    melde("result", db=str(args.db), schema_version=db.SCHEMA_VERSION)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    sub = parser.add_subparsers(dest="befehl", required=True)

    p = sub.add_parser("init-db", help="leere Datenbank aus db/schema.sql anlegen")
    p.add_argument("--db", default=str(db.DEFAULT_DB))
    p.add_argument("--force", action="store_true", help="vorhandene Datenbank löschen und neu anlegen")
    p.set_defaults(func=cmd_init_db)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (FileExistsError, FileNotFoundError) as e:
        melde("error", message=str(e))
        return 1
    except Exception as e:
        melde("error", message=f"{type(e).__name__}: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
