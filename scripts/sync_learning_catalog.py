"""Export the backend-owned curriculum for the frontend; --check detects drift."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "src/application/learning/catalog.json"
    target = root / "frontend/src/content/learning-tracks.json"
    content = source.read_text(encoding="utf-8")
    if args.check:
        if target.read_text(encoding="utf-8") != content:
            raise SystemExit("Curriculum export is stale; run scripts/sync_learning_catalog.py")
        print("Curriculum export matches canonical catalog.")
    else:
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
