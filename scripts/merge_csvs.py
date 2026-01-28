"""
Combine all output/*.csv files into one master CSV.

Reads every CSV in output/, adds a 'source' column (filename stem, e.g. rethinkingthefuture),
optionally deduplicates by name (keep first), and writes output/master_results.csv.
"""
import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
MASTER_FILE = OUTPUT_DIR / "master_results.csv"

# Standard columns for the master file (source added)
MASTER_FIELDS = [
    "name", "email", "phone", "website", "address", "city", "state",
    "zip_code", "social_media", "specialty", "source_url", "source"
]


def source_label(path: Path) -> str:
    """Derive source label from filename (e.g. rethinkingthefuture_results.csv -> rethinkingthefuture)."""
    stem = path.stem.lower()
    for suffix in ("_results", "_designers", "_asid"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def load_csv(path: Path, source: str) -> list[dict]:
    """Load one CSV and ensure all MASTER_FIELDS exist; set 'source'."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    out = []
    for row in rows:
        r = {k: (row.get(k) or "").strip() for k in MASTER_FIELDS if k != "source"}
        r["source"] = source
        out.append(r)
    return out


def merge(
    output_dir: Path,
    master_path: Path,
    dedupe: bool = True,
    exclude: list[str] | None = None,
) -> tuple[int, int]:
    """
    Merge all CSVs in output_dir into master_path.
    exclude: optional list of source labels to skip (e.g. ['master'] to skip master_results).
    Returns (total_rows, written_rows).
    """
    exclude = set((exclude or []) + ["master"])
    all_rows = []
    for path in sorted(output_dir.glob("*.csv")):
        if path.resolve() == master_path.resolve():
            continue
        label = source_label(path)
        if label in exclude:
            continue
        if path.name.lower() == master_path.name.lower():
            continue
        try:
            rows = load_csv(path, label)
            all_rows.extend(rows)
        except Exception as e:
            print(f"Warning: skip {path.name}: {e}", file=sys.stderr)

    total = len(all_rows)
    if dedupe and "name" in MASTER_FIELDS:
        seen = set()
        unique = []
        for row in all_rows:
            key = (row.get("name") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(row)
            elif not key:
                unique.append(row)
        all_rows = unique

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(master_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    return total, len(all_rows)


def main():
    ap = argparse.ArgumentParser(description="Merge all output CSVs into one master file")
    ap.add_argument(
        "--output", "-o",
        type=Path,
        default=MASTER_FILE,
        help=f"Master output path (default: {MASTER_FILE})",
    )
    ap.add_argument(
        "--dir", "-d",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory containing CSV files",
    )
    ap.add_argument(
        "--no-dedup",
        action="store_true",
        help="Do not deduplicate by name",
    )
    args = ap.parse_args()

    if not args.dir.exists():
        print(f"Directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    total, written = merge(
        args.dir,
        args.output,
        dedupe=not args.no_dedup,
        exclude=["master"] if args.output.name.lower().startswith("master") else None,
    )
    print(f"Merged {total} rows -> {written} rows ({'deduped' if not args.no_dedup else 'no dedup'}) -> {args.output}")


if __name__ == "__main__":
    main()
