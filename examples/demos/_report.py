"""Small offline reports and numeric exports for synthetic demos."""

import csv
from html import escape
import json
from pathlib import Path


def plotting():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise ImportError('Install demo support: python -m pip install "greytheory[demos]"') from error
    return plt


def write_csv(path, headers, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def table(headers, rows):
    head = "".join(f"<th>{escape(str(value))}</th>" for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def report(path, title, description, sections):
    content = "".join(f'<section><h2>{escape(heading)}</h2>{body}</section>' for heading, body in sections)
    Path(path).write_text(f'''<!doctype html>
<html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>
:root{{color-scheme:light dark;--bg:#f5f7fb;--panel:white;--ink:#172033;--line:#dbe2ed;--muted:#556176}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111827;--panel:#1b2536;--ink:#e6edf7;--line:#35435a;--muted:#afbdd1}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:32px 20px}}h1{{line-height:1.25}}h2{{font-size:1.25rem;margin:0 0 16px}}
.banner{{background:#4931a8;color:white;padding:12px 18px;border-radius:10px;font-weight:650}}
.intro{{color:var(--muted)}}section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px;margin:20px 0}}
img{{max-width:100%;height:auto;background:white;border-radius:8px}}a{{color:#5388e8}}code{{overflow-wrap:anywhere}}
.table{{overflow:auto}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}
</style><main><div class="banner">SYNTHETIC DEMO · 合成資料 · 非真實量測／鑑識證據</div>
<h1>{escape(title)}</h1><p class="intro">{escape(description)}</p>{content}</main></html>''', encoding="utf-8")
