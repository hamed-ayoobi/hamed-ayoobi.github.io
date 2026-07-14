#!/usr/bin/env python3
"""Optionally add Google Scholar metrics via SerpAPI when a key is configured."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path


AUTHOR_ID = "JDQUWWoAAAAJ"
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "publications.js"


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def scholar_category(publication: str) -> tuple[str, str]:
    text = publication.lower()
    if "arxiv" in text or "preprint" in text:
        return "preprint", "Preprint"
    if any(marker in text for marker in ("conference", "proceedings", "aaai", "icra", "ijcai", "ecai")):
        return "conference", "Conference paper"
    return "article", "Journal article"


def main() -> None:
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not api_key:
        print("SERPAPI_KEY is not configured; keeping publication data without Scholar metrics.")
        return

    query = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": AUTHOR_ID,
            "api_key": api_key,
            "hl": "en",
            "sort": "pubdate",
            "num": 100,
        }
    )
    with urllib.request.urlopen(f"https://serpapi.com/search.json?{query}", timeout=40) as response:
        scholar = json.load(response)

    cited_by = scholar.get("cited_by", {}).get("table", [])
    metrics = {}
    for row in cited_by:
        label = row.get("citations", {}).get("all")
        metric = (row.get("name") or "").lower().replace("-", "")
        if metric == "citations":
            metrics["citations"] = label
        elif metric == "hindex":
            metrics["hIndex"] = label
        elif metric == "i10index":
            metrics["i10Index"] = label

    source = DATA_FILE.read_text(encoding="utf-8").strip()
    payload = json.loads(source.removeprefix("window.PUBLICATIONS_DATA = ").removesuffix(";"))
    publications = payload.get("publications", [])
    existing = {normalize_title(item.get("title", "")): item for item in publications}

    for article in scholar.get("articles", []):
        title = article.get("title", "").strip()
        year = article.get("year")
        if not title or not year:
            continue
        normalized = normalize_title(title)
        citations = (article.get("cited_by") or {}).get("value", 0)
        if normalized in existing:
            existing[normalized]["scholarCitations"] = citations
            existing[normalized]["scholarUrl"] = article.get("link")
            continue

        venue = article.get("publication", "")
        category, label = scholar_category(venue)
        new_item = {
            "title": title,
            "authors": [author.strip() for author in article.get("authors", "").split(",") if author.strip()],
            "year": int(year),
            "date": None,
            "venue": venue,
            "category": category,
            "label": label,
            "url": article.get("link"),
            "doi": None,
            "scholarCitations": citations,
            "scholarUrl": article.get("link"),
        }
        publications.append(new_item)
        existing[normalized] = new_item

    publications.sort(key=lambda item: (item.get("year") or 0, item.get("date") or ""), reverse=True)
    payload["publications"] = publications
    payload["scholarMetrics"] = metrics
    payload["metricsSource"] = "Google Scholar via SerpAPI"
    payload["source"] = "Google Scholar via SerpAPI + OpenAlex / ORCID"
    DATA_FILE.write_text(
        "window.PUBLICATIONS_DATA = " + json.dumps(payload, indent=2, ensure_ascii=True) + ";\n",
        encoding="utf-8",
    )
    print(f"Merged {len(scholar.get('articles', []))} Google Scholar records and metrics: {metrics}")


if __name__ == "__main__":
    main()
