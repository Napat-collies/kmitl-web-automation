"""Browser automation with Playwright (Lecture 12 §6): when search + fetch isn't
enough — JavaScript-rendered pages and multi-step flows behind a login.

Two demos:
1. `render_vs_fetch` — a plain HTTP GET of a JS page returns an empty shell;
   a real browser runs the JavaScript and the content appears.
2. `automate_login` — the four browser primitives (goto, fill, click, read)
   sequenced into a login flow, with the ACT/OBS trace the lecture shows.

Target site: https://quotes.toscrape.com — a sandbox built for scraping practice
(its /js/ page renders with JavaScript; its /login accepts any credentials).

Note (Windows): Playwright's async API needs the Proactor event loop to spawn
its browser subprocess, but uvicorn resets the loop policy to Selector on
startup (worse with --reload), which breaks it with NotImplementedError. The
sync API sidesteps this entirely — it manages its own subprocess machinery
without depending on the calling loop's policy — so each Playwright call runs
via the sync API inside a worker thread (asyncio.to_thread), keeping the
FastAPI endpoints async without touching the main event loop.
"""
from __future__ import annotations
import asyncio 
import httpx
import trafilatura
from playwright.sync_api import sync_playwright

from .config import Settings

_UA = "kmitl-web-automation/1.0 (teaching demo)"
JS_DEMO_URL = "https://quotes.toscrape.com/js/"
LOGIN_URL = "https://quotes.toscrape.com/login"


def _render_vs_fetch_sync(url: str, settings: Settings) -> dict:
    """Runs in a worker thread. Compare a plain GET (no JavaScript) with a real browser render."""
    # 1) plain HTTP GET — what search+fetch would see
    try:
        raw_html = httpx.get(url, timeout=settings.request_timeout,
                             headers={"User-Agent": _UA}, follow_redirects=True).text
    except httpx.HTTPError as exc:
        raw_html = f"(fetch failed: {exc})"
    raw_text = (trafilatura.extract(raw_html) or "").strip()

    # 2) real browser — runs the page's JavaScript, then reads the DOM
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=_UA)
        page.goto(url, wait_until="networkidle", timeout=30000)
        rendered_text = page.inner_text("body").strip()
        try:
            quote_count = page.locator(".quote").count()   # quotes.toscrape specific
        except Exception:  # noqa: BLE001
            quote_count = None
        browser.close()

    return {
        "url": url,
        "raw_len": len(raw_text),
        "raw_preview": raw_text[:400] or "(a plain GET returned no readable content — "
                                         "the page is built by JavaScript)",
        "rendered_len": len(rendered_text),
        "rendered_preview": rendered_text[:400],
        "quotes_visible_after_render": quote_count,
    }


async def render_vs_fetch(url: str, settings: Settings) -> dict:
    """Async wrapper: offloads the sync Playwright flow to a worker thread."""
    return await asyncio.to_thread(_render_vs_fetch_sync, url, settings)


def _automate_login_sync(username: str, password: str, settings: Settings) -> dict:
    """Runs in a worker thread. Drives goto → fill → fill → click → read, recording every ACT/OBS."""
    trace: list[dict] = []

    def log(act: str, obs: str) -> None:
        trace.append({"act": act, "obs": obs})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=_UA)

        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        log(f'goto("{LOGIN_URL}")', f"ok ({page.url})")

        page.fill("input#username", username)
        log('fill("input#username", …)', f"typed {username!r}")

        page.fill("input#password", password)
        log('fill("input#password", …)', "typed ••••••")

        page.click("input[type=submit]")
        page.wait_for_load_state("domcontentloaded")
        log('click("input[type=submit]")', f"navigated -> {page.url}")

        logged_in = page.locator("a[href='/logout']").count() > 0
        log('read("a[href=/logout]")', "Logout link present" if logged_in
            else "not logged in (no Logout link)")

        first_author = ""
        if page.locator(".quote .author").count():
            first_author = page.locator(".quote .author").first.inner_text()
            log('read(".quote .author")', f"{first_author!r}")

        browser.close()

    return {
        "logged_in": logged_in,
        "result": (f"Logged in as {username!r}; the first quote on the page is by "
                   f"{first_author}.") if logged_in else "Login did not succeed.",
        "trace": trace,
    }


async def automate_login(username: str, password: str, settings: Settings) -> dict:
    """Async wrapper: offloads the sync Playwright flow to a worker thread."""
    return await asyncio.to_thread(_automate_login_sync, username, password, settings)