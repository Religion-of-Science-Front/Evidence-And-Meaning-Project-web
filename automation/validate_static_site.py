from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import sys

ROOT = Path(__file__).resolve().parents[1] / "site"

FORBIDDEN_PUBLIC_PHRASES = [
    "Religion of Science",
    "私たちが聖なるものとして扱うもの",
    "自然は聖なる",
    "生命は科学的に聖なる",
]

REQUIRED_PATHS = [
    "index.html",
    "404.html",
    "assets/site.css",
    "practice/index.html",
    "evidence/index.html",
    "refuge/index.html",
    "worldview/index.html",
    "faq/index.html",
    "trust/index.html",
    "participate/index.html",
    "articles/index.html",
    "articles/why-build-religion/index.html",
    "articles/no-afterlife-guarantee/index.html",
    "articles/three-minute-worship/index.html",
]


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.refs.append(("href", attrs["href"]))
        if tag in ("img", "script") and "src" in attrs:
            self.refs.append(("src", attrs["src"]))
        if tag == "link" and "href" in attrs:
            self.refs.append(("href", attrs["href"]))


def local_target(source: Path, ref: str) -> Path | None:
    if not ref or ref.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
        return None

    parsed = urlparse(ref)
    if parsed.scheme or parsed.netloc:
        return None

    clean = parsed.path
    if not clean:
        return None

    if clean.startswith("/"):
        target = ROOT / clean.lstrip("/")
    else:
        target = source.parent / clean

    target = target.resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        raise ValueError(f"reference escapes site root: {ref}")

    if clean.endswith("/") or target.is_dir():
        target = target / "index.html"

    return target


def main() -> int:
    errors: list[str] = []

    for required in REQUIRED_PATHS:
        if not (ROOT / required).exists():
            errors.append(f"required path missing: {required}")

    html_files = sorted(ROOT.rglob("*.html"))
    if not html_files:
        errors.append("No HTML files found under site/")

    for path in html_files:
        text = path.read_text(encoding="utf-8")

        for phrase in FORBIDDEN_PUBLIC_PHRASES:
            if phrase in text:
                errors.append(f"{path.relative_to(ROOT)}: superseded wording found: {phrase}")

        parser = Parser()
        try:
            parser.feed(text)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"{path.relative_to(ROOT)}: HTML parse failure: {exc}")
            continue

        for kind, ref in parser.refs:
            try:
                target = local_target(path, ref)
            except ValueError as exc:
                errors.append(f"{path.relative_to(ROOT)}: {exc}")
                continue
            if target is None:
                continue
            if not target.exists():
                errors.append(
                    f"{path.relative_to(ROOT)}: missing local {kind}: {ref} -> "
                    f"{target.relative_to(ROOT)}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"PASS: validated {len(html_files)} HTML files and {len(REQUIRED_PATHS)} required paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
