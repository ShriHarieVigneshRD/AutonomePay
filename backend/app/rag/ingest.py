"""Fetch public policy pages listed in data/merchants.json and save dated snapshots.

    python -m app.rag.ingest                       # every merchant with public_sources
    python -m app.rag.ingest --merchant netflix_india

Snapshots land in app/rag/sources/<merchant_id>/<slug>.md and are committed, so the app never
fetches the web while chatting (fast, reproducible, and no live prompt-injection surface).
Refreshing is a deliberate step: re-run this command and review the diff.

Pages are fetched only if robots.txt allows it, reduced to their main text, and screened by
the same prompt-injection guard used for chat. Pages rendered by JavaScript usually yield too
little text; they are reported and skipped (the curated policy document remains the source).
"""

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlsplit

import httpx

from app.core.catalog import load_catalog
from app.guardrails.input_guard import run_pre_llm_guardrail

SOURCES_DIR = Path(__file__).resolve().parent / "sources"
USER_AGENT = "AutonomePayPolicyIngest/1.0"
MIN_CHARS = 600


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "page"


def robots_allows(url: str) -> bool:
    parts = urlsplit(url)
    parser = robotparser.RobotFileParser(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        parser.read()
    except Exception:
        return True  # no readable robots.txt: the conventional default is allow
    return parser.can_fetch(USER_AGENT, url)


def extract_main_text(html: str, url: str) -> str:
    import trafilatura  # ingest-only dependency (requirements-ingest.txt)

    text = trafilatura.extract(
        html, url=url, output_format="markdown", include_tables=True, include_links=False, favor_recall=True
    )
    return (text or "").strip()


def snapshot(merchant_id: str, source: dict, today: str) -> tuple[str, str]:
    url, title = source["url"], source["title"]
    if not robots_allows(url):
        return "skipped", "robots.txt disallows"
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
        }  # no brotli/zstd decoder installed
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=20)
        response.raise_for_status()
    except httpx.HTTPError as e:
        return "failed", f"fetch error: {e.__class__.__name__}"
    text = extract_main_text(response.text, url)
    if len(text) < MIN_CHARS:
        return "skipped", f"only {len(text)} chars of main text (likely rendered by JavaScript)"
    screen = run_pre_llm_guardrail(text)
    if not screen["passed"]:
        return "skipped", f"instruction-like text found ({screen['refusal_reason']})"

    path = SOURCES_DIR / merchant_id / f"{slugify(title)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    header = f"---\ntitle: {title}\nsource_url: {url}\nfetched_at: {today}\nsha256: {digest}\n---\n\n"
    path.write_text(header + text + "\n", encoding="utf-8", newline="\n")
    return "saved", f"{len(text):,} chars -> {path.relative_to(SOURCES_DIR.parent)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    parser.add_argument("--merchant", help="only this merchant_id")
    args = parser.parse_args(argv)

    today = date.today().isoformat()
    rows = []
    for merchant_id, cfg in load_catalog().items():
        if args.merchant and merchant_id != args.merchant:
            continue
        for source in cfg.get("public_sources", []):
            status, detail = snapshot(merchant_id, source, today)
            rows.append((merchant_id, status, source["url"], detail))

    for merchant_id, status, url, detail in rows:
        print(f"{status:8} {merchant_id:18} {url}\n         {detail}")
    saved = sum(1 for row in rows if row[1] == "saved")
    print(f"\n{saved} of {len(rows)} pages saved.")
    return 0 if saved or not rows else 1


if __name__ == "__main__":
    sys.exit(main())
