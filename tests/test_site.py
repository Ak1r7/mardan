from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.section_ids: set[str] = set()
        self.anchor_links: list[str] = []
        self.image_sources: list[str] = []
        self.forms: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "section" and data.get("id"):
            self.section_ids.add(data["id"])
        if tag == "a" and (data.get("href") or "").startswith("#"):
            self.anchor_links.append(data["href"][1:])
        if tag == "img" and data.get("src"):
            self.image_sources.append(data["src"])
        if tag == "form":
            self.forms.append(data)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = INDEX.read_text(encoding="utf-8")
        parser = SiteParser()
        parser.feed(cls.html)
        cls.parser = parser

    def test_required_pages_exist(self) -> None:
        for name in ["index.html", "privacy.html", "404.html", "500.html", "robots.txt", "sitemap.xml"]:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_required_sections_exist(self) -> None:
        required = {"home", "about", "works", "process", "installment", "reviews", "faq", "contacts"}
        self.assertTrue(required.issubset(self.parser.section_ids))

    def test_ids_are_unique(self) -> None:
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))

    def test_internal_anchors_resolve(self) -> None:
        ids = set(self.parser.ids)
        for target in self.parser.anchor_links:
            if target:
                self.assertIn(target, ids)

    def test_requested_media_layout(self) -> None:
        self.assertNotIn('assets/media/brand-poster.png', self.html)
        self.assertIn('class="final-cta-brand"', self.html)
        self.assertTrue((ROOT / "assets/images/final-cta-house.webp").is_file())
        css = (ROOT / "assets/css/style.css").read_text(encoding="utf-8")
        self.assertIn('../images/final-cta-house.webp', css)
        for filename in ["about-company.png", "price-and-quality.png", "work-process.png", "installment-quality.png", "services-included.png", "quality-details.png", "exact-deadlines.png"]:
            self.assertEqual(self.html.count(f'src="assets/media/{filename}"'), 0, filename)

    def test_refined_sections_are_present(self) -> None:
        self.assertNotIn('class="breadcrumbs"', self.html)
        self.assertIn('assets/images/hero-clean.webp', self.html)
        self.assertIn('assets/images/hero-branded.webp', self.html)
        self.assertNotIn('class="hero-motif"', self.html)
        self.assertFalse((ROOT / 'assets/brand-line.svg').exists())
        self.assertIn('class="about-backdrop"', self.html)
        self.assertIn('assets/images/about-premium.webp', self.html)
        self.assertNotIn('class="about-house-art"', self.html)
        self.assertNotIn('class="process-brand-line"', self.html)
        self.assertNotIn('href="#process">Схема работы</a>', self.html)
        self.assertIn('class="process-note-icon process-note-icon-number"', self.html)
        self.assertIn('class="reviews-cards', self.html)
        self.assertGreaterEqual(self.html.count('<details'), 8)
        self.assertNotIn('class="to-top"', self.html)

    def test_portfolio_v2_is_integrated(self) -> None:
        self.assertIn('class="section portfolio-section portfolio-premium"', self.html)
        self.assertIn('>Коммерческие помещения</button>', self.html)
        self.assertNotIn('>Жилые помещения</button>', self.html)
        self.assertIn('assets/images/portfolio/chocolate-1280.webp', self.html)
        self.assertNotIn('apartment-gold', self.html)
        self.assertEqual(self.html.count('class="project-card reveal"'), 4)

    def test_local_image_files_exist(self) -> None:
        for source in self.parser.image_sources:
            if source.startswith("assets/"):
                self.assertTrue((ROOT / source).is_file(), source)

    def test_forms_are_connected_to_real_handler(self) -> None:
        self.assertEqual(len(self.parser.forms), 3)
        for form in self.parser.forms:
            self.assertEqual(form.get("action"), "api/contact.php")
            self.assertIn("js-contact-form", (form.get("class") or "").split())



    def test_compact_hero_quiz_is_integrated(self) -> None:
        self.assertIn('data-hero-quiz=""', self.html)
        self.assertIn('name="formType" type="hidden" value="quiz"', self.html)
        self.assertIn('assets/images/hero-brand-overlay.webp', self.html)
        self.assertTrue((ROOT / 'assets/images/hero-brand-overlay.webp').is_file())
        self.assertEqual(self.html.count('data-quiz-step='), 5)

    def test_modals_start_hidden(self) -> None:
        self.assertRegex(self.html, r'<div(?=[^>]*class="modal")(?=[^>]*hidden)[^>]*>')
        self.assertRegex(self.html, r'<div(?=[^>]*class="gallery-modal")(?=[^>]*hidden)[^>]*>')

    def test_zero_asset_is_integrated(self) -> None:
        self.assertIn('assets/images/installment-zero.webp', self.html)
        self.assertTrue((ROOT / 'assets/images/installment-zero.webp').is_file())

    def test_no_placeholder_content_or_unsafe_js(self) -> None:
        self.assertNotRegex(self.html, re.compile(r"Lorem\s+ipsum", re.I))
        js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotRegex(js, r"\beval\s*\(")


if __name__ == "__main__":
    unittest.main()
