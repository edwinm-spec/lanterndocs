import json
import os
import posixpath
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def _parse_front_matter(text: str) -> Tuple[Dict, str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    meta = {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            meta[k.strip()] = v.strip()
    if end is None:
        return {}, text
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body

def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

def _extract_title(md: str, meta: Dict) -> str:
    if meta.get("title"):
        return str(meta["title"]).strip()
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"

def _extract_summary(md: str) -> str:
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        parts = [s]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith("#"):
                break
            parts.append(nxt)
            i += 1
        joined = " ".join(parts)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined
    return ""

def _extract_headings(md: str) -> List[str]:
    headings = []
    for line in md.splitlines():
        if line.startswith("## "):
            headings.append(line[3:].strip())
        elif line.startswith("### "):
            headings.append(line[4:].strip())
    return headings

def _markdown_to_html(md: str) -> str:
    # Simple markdown to HTML conversion
    html = md
    html = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
    html = re.sub(r"^- (.*?)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"<li>.*?</li>", lambda m: f"<ul>{m.group(0)}</ul>", html)
    html = re.sub(r"\n\n", r"</p><p>", html)
    html = f"<p>{html}</p>"
    return html

def _apply_template(template: str, **kwargs) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result

def _rel_href(from_file: str, to_file: str) -> str:
    return os.path.relpath(to_file, start=os.path.dirname(from_file) or ".")

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

def _resolve_link(target: str, from_source: str, by_title: Dict, by_path: Dict) -> str:
    tgt = by_title.get(target) or by_path.get(target)
    if not tgt:
        return target
    if tgt.get("draft"):
        return f'<span class="draft-link">{target}</span>'
    to_html = tgt["source_path"][:-3] + ".html"
    href = _rel_href(from_source[:-3] + ".html", to_html)
    return f'<a href="{href}">{target}</a>'

def build_site(*, content_root: Path, theme_root: Path, out_dir: Path) -> None:
    pages = []
    for md_path in sorted(content_root.rglob("*.md")):
        rel = md_path.relative_to(content_root).as_posix()
        raw = _load_text(md_path)
        meta, body = _parse_front_matter(raw)
        title = _extract_title(body, meta)
        draft = _coerce_bool(meta.get("draft"))
        pages.append({"source_path": rel, "title": title, "draft": draft, "markdown": body})

    by_title = {p["title"]: p for p in pages}
    by_path = {p["source_path"][:-3]: p for p in pages}

    published = [p for p in pages if not p["draft"]]

    page_tpl = _read_template(theme_root / "page.html")
    index_tpl = _read_template(theme_root / "index.html")

    out_dir.mkdir(parents=True, exist_ok=True)

    for p in published:
        html_body = _markdown_to_html(p["markdown"])
        html_body = WIKI_LINK_RE.sub(lambda m: _resolve_link(m.group(1), p["source_path"], by_title, by_path), html_body)

        out_path = out_dir / (p["source_path"][:-3] + ".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_apply_template(page_tpl, title=p["title"], nav_html="", body_html=html_body), encoding="utf-8")

    search_pages = []
    for p in published:
        search_pages.append({
            "slug": p["source_path"][:-3].replace("/", "-").lower(),
            "title": p["title"],
            "summary": _extract_summary(p["markdown"]),
            "headings": _extract_headings(p["markdown"]),
            "source_path": p["source_path"]
        })
    (out_dir / "search_index.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "pages": search_pages}, indent=2), encoding="utf-8")
