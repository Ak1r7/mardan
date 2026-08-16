from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT.parent
STANDALONE_DIR = PACKAGE_ROOT / "standalone-version"
STANDALONE_FILE = STANDALONE_DIR / "Мардан-Строй-standalone.html"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def inline_css_asset_urls(css: str) -> str:
    """Inline local CSS url(...) assets for the standalone build."""
    pattern = re.compile(r'url\((?P<quote>["\']?)(?P<path>\.\./[^)"\']+)(?P=quote)\)')

    def replace(match: re.Match[str]) -> str:
        asset = (ROOT / "assets" / "css" / match.group("path")).resolve()
        if not asset.is_file():
            return match.group(0)
        return f'url("{data_uri(asset)}")'

    return pattern.sub(replace, css)


def inline_single_asset_attributes(html: str) -> str:
    """Inline ordinary local asset attributes while preserving the DOM structure."""
    pattern = re.compile(
        r'(?P<prefix>\b(?:src|href|data-image|data-responsive-small|data-responsive-large)=\")(?P<path>assets/[^\"\s]+)(?P<suffix>\")'
    )

    def replace(match: re.Match[str]) -> str:
        asset = ROOT / match.group("path")
        if not asset.is_file():
            return match.group(0)
        return f'{match.group("prefix")}{data_uri(asset)}{match.group("suffix")}'

    return pattern.sub(replace, html)


def inline_srcset_attributes(html: str) -> str:
    """Inline every candidate in srcset without removing responsive image choices."""
    pattern = re.compile(r'(?P<prefix>\bsrcset=\")(?P<value>[^\"]+)(?P<suffix>\")')

    def replace_srcset(match: re.Match[str]) -> str:
        value = match.group("value")

        def replace_asset(asset_match: re.Match[str]) -> str:
            relative = asset_match.group(0)
            asset = ROOT / relative
            return data_uri(asset) if asset.is_file() else relative

        value = re.sub(r'assets/[^,\s]+', replace_asset, value)
        return f'{match.group("prefix")}{value}{match.group("suffix")}'

    return pattern.sub(replace_srcset, html)



RESPONSIVE_IMAGE_SCRIPT = """<script>
(() => {
  const updateResponsiveImages = () => {
    const viewportWidth = window.innerWidth;
    const density = window.devicePixelRatio || 1;
    document.querySelectorAll('img[data-responsive-small][data-responsive-large]').forEach((image) => {
      const slotWidth = viewportWidth <= 700 ? viewportWidth : viewportWidth * 0.5;
      const useSmall = slotWidth * density <= 720;
      const nextSource = useSmall
        ? image.dataset.responsiveSmall
        : image.dataset.responsiveLarge;
      const candidateWidth = useSmall ? 720 : 1280;
      const nextSrcset = `${nextSource} ${candidateWidth}w`;
      image.sizes = '(max-width: 700px) 100vw, 50vw';
      if (image.srcset !== nextSrcset) image.srcset = nextSrcset;
    });
  };
  document.addEventListener('DOMContentLoaded', updateResponsiveImages, { once: true });
  window.addEventListener('resize', updateResponsiveImages, { passive: true });
})();
</script>"""


def prepare_responsive_images(html: str) -> str:
    """Replace multi-candidate data-URI srcsets with deterministic offline selection.

    A comma is part of every data URI and also separates srcset candidates. Some
    browsers parse multi-candidate data-URI srcsets inconsistently. The small
    script reproduces the original 720w/1280w choice from the site's `sizes`
    rule, including device-pixel-ratio, while keeping the rendered image exact.
    """
    image_pattern = re.compile(
        r'<img(?P<before>[^>]*?)\s+sizes="\(max-width: 700px\) 100vw, 50vw"'
        r'(?P<middle>[^>]*?)\s+src="(?P<large>assets/[^\"]+-1280\.webp)"'
        r'\s+srcset="(?P<small>assets/[^\"]+-720\.webp) 720w, '
        r'(?P=large) 1280w"(?P<after>[^>]*)>',
        re.DOTALL,
    )

    def replace_image(match: re.Match[str]) -> str:
        return (
            '<img'
            f'{match.group("before")}'
            f'{match.group("middle")}'
            f' src="{match.group("large")}"'
            f' data-responsive-small="{match.group("small")}"'
            f' data-responsive-large="{match.group("large")}"'
            f'{match.group("after")}>'
        )

    html = image_pattern.sub(replace_image, html)
    # A one-candidate srcset is visually identical to src and unnecessary offline.
    html = re.sub(
        r'\s+srcset="(?P<asset>assets/[^\"\s]+) \d+w"',
        '',
        html,
    )
    return html

def build_standalone() -> None:
    """Build a self-contained visual copy of the full site.

    Responsive sources, srcset and sizes are deliberately retained so the offline
    HTML renders the same assets as the full PHP-capable version at every width.
    """
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html = prepare_responsive_images(html)
    html = html.replace("</head>", f"{RESPONSIVE_IMAGE_SCRIPT}\n</head>", 1)
    css = (ROOT / "assets/css/style.css").read_text(encoding="utf-8")
    css = inline_css_asset_urls(css)
    js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")

    html = re.sub(
        r'<link\b(?=[^>]*\bhref="assets/css/style\.css")[^>]*>',
        lambda _match: f"<style>\n{css}\n</style>",
        html,
        count=1,
    )
    html = re.sub(
        r'<script\b(?=[^>]*\bsrc="assets/js/app\.js")[^>]*>\s*</script>',
        lambda _match: f"<script>\n{js}\n</script>",
        html,
        count=1,
    )

    html = inline_srcset_attributes(html)
    html = inline_single_asset_attributes(html)
    html = html.replace(
        '<link href="https://mardan-stroy.ru/" rel="canonical"/>',
        '<!-- canonical omitted in offline standalone build -->',
    )
    html = html.replace(
        'href="privacy.html"',
        'href="#contacts" title="Политика доступна в полной версии проекта"',
    )

    STANDALONE_DIR.mkdir(parents=True, exist_ok=True)
    STANDALONE_FILE.write_text(html, encoding="utf-8")


def build_manifest() -> None:
    included: list[dict[str, str | int]] = []
    excluded_parts = {"storage", "references", "tests", "tools", "src"}
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.name == "build-manifest.json"
            or any(part in excluded_parts for part in path.relative_to(ROOT).parts)
        ):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        included.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )
    (ROOT / "build-manifest.json").write_text(
        json.dumps({"files": included}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_standalone()
    build_manifest()
    print(f"OK: standalone built at {STANDALONE_FILE}")
