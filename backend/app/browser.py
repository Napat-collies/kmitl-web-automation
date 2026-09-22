"""Browser automation with Playwright (Lecture 12 §6): when search + fetch isn't
enough — JavaScript-rendered pages and multi-step flows behind a login.

Two demos:
1. `render_vs_fetch` — a plain HTTP GET of a JS page returns an empty shell;
   a real browser runs the JavaScript and the content appears.
2. `automate_login` — the four browser primitives (goto, fill, click, read)
   sequenced into a login flow, with the ACT/OBS trace the lecture shows.

Target site: https://quotes.toscrape.com — a sandbox built for scraping practice
(its /js/ page renders with JavaScript; its /login accepts any credentials).
"""
from __future__ import annotations

import httpx
import trafilatura
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from .config import Settings

_UA = "kmitl-web-automation/1.0 (teaching demo)"
JS_DEMO_URL = "https://quotes.toscrape.com/js/"
LOGIN_URL = "https://quotes.toscrape.com/login"


class BrowserUnavailable(RuntimeError):
    """The browser couldn't start — almost always because it wasn't installed."""


def _launch_hint(exc: Exception) -> str:
    return (
        "Could not start the browser. In the backend/ folder run:\n"
        "    uv run playwright install chromium\n"
        "(on Linux you may also need: uv run playwright install-deps)\n"
        f"Original error: {exc}"
    )


async def _launch_chromium(p):
    """Launch chromium, turning the cryptic 'Executable doesn't exist' / missing-lib
    failure into a clear, actionable BrowserUnavailable message."""
    try:
        return await p.chromium.launch()
    except PlaywrightError as exc:
        raise BrowserUnavailable(_launch_hint(exc)) from exc


async def render_vs_fetch(url: str, settings: Settings) -> dict:
    """Compare a plain GET (no JavaScript) with a real browser render."""
    # 1) plain HTTP GET — what search+fetch would see
    try:
        raw_html = httpx.get(url, timeout=settings.request_timeout,
                             headers={"User-Agent": _UA}, follow_redirects=True).text
    except httpx.HTTPError as exc:
        raw_html = f"(fetch failed: {exc})"
    raw_text = (trafilatura.extract(raw_html) or "").strip()

    # 2) real browser — runs the page's JavaScript, then reads the DOM
    async with async_playwright() as p:
        browser = await _launch_chromium(p)
        page = await browser.new_page(user_agent=_UA)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        rendered_text = (await page.inner_text("body")).strip()
        try:
            quote_count = await page.locator(".quote").count()   # quotes.toscrape specific
        except Exception:  # noqa: BLE001
            quote_count = None
        await browser.close()

    return {
        "url": url,
        "raw_len": len(raw_text),
        "raw_preview": raw_text[:400] or "(a plain GET returned no readable content — "
                                         "the page is built by JavaScript)",
        "rendered_len": len(rendered_text),
        "rendered_preview": rendered_text[:400],
        "quotes_visible_after_render": quote_count,
    }


async def automate_login(username: str, password: str, settings: Settings) -> dict:
    """Drive the goto → fill → fill → click → read flow, recording every ACT/OBS."""
    trace: list[dict] = []

    def log(act: str, obs: str) -> None:
        trace.append({"act": act, "obs": obs})

    async with async_playwright() as p:
        browser = await _launch_chromium(p)
        page = await browser.new_page(user_agent=_UA)

        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        log(f'goto("{LOGIN_URL}")', f"ok ({page.url})")

        await page.fill("input#username", username)
        log('fill("input#username", …)', f"typed {username!r}")

        await page.fill("input#password", password)
        log('fill("input#password", …)', "typed ••••••")

        await page.click("input[type=submit]")
        await page.wait_for_load_state("domcontentloaded")
        log('click("input[type=submit]")', f"navigated -> {page.url}")

        logged_in = await page.locator("a[href='/logout']").count() > 0
        log('read("a[href=/logout]")', "Logout link present" if logged_in
            else "not logged in (no Logout link)")

        first_author = ""
        if await page.locator(".quote .author").count():
            first_author = await page.locator(".quote .author").first.inner_text()
            log('read(".quote .author")', f"{first_author!r}")

        await browser.close()

    return {
        "logged_in": logged_in,
        "result": (f"Logged in as {username!r}; the first quote on the page is by "
                   f"{first_author}.") if logged_in else "Login did not succeed.",
        "trace": trace,
    }
