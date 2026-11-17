"""Turn the policy corpus into small, labelled chunks.

Corpus per merchant:
- rag/policies/*.md      curated internal settlement rules
- rag/sources/<id>/*.md  dated snapshots of the merchant's public pages (see ingest.py)
- one generated "Enforced limits" chunk from data/merchants.json, so retrieved text always
  matches what the guardrail enforces.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.catalog import load_catalog

RAG_DIR = Path(__file__).resolve().parent
POLICIES_DIR = RAG_DIR / "policies"
SOURCES_DIR = RAG_DIR / "sources"
MAX_CHARS = 700
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


@dataclass(frozen=True)
class Chunk:
    id: str
    merchant_id: str
    source: str  # document title
    section: str
    text: str
    kind: str  # policy | web | limits
    url: str | None = None
    fetched_at: str | None = None

    def labelled(self) -> str:
        origin = f" ({self.url}, fetched {self.fetched_at})" if self.url else ""
        return f"[{self.source} › {self.section}]{origin}\n{self.text}"

    def citation(self) -> dict[str, Any]:
        return {"id": self.id, "source": self.source, "section": self.section, "kind": self.kind,
                "url": self.url, "fetched_at": self.fetched_at}  # fmt: skip


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    header, _, body = text[4:].partition("\n---\n")
    meta = dict(line.split(": ", 1) for line in header.splitlines() if ": " in line)
    return meta, body


def _units(lines: list[str]) -> list[str]:
    """Paragraphs and list items, the smallest pieces we keep whole."""
    units, current = [], []
    for line in lines:
        if not line.strip() or _LIST_ITEM.match(line):
            if current:
                units.append(" ".join(current))
            current = [line.strip()] if line.strip() else []
        else:
            current.append(line.strip())
    if current:
        units.append(" ".join(current))
    return [u for u in units if u]


_NUMBERED_RULE = re.compile(r"^\d+[.)]\s")


def _pack(units: list[str], rules_stand_alone: bool) -> list[str]:
    """Group small units up to MAX_CHARS. A numbered policy rule always stands alone (precise citations)."""
    windows, current = [], ""
    for unit in units:
        if rules_stand_alone and _NUMBERED_RULE.match(unit):
            if current:
                windows.append(current)
                current = ""
            windows.append(unit)
            continue
        while len(unit) > MAX_CHARS:  # one huge paragraph: cut at a sentence boundary when possible
            cut = unit.rfind(". ", 0, MAX_CHARS) + 1 or MAX_CHARS
            windows.append(unit[:cut].strip())
            unit = unit[cut:].strip()
        if current and len(current) + len(unit) + 1 > MAX_CHARS:
            windows.append(current)
            current = ""
        current = f"{current}\n{unit}" if current else unit
    if current:
        windows.append(current)
    return windows


def chunk_markdown(merchant_id: str, doc_id: str, body: str, kind: str, meta: dict[str, str]) -> list[Chunk]:
    title = meta.get("title", "")
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in body.splitlines():
        heading = _HEADING.match(line)
        if heading:
            if not title and len(heading.group(1)) == 1:
                title = heading.group(2).strip()
                continue
            sections.append((heading.group(2).strip(), []))
        else:
            sections[-1][1].append(line)

    chunks = []
    for section, lines in sections:
        for window in _pack(_units(lines), rules_stand_alone=kind == "policy"):
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{len(chunks)}",
                    merchant_id=merchant_id,
                    source=title or doc_id,
                    section=section,
                    text=window,
                    kind=kind,
                    url=meta.get("source_url"),
                    fetched_at=meta.get("fetched_at"),
                )
            )
    return chunks


def limits_chunk(cfg: dict[str, Any]) -> Chunk:
    lines = [
        f"Maximum renewal discount: INR {cfg['max_discount_inr']:.2f}.",
        f"Maximum grace period: {cfg['max_grace_days']} days.",
        f"Escalate to a human above INR {cfg['auto_escalation_limit']:,.2f}.",
    ]
    if cfg.get("plans"):
        plans = "; ".join(f"{p['name']} INR {p['price_inr']} per {p['period']}" for p in cfg["plans"])
        lines.append(f"Plans: {plans}.")
    if cfg.get("split_schedule_pct"):
        pct = "/".join(str(p) for p in cfg["split_schedule_pct"])
        lines.append(
            f"Instalments allowed: {pct} split for invoices of INR {cfg['split_min_invoice_inr']:,} or more."
        )
    else:
        lines.append("Instalment or split payments are not offered.")
    if cfg.get("partial_settlement_pct"):
        lines.append(
            f"Disputed goods: the customer may pay the undisputed {cfg['partial_settlement_pct']}% now."
        )
    return Chunk(
        id=f"limits:{cfg['merchant_id']}",
        merchant_id=cfg["merchant_id"],
        source=f"{cfg['name']} enforced limits",
        section="Guardrail limits",
        text="\n".join(lines),
        kind="limits",
    )


def load_corpus() -> dict[str, list[Chunk]]:
    catalog = load_catalog()
    by_doc = {cfg["policy_doc"]: merchant_id for merchant_id, cfg in catalog.items()}
    corpus: dict[str, list[Chunk]] = {
        merchant_id: [limits_chunk(cfg)] for merchant_id, cfg in catalog.items()
    }

    for path in sorted(POLICIES_DIR.glob("*.md")):
        merchant_id = by_doc.get(path.name)
        if merchant_id:
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            corpus[merchant_id] += chunk_markdown(merchant_id, path.stem, body, "policy", meta)

    for path in sorted(SOURCES_DIR.glob("*/*.md")):
        merchant_id = path.parent.name
        if merchant_id in corpus:
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            corpus[merchant_id] += chunk_markdown(
                merchant_id, f"{merchant_id}/{path.stem}", body, "web", meta
            )
    return corpus
