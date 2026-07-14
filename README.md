# Hamed Ayoobi — academic profile

A fast, accessible personal academic website built for GitHub Pages. The site uses plain HTML, CSS, and JavaScript, so it has no build step and no runtime server dependency.

## Publish with GitHub Pages

1. Push these files to the `hamed-ayoobi.github.io` repository.
2. Open **Settings → Pages** in GitHub.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select the default branch and the repository root, then save.

GitHub will publish the site at `https://hamed-ayoobi.github.io/`.

## Automatic publication updates

The scheduled workflow at `.github/workflows/sync-profile-data.yml` runs daily at 05:17 UTC. It rebuilds `data/publications.js` from the public OpenAlex record associated with ORCID `0000-0002-5418-6352` and commits any changes. This avoids scraping Google Scholar, which frequently blocks automated requests, while keeping the publication list linked to a persistent scholarly identifier.

Google Scholar remains the primary citation-profile link. To update publications and metrics directly from the supplied Scholar profile, create a repository Actions secret named `SERPAPI_KEY`. The optional script queries Scholar author ID `JDQUWWoAAAAJ` through SerpAPI, merges up to 100 date-sorted papers into the OpenAlex record, and adds citations, h-index, and i10-index data. This server-side workflow is necessary because Google Scholar blocks direct browser requests from a static GitHub Pages site.

The workflow can also be run manually from **Actions → Sync profile data → Run workflow**.

## LinkedIn activity

LinkedIn does not provide an unauthenticated read API for personal posts. The site therefore reads a committed cache, `data/linkedin-posts.js`, and always links to the public activity page as a dependable fallback.

For reliable automatic updates, use a LinkedIn developer application approved for the restricted `r_member_social` permission and add `LINKEDIN_ACCESS_TOKEN` plus `LINKEDIN_PERSON_URN` (for example, `urn:li:person:...`) as repository Actions secrets. The workflow then reads the latest posts through LinkedIn's official Posts API.

Alternatively, connect an RSS/Atom feed that you are authorized to use as `LINKEDIN_FEED_URL`, or configure the same `SERPAPI_KEY` used for Scholar. The daily workflow prefers the official API, then an authorized feed, then public posts indexed under `linkedin.com/posts/hamed-ayoobi_` through Google/SerpAPI. Search discovery can lag behind a new post; all discovered posts are therefore merged with the committed cache so a delayed result or transient failure cannot remove a newer cached post.

Both data files are browser-loadable JavaScript caches. This means publications and LinkedIn activity work when `index.html` is opened directly, on localhost, and on GitHub Pages.

Posts can also be curated directly in `data/linkedin-posts.js` using this format inside the `posts` array:

```json
{
  "title": "Post title",
  "summary": "A short excerpt.",
  "date": "2026-07-14",
  "url": "https://www.linkedin.com/posts/..."
}
```

## Update profile content

- Main biography, research themes, supervision, teaching, and recognition: `index.html`
- Visual design and responsive layout: `css/styles.css`
- Publication and activity rendering: `js/scripts.js`
- Publication updater: `scripts/sync_publications.py`

Run a local preview from the repository root with:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.
