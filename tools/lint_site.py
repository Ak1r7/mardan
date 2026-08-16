from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [ROOT / name for name in ("index.html", "privacy.html", "404.html", "500.html")]


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.refs: list[tuple[str, str, str]] = []
        self.images: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self.labels_for: set[str] = set()
        self.form_control_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.append(data["id"])
        for key in ("src", "href", "action", "data-image"):
            value = data.get(key)
            if value:
                self.refs.append((tag, key, value))
        if tag == "img":
            self.images.append(data)
        elif tag == "button":
            self.buttons.append(data)
        elif tag == "form":
            self.forms.append(data)
        elif tag == "label" and data.get("for"):
            self.labels_for.add(data["for"])
        elif tag in {"input", "textarea", "select"} and data.get("id") and data.get("type") != "hidden":
            self.form_control_ids.add(data["id"])


def local_path(value: str) -> Path | None:
    if value.startswith(("http://", "https://", "mailto:", "tel:", "data:", "#", "tg:")):
        return None
    clean = value.split("?", 1)[0].split("#", 1)[0]
    return ROOT / clean


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    errors: list[str] = []
    parsers: dict[Path, AuditParser] = {}
    for html_file in HTML_FILES:
        if not html_file.exists():
            errors.append(f"Missing HTML file: {html_file.name}")
            continue
        parser = AuditParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        parsers[html_file] = parser
        duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        if duplicates:
            errors.append(f"{html_file.name}: duplicate ids: {', '.join(duplicates)}")
        for tag, key, value in parser.refs:
            path = local_path(value)
            if path is not None and not path.exists():
                errors.append(f"{html_file.name}: missing {key} reference {value}")
        for image in parser.images:
            if "alt" not in image:
                errors.append(f"{html_file.name}: image without alt: {image.get('src', '?')}")
            if not image.get("width") or not image.get("height"):
                errors.append(f"{html_file.name}: image without intrinsic dimensions: {image.get('src', '?')}")
        for button in parser.buttons:
            if not button.get("type"):
                errors.append(f"{html_file.name}: button without explicit type")
        missing_labels = sorted(parser.form_control_ids - parser.labels_for)
        if missing_labels:
            errors.append(f"{html_file.name}: controls without matching labels: {', '.join(missing_labels)}")

    index_parser = parsers.get(ROOT / "index.html")
    if index_parser:
        index_ids = set(index_parser.ids)
        for _, key, value in index_parser.refs:
            if key == "href" and value.startswith("#") and value[1:] and value[1:] not in index_ids:
                errors.append(f"index.html: anchor target does not exist: {value}")
        for form in index_parser.forms:
            classes = set((form.get("class") or "").split())
            if "js-contact-form" not in classes:
                errors.append("index.html: contact form missing js-contact-form class")
            if form.get("action") != "api/contact.php":
                errors.append("index.html: contact form must post to api/contact.php")

    source_files = [ROOT / "src/app.ts", ROOT / "assets/js/app.js", ROOT / "api/contact.php"]
    forbidden = {
        "innerHTML": re.compile(r"\binnerHTML\b"),
        "eval": re.compile(r"\beval\s*\("),
        "new Function": re.compile(r"new\s+Function\b"),
    }
    for source_file in source_files:
        text = source_file.read_text(encoding="utf-8")
        for label, pattern in forbidden.items():
            if pattern.search(text):
                errors.append(f"{source_file.relative_to(ROOT)}: forbidden construct {label}")

    index_text = (ROOT / "index.html").read_text(encoding="utf-8")
    retained_media = []
    removed_media = ["price-and-quality.png", "work-process.png", "installment-quality.png", "services-included.png", "quality-details.png", "exact-deadlines.png"]
    for filename in retained_media:
        if index_text.count(f'src="assets/media/{filename}"') != 1:
            errors.append(f"index.html: retained supplied media must be used exactly once: {filename}")
    for filename in removed_media:
        if index_text.count(f'src="assets/media/{filename}"') != 0:
            errors.append(f"index.html: removed supplied media must not be rendered: {filename}")
    if 'class="breadcrumbs"' in index_text:
        errors.append("index.html: visible breadcrumbs must be removed")
    if 'class="to-top"' in index_text:
        errors.append("index.html: footer arrow must be removed")
    if 'src="assets/images/installment-zero.webp"' not in index_text:
        errors.append("index.html: approved standalone zero-percent asset is missing")
    if re.search(r"Lorem\s+ipsum", index_text, re.I):
        errors.append("index.html: Lorem ipsum is not allowed")

    if errors:
        fail(errors)
    print("OK: HTML, local references, form wiring and forbidden-code checks passed")


if __name__ == "__main__":
    main()
