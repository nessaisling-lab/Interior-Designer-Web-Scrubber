"""
Clean and enrich contact info in rethinkingthefuture_results.csv.

1. Clean: split malformed email (e.g. "212.477.0287info@cookfox.com") into phone and email.
2. Enrich (--enrich): visit profile URL (website when internal) or firm website to fill email/website using the scraper.
"""
import argparse
import csv
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "output" / "rethinkingthefuture_results.csv"

# Email pattern: local part must start with a letter so we don't match "212.477.0287info@..."
EMAIL_RE = re.compile(r"[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Leading digits that could be phone (7+ digits, optional dots/dashes) or zip (5 digits)
PHONE_LIKE = re.compile(r"^(\d[\d.\-\s]{6,})\s*$")  # e.g. 212.477.0287
ZIP_LIKE = re.compile(r"^(\d{5})\s*$")  # 5 digits only


def clean_contact_cell(value: str) -> tuple[str, str, str]:
    """
    If value looks like "212.477.0287info@cookfox.com" or "10038info@...", return
    (phone, zip_code, email) with extracted parts. Otherwise return ("", "", value).
    """
    if not value or not value.strip():
        return ("", "", "")
    raw = value.strip()
    email_m = EMAIL_RE.search(raw)
    if not email_m:
        return ("", "", raw)
    email = email_m.group(0)
    prefix = raw[: email_m.start()].strip()
    if not prefix:
        return ("", "", email)
    # prefix is something like "212.477.0287" or "10038" or "11201"
    digits_only = re.sub(r"\D", "", prefix)
    if len(digits_only) == 5:
        return ("", prefix.strip(), email)  # treat as zip
    if len(digits_only) >= 7:
        return (prefix.strip(), "", email)  # treat as phone
    return ("", "", email)


def clean_row(row: dict) -> dict:
    """Clean email/phone/zip in one row. Mutates and returns row."""
    email_val = (row.get("email") or "").strip()
    if not email_val:
        return row
    phone, zip_code, email = clean_contact_cell(email_val)
    row["email"] = email
    if phone and not (row.get("phone") or "").strip():
        row["phone"] = phone
    if zip_code and not (row.get("zip_code") or "").strip():
        row["zip_code"] = zip_code
    return row


def run_clean(csv_path: Path) -> int:
    """Clean malformed contact fields. Returns number of rows updated."""
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changes = 0
    for row in rows:
        email_before = (row.get("email") or "").strip()
        clean_row(row)
        if (row.get("email") or "").strip() != email_before:
            changes += 1
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return changes


def _is_rtf_profile_url(url: str) -> bool:
    """True if url looks like a re-thinkingthefuture profile (not the list page)."""
    if not url or "re-thinkingthefuture.com" not in url.lower():
        return False
    # List pages look like .../top-architecture-firms-architects-in-new-york/ or .../2/
    if "top-architecture-firms-architects-in-new-york" in url.lower() and url.rstrip("/").split("/")[-1].isdigit():
        return False
    if "top-architecture-firms-architects-in-new-york" in url.lower() and url.rstrip("/").endswith("new-york"):
        return False
    return True


def run_enrich(csv_path: Path, delay_sec: float = 2.0) -> int:
    """Enrich rows missing email/website by visiting profile URL or firm website via scraper."""
    sys.path.insert(0, str(PROJECT_ROOT))
    import config
    from scrapers.directory_scraper import DirectoryScraper

    cfg = config.WEBSITE_CONFIGS.get("rethinkingthefuture")
    if not cfg:
        print("rethinkingthefuture config not found")
        return 0
    scraper = DirectoryScraper(cfg)

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    updated = 0
    for i, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip()
        website = (row.get("website") or "").strip()
        need_email = not email
        need_website = not website or "re-thinkingthefuture.com" in (website or "").lower()
        if not need_email and not need_website:
            continue
        # Use website as profile URL when it's an RTF profile; then resolve to homepage + email
        if _is_rtf_profile_url(website):
            try:
                homepage, resolved_email = scraper._resolve_homepage_from_profile(website)
                if homepage:
                    row["website"] = homepage
                    updated += 1
                if resolved_email and need_email:
                    row["email"] = resolved_email
                    updated += 1
            except Exception as e:
                print(f"  [{name}] profile error: {e}")
        elif website and website.startswith("http") and "re-thinkingthefuture" not in website.lower():
            if need_email:
                try:
                    resolved_email = scraper._try_extract_email_from_detail_page(website)
                    if resolved_email:
                        row["email"] = resolved_email
                        updated += 1
                except Exception as e:
                    print(f"  [{name}] website email error: {e}")
        if scraper.selenium_helper:
            scraper.selenium_helper.close()
            scraper.selenium_helper = None
        if delay_sec > 0 and i < len(rows) - 1:
            time.sleep(delay_sec)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return updated


def main():
    ap = argparse.ArgumentParser(description="Clean/enrich contact info in rethinkingthefuture_results.csv")
    ap.add_argument("--enrich", action="store_true", help="Visit source_url/website to fill email/website (uses Selenium)")
    ap.add_argument("--csv", type=Path, default=CSV_PATH, help="Path to CSV")
    ap.add_argument("--delay", type=float, default=2.0, help="Seconds between requests when enriching")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}")
        sys.exit(1)

    n = run_clean(args.csv)
    print(f"Clean: updated {n} row(s) (split phone/zip/email where merged).")

    if args.enrich:
        print("Enriching from source_url/website (this may take a while)...")
        m = run_enrich(args.csv, delay_sec=args.delay)
        print(f"Enrich: updated {m} field(s).")
    else:
        print("Run with --enrich to fill email/website by visiting profile and firm pages.")


if __name__ == "__main__":
    main()
