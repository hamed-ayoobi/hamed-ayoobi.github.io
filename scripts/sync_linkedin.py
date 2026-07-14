#!/usr/bin/env python3
"""Refresh cached LinkedIn activity from authorized or public discovery sources."""

from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "data" / "linkedin-posts.js"
PROFILE_URL = "https://www.linkedin.com/in/hamed-ayoobi/recent-activity/all/"


def clean_text(value: str, limit: int = 260) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element.iter():
        name = child.tag.rsplit("}", 1)[-1].lower()
        if name in names and child.text:
            return child.text.strip()
    return ""


def entry_url(entry: ET.Element) -> str:
    for child in entry.iter():
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        if child.attrib.get("href"):
            return child.attrib["href"]
        if child.text:
            return child.text.strip()
    return PROFILE_URL


def activity_date(url: str) -> str:
    match = re.search(r"activity-(\d+)", url)
    if not match:
        return ""
    timestamp_ms = int(match.group(1)) >> 22
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()


def posts_from_feed(feed_url: str) -> list[dict]:
    request = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 profile feed updater"})
    with urllib.request.urlopen(request, timeout=40) as response:
        root = ET.fromstring(response.read())

    entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
    return [
        {
            "title": clean_text(child_text(entry, ("title",)), 140) or "LinkedIn update",
            "summary": clean_text(child_text(entry, ("description", "summary", "content"))),
            "date": child_text(entry, ("pubdate", "published", "updated"))[:10],
            "url": entry_url(entry),
        }
        for entry in entries[:5]
    ]


def posts_from_api(access_token: str, person_urn: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {"author": person_urn, "q": "author", "count": 10, "sortBy": "LAST_MODIFIED"}
    )
    request = urllib.request.Request(
        f"https://api.linkedin.com/rest/posts?{query}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": os.environ.get("LINKEDIN_API_VERSION", "202606"),
            "X-Restli-Protocol-Version": "2.0.0",
            "X-RestLi-Method": "FINDER",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        elements = json.load(response).get("elements", [])

    posts = []
    for post in elements:
        commentary = clean_text(post.get("commentary", ""))
        post_id = post.get("id", "")
        timestamp = post.get("publishedAt") or post.get("createdAt")
        published = (
            datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()
            if timestamp
            else ""
        )
        title = clean_text(re.split(r"(?<=[.!?])\s+", commentary)[0], 140) or "LinkedIn update"
        posts.append(
            {
                "title": title,
                "summary": commentary,
                "date": published,
                "url": f"https://www.linkedin.com/feed/update/{urllib.parse.quote(post_id, safe=':')}/"
                if post_id
                else PROFILE_URL,
            }
        )
    return posts[:5]


def posts_from_search(api_key: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {
            "engine": "google",
            "q": "site:linkedin.com/posts/hamed-ayoobi_",
            "num": 10,
            "hl": "en",
            "api_key": api_key,
        }
    )
    with urllib.request.urlopen(f"https://serpapi.com/search.json?{query}", timeout=40) as response:
        results = json.load(response).get("organic_results", [])

    posts = []
    seen = set()
    for result in results:
        url = result.get("link", "")
        if "linkedin.com/posts/hamed-ayoobi_" not in url or url in seen:
            continue
        seen.add(url)
        summary = clean_text(result.get("snippet", ""))
        title = clean_text(result.get("title", ""), 140)
        title = re.sub(r"\s*\|\s*Hamed Ayoobi.*$", "", title, flags=re.I).strip()
        if not title or title.startswith("#") or "hamed ayoobi's post" in title.lower():
            title = clean_text(re.split(r"(?<=[.!?])\s+", summary)[0], 140) or "LinkedIn update"
        posts.append(
            {
                "title": title,
                "summary": summary,
                "date": activity_date(url),
                "url": url,
            }
        )

    posts.sort(key=lambda post: post["date"], reverse=True)
    return posts[:5]


def cached_posts() -> list[dict]:
    if not OUTPUT.exists():
        return []
    source = OUTPUT.read_text(encoding="utf-8").strip()
    try:
        payload = json.loads(source.removeprefix("window.LINKEDIN_DATA = ").removesuffix(";"))
    except json.JSONDecodeError:
        return []
    return payload.get("posts", [])


def merge_posts(discovered: list[dict]) -> list[dict]:
    """Keep new discoveries without losing newer posts not indexed by search yet."""
    specific_dates = {
        post.get("date") for post in discovered if post.get("url") and post.get("url") != PROFILE_URL
    }
    merged = []
    seen_urls = set()
    for post in [*discovered, *cached_posts()]:
        url = post.get("url") or PROFILE_URL
        if url == PROFILE_URL and post.get("date") in specific_dates:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(post)
    merged.sort(key=lambda post: post.get("date") or "", reverse=True)
    return merged[:5]


def main() -> None:
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    person_urn = os.environ.get("LINKEDIN_PERSON_URN", "").strip()
    feed_url = os.environ.get("LINKEDIN_FEED_URL", "").strip()
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if access_token and person_urn:
        posts = posts_from_api(access_token, person_urn)
        source = "Official LinkedIn Posts API"
    elif feed_url:
        posts = posts_from_feed(feed_url)
        source = "Authorized LinkedIn activity feed"
    elif api_key:
        posts = posts_from_search(api_key)
        source = "Public LinkedIn posts indexed by Google via SerpAPI"
    else:
        print("No authorized LinkedIn source or SERPAPI_KEY is configured; keeping the cached activity.")
        return

    if not posts:
        print("No LinkedIn posts were found; keeping the current cached activity.")
        return

    posts = merge_posts(posts)

    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": source,
        "posts": posts,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "window.LINKEDIN_DATA = " + json.dumps(payload, indent=2, ensure_ascii=True) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(posts)} LinkedIn posts to {OUTPUT}")


if __name__ == "__main__":
    main()
