import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")

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
    html = md
    html = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
    html = re.sub(r"^- (.*?)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"\n\n", r"</p><p>", html)
    html = f"<p>{html}</p>"
    return html

def _apply_template(template: str, **kwargs) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result

def build_site(*, content_root: Path, theme_root: Path, out_dir: Path) -> None:
    pages = []
    for md_path in content_root.rglob("*.md"):
        rel = md_path.relative_to(content_root).as_posix()
        raw = _load_text(md_path)
        meta, body = _parse_front_matter(raw)
        title = _extract_title(body, meta)
        pages.append({"source_path": rel, "title": title, "markdown": body})

    page_tpl = _read_template(theme_root / "page.html")
    index_tpl = _read_template(theme_root / "index.html")

    out_dir.mkdir(parents=True, exist_ok=True)

    for p in pages:
        html_body = _markdown_to_html(p["markdown"])
        out_path = out_dir / (p["source_path"][:-3] + ".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_apply_template(page_tpl, title=p["title"], nav_html="", body_html=html_body), encoding="utf-8")

    (out_dir / "index.html").write_text(_apply_template(index_tpl, title="LanternDocs", nav_html="", body_html="<h1>LanternDocs</h1>\n"), encoding="utf-8")
