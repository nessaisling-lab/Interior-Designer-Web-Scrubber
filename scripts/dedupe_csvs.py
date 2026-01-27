"""
Deduplicate CSV files in output/ by designer name (case-insensitive).
Keeps the first occurrence of each name per file.
"""
import csv
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def dedupe_file(path: Path) -> tuple[int, int]:
    """Remove duplicate rows by 'name'. Returns (original_count, deduped_count)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    original = len(rows)
    if "name" not in fieldnames or original == 0:
        return (original, original)
    seen = set()
    unique = []
    for row in rows:
        key = (row.get("name") or "").strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(row)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(unique)
    return (original, len(unique))


def main():
    if not OUTPUT_DIR.exists():
        print(f"Output dir not found: {OUTPUT_DIR}")
        sys.exit(1)
    total_removed = 0
    for path in sorted(OUTPUT_DIR.glob("*.csv")):
        orig, after = dedupe_file(path)
        removed = orig - after
        if removed > 0:
            print(f"{path.name}: {orig} -> {after} rows (-{removed} duplicates)")
            total_removed += removed
    if total_removed == 0:
        print("No duplicates found in output CSVs.")
    else:
        print(f"Total duplicates removed: {total_removed}")


if __name__ == "__main__":
    main()
