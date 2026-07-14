const PROFILE = {
  linkedinActivity: "https://www.linkedin.com/in/hamed-ayoobi/recent-activity/all/",
  scholar: "https://scholar.google.com/citations?user=JDQUWWoAAAAJ&hl=en",
};

const state = {
  publications: [],
  filter: "all",
  query: "",
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(date);
}

function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons({ attrs: { "aria-hidden": "true" } });
  }
}

function initNavigation() {
  const toggle = document.querySelector(".menu-toggle");
  const menu = document.querySelector(".site-menu");
  const navLinks = [...document.querySelectorAll('.site-menu a[href^="#"]')];
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  function closeMenu() {
    menu?.classList.remove("open");
    document.body.classList.remove("menu-open");
    toggle?.setAttribute("aria-expanded", "false");
    toggle?.setAttribute("aria-label", "Open navigation");
    if (toggle) toggle.innerHTML = '<i data-lucide="menu" aria-hidden="true"></i>';
    initIcons();
  }

  toggle?.addEventListener("click", () => {
    const isOpen = menu?.classList.toggle("open");
    document.body.classList.toggle("menu-open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    toggle.innerHTML = `<i data-lucide="${isOpen ? "x" : "menu"}" aria-hidden="true"></i>`;
    initIcons();
  });

  menu?.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });

  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      navLinks.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`);
      });
    },
    { rootMargin: "-20% 0px -65%", threshold: [0.05, 0.25] },
  );
  sections.forEach((section) => observer.observe(section));
}

function initReveals() {
  const elements = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    elements.forEach((element) => element.classList.add("visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px" },
  );
  elements.forEach((element) => observer.observe(element));
}

function publicationMatches(publication) {
  const matchesType = state.filter === "all" || publication.category === state.filter;
  if (!matchesType) return false;
  if (!state.query) return true;
  const haystack = [publication.title, publication.authors?.join(" "), publication.venue, publication.year]
    .join(" ")
    .toLowerCase();
  return haystack.includes(state.query);
}

function renderPublications() {
  const list = document.querySelector("#publication-list");
  if (!list) return;
  const publications = state.publications.filter(publicationMatches);

  if (!publications.length) {
    list.innerHTML = '<p class="empty-state">No publications match this search.</p>';
    return;
  }

  list.innerHTML = publications
    .map((publication) => {
      const title = escapeHtml(publication.title);
      const url = escapeHtml(publication.url || PROFILE.scholar);
      const authors = (publication.authors || [])
        .map((author) => (author.toLowerCase().includes("hamed ayoobi") ? `<strong>${escapeHtml(author)}</strong>` : escapeHtml(author)))
        .join(", ");
      return `
        <article class="publication-item">
          <div class="publication-year">${escapeHtml(publication.year)}</div>
          <div>
            <span class="publication-type">${escapeHtml(publication.label || publication.category)}</span>
            <h3>${title}</h3>
            <p class="publication-authors">${authors}</p>
            <p class="publication-venue">${escapeHtml(publication.venue || "Scholarly publication")}</p>
          </div>
          <a class="publication-link" href="${url}" target="_blank" rel="noreferrer" aria-label="Open ${title}">
            <i data-lucide="arrow-up-right" aria-hidden="true"></i>
          </a>
        </article>`;
    })
    .join("");
  initIcons();
}

function applyPublicationData(data) {
  state.publications = data.publications || [];
  document.querySelector("#publication-count").textContent = state.publications.length;
  if (data.generatedAt) {
    document.querySelector("#publication-updated").textContent = `Last refreshed ${formatDate(data.generatedAt.slice(0, 10))} via ${data.source || "OpenAlex"}.`;
  }
  renderPublications();
}

async function loadPublications() {
  const list = document.querySelector("#publication-list");
  const bundled = window.PUBLICATIONS_DATA;
  if (bundled?.publications?.length) {
    applyPublicationData(bundled);
    return;
  }

  try {
    const response = await fetch("data/publications.js", { cache: "no-cache" });
    if (!response.ok) throw new Error(`Publication request failed: ${response.status}`);
    const source = await response.text();
    const data = JSON.parse(source.replace(/^window\.PUBLICATIONS_DATA\s*=\s*/, "").replace(/;\s*$/, ""));
    applyPublicationData(data);
  } catch (error) {
    console.error(error);
    if (list) {
      list.innerHTML = `<p class="empty-state">The publication record is temporarily unavailable. <a href="${PROFILE.scholar}" target="_blank" rel="noreferrer">View Google Scholar</a>.</p>`;
    }
  }
}

function initPublicationControls() {
  const search = document.querySelector("#publication-search");
  const filters = document.querySelectorAll(".filter-button");

  search?.addEventListener("input", (event) => {
    state.query = event.target.value.trim().toLowerCase();
    renderPublications();
  });

  filters.forEach((button) => {
    button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      filters.forEach((candidate) => {
        const isActive = candidate === button;
        candidate.classList.toggle("active", isActive);
        candidate.setAttribute("aria-pressed", String(isActive));
      });
      renderPublications();
    });
  });
}

function renderLinkedInPosts(data) {
  const container = document.querySelector("#linkedin-posts");
  if (!container) return;
  const posts = data.posts || [];
  if (!posts.length) {
    container.innerHTML = `
      <div class="linkedin-empty">
        <p>Research notes, new papers, talks, and collaboration updates are shared on LinkedIn.</p>
        <a class="text-link" href="${PROFILE.linkedinActivity}" target="_blank" rel="noreferrer">View recent activity <i data-lucide="arrow-up-right" aria-hidden="true"></i></a>
      </div>`;
    initIcons();
    return;
  }

  container.innerHTML = posts
    .slice(0, 3)
    .map((post) => `
      <article class="linkedin-post">
        <time datetime="${escapeHtml(post.date || "")}">${escapeHtml(formatDate(post.date))}</time>
        <a href="${escapeHtml(post.url)}" target="_blank" rel="noreferrer">${escapeHtml(post.title || "View post")}</a>
        ${post.summary ? `<p>${escapeHtml(post.summary)}</p>` : ""}
      </article>`)
    .join("");
}

async function loadLinkedInPosts() {
  const container = document.querySelector("#linkedin-posts");
  if (!container) return;
  const bundled = window.LINKEDIN_DATA;
  if (bundled?.posts?.length) {
    renderLinkedInPosts(bundled);
    return;
  }

  try {
    const response = await fetch("data/linkedin-posts.js", { cache: "no-cache" });
    if (!response.ok) throw new Error(`LinkedIn request failed: ${response.status}`);
    const source = await response.text();
    const data = JSON.parse(source.replace(/^window\.LINKEDIN_DATA\s*=\s*/, "").replace(/;\s*$/, ""));
    renderLinkedInPosts(data);
  } catch (error) {
    console.error(error);
    container.innerHTML = `<div class="linkedin-empty"><a class="text-link" href="${PROFILE.linkedinActivity}" target="_blank" rel="noreferrer">View recent activity on LinkedIn <i data-lucide="arrow-up-right" aria-hidden="true"></i></a></div>`;
    initIcons();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelector("#current-year").textContent = new Date().getFullYear();
  initIcons();
  initNavigation();
  initReveals();
  initPublicationControls();
  loadPublications();
  loadLinkedInPosts();
});
