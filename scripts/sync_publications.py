#!/usr/bin/env python3
"""Refresh the website publication data from the author's ORCID-linked OpenAlex record."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ORCID = "0000-0002-5418-6352"
SCHOLAR_URL = "https://scholar.google.com/citations?user=JDQUWWoAAAAJ&hl=en"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "publications.js"
EXCLUDED_OPENALEX_IDS = {
    "https://openalex.org/W2995752150",  # Extended abstract duplicate.
    "https://openalex.org/W3011481592",  # Repository copy of Local-HDP.
    "https://openalex.org/W3152708686",  # Local-HDP preprint with a journal version.
}
TITLE_OVERRIDES = {
    "https://doi.org/10.4204/eptcs.385.36": "PySpArX - A Python Library for Generating Sparse Argumentative Explanations for Neural Networks",
    "https://doi.org/10.1093/neuonc/noaf185.104": "ArgTumour: Integrating Large Language Models and Computational Argumentation to Discuss Treatment Options for High-Grade Glioma",
}


def normalize_title(title: str) -> str:
    title = re.sub(r"\s*\[(technical report|preprint)\]\s*", " ", title, flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def category_for(work: dict) -> tuple[str, str]:
    work_type = work.get("type", "")
    venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name", "")
    doi = (work.get("doi") or "").lower()
    if work_type == "preprint" or "arxiv" in venue.lower():
        return "preprint", "Preprint"
    conference_doi_markers = (
        "10.1609/aaai",
        "10.24963/kr",
        "10.3233/faia",
        "10.4204/eptcs",
        "10.1109/icra",
        "10.1109/icmla",
        "10.1109/case",
        "10.1109/coase",
        "10.1145/3715275.3732100",
        "10.1093/neuonc/noaf185.104",
    )
    if work_type in {"proceedings-article", "book-chapter"} or any(marker in doi for marker in conference_doi_markers) or any(
        marker in venue.lower() for marker in ("conference", "proceedings")
    ):
        return "conference", "Conference paper"
    if work_type == "dissertation":
        return "article", "Doctoral thesis"
    return "article", "Journal article"


def work_url(work: dict) -> str:
    if work.get("doi"):
        return work["doi"]
    primary = work.get("primary_location") or {}
    return primary.get("landing_page_url") or work.get("id") or SCHOLAR_URL


def venue_for(work: dict) -> str:
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    return source.get("display_name") or ""


def fetch_works() -> list[dict]:
    fixture = os.environ.get("OPENALEX_INPUT", "").strip()
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8")).get("results", [])

    params = urllib.parse.urlencode(
        {
            "filter": f"author.orcid:{ORCID}",
            "sort": "publication_date:desc",
            "per-page": 100,
            "mailto": "h.ayoobi@umcg.nl",
        }
    )
    request = urllib.request.Request(
        f"https://api.openalex.org/works?{params}",
        headers={"User-Agent": "hamed-ayoobi.github.io publication updater"},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response).get("results", [])


def deduplicate(works: list[dict]) -> list[dict]:
    final_titles = {
        normalize_title(work.get("title", ""))
        for work in works
        if work.get("type") != "preprint"
    }
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []

    for work in works:
        title = work.get("title") or ""
        normalized = normalize_title(title)
        doi = (work.get("doi") or "").lower()
        is_preprint = work.get("type") == "preprint"

        if work.get("id") in EXCLUDED_OPENALEX_IDS:
            continue
        if not title or not work.get("publication_year"):
            continue
        if is_preprint and normalized in final_titles:
            continue
        if doi and doi in seen_dois:
            continue
        if normalized in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        seen_titles.add(normalized)
        unique.append(work)

    return unique


def serialize(work: dict) -> dict:
    category, label = category_for(work)
    authors = [
        authorship.get("author", {}).get("display_name", "")
        for authorship in work.get("authorships", [])
    ]
    return {
        "title": TITLE_OVERRIDES.get((work.get("doi") or "").lower(), work.get("title", "")),
        "authors": [author for author in authors if author],
        "year": work.get("publication_year"),
        "date": work.get("publication_date"),
        "venue": venue_for(work),
        "category": category,
        "label": label,
        "url": work_url(work),
        "doi": work.get("doi"),
        "openAlexCitations": work.get("cited_by_count", 0),
    }


def main() -> None:
    works = deduplicate(fetch_works())
    publications = [serialize(work) for work in works]
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "OpenAlex / ORCID",
        "orcid": ORCID,
        "scholarUrl": SCHOLAR_URL,
        "publications": publications,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "window.PUBLICATIONS_DATA = " + json.dumps(payload, indent=2, ensure_ascii=True) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(publications)} publications to {OUTPUT}")


if __name__ == "__main__":
    main()
