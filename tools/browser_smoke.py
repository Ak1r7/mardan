from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
import mimetypes

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
HTML = HTML.replace('loading="lazy"', 'loading="eager"').replace('<head>', '<head><base href="http://mardan.local/">', 1)


def main() -> None:
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()

        def handle(route) -> None:
            parsed = urlparse(route.request.url)
            relative = unquote(parsed.path.lstrip("/")) or "index.html"
            path = (ROOT / relative).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                route.abort()
                return
            if path.is_file():
                route.fulfill(
                    status=200,
                    body=path.read_bytes(),
                    content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                )
            else:
                route.fulfill(status=404, body=b"not found", content_type="text/plain")

        page.route("http://mardan.local/**", handle)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.set_content(HTML, wait_until="load", timeout=15_000)
        page.wait_for_function("[...document.images].every(img => img.complete)", timeout=10_000)

        assert page.evaluate("document.documentElement.scrollWidth") == 390
        assert page.locator("h1").count() == 1
        assert page.locator("img:not([alt])").count() == 0

        menu = page.locator(".menu-toggle")
        menu.click()
        assert menu.get_attribute("aria-expanded") == "true"
        assert page.locator("#site-nav").evaluate("el => el.classList.contains('is-open')")
        page.locator('#site-nav a[href="#about"]').evaluate("el => { el.addEventListener('click', event => event.preventDefault(), {once: true}); el.click(); }")
        assert menu.get_attribute("aria-expanded") == "false"

        page.locator('[data-filter="houses"]').click()
        assert page.locator('.project-card:not([hidden])').count() == 1
        page.locator('[data-filter="all"]').click()
        assert page.locator('.project-card:not([hidden])').count() == 4

        second_faq = page.locator('.faq-list details').nth(1)
        second_faq.locator('summary').click()
        page.wait_for_timeout(420)
        assert second_faq.get_attribute('open') is not None
        assert second_faq.locator('.faq-answer').evaluate('el => el.getBoundingClientRect().height') > 0
        second_faq.locator('summary').click()
        page.wait_for_timeout(420)
        assert second_faq.get_attribute('open') is None

        page.locator(".price-card").click()
        modal = page.locator("#request-modal")
        assert not modal.is_hidden()
        assert modal.get_attribute("aria-hidden") == "false"
        page.keyboard.press("Escape")
        assert modal.get_attribute("hidden") is not None
        assert modal.get_attribute("aria-hidden") == "true"

        page.locator("#contact-form-does-not-exist").count()  # confirms selector calls do not mutate the page
        submit = page.locator(".contact-form button[type='submit']")
        submit.click()
        status = page.locator(".contact-form .form-message")
        assert "Укажите имя" in status.inner_text()
        assert page.locator(".contact-form [aria-invalid='true']").count() >= 1

        assert not console_errors, console_errors
        browser.close()
    print("OK: browser smoke tests passed")


if __name__ == "__main__":
    main()
