import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>SkreenMaker Report</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; color: #333; margin: 0; padding: 20px; }
.container { max-width: 1200px; margin: 0 auto; }
h1 { margin-bottom: 8px; }
.summary { display: flex; gap: 16px; margin-bottom: 20px; }
.badge { padding: 8px 14px; border-radius: 6px; font-weight: 600; }
.badge.ok { background: #d4edda; color: #155724; }
.badge.warn { background: #fff3cd; color: #856404; }
.badge.err { background: #f8d7da; color: #721c24; }
table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f1f3f5; font-weight: 600; }
tr:hover { background: #f8f9fa; }
img { max-width: 320px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }
.no-change { background: #fffbe6; }
</style>
</head>
<body>
<div class="container">
  <h1>SkreenMaker Walkthrough Report</h1>
  <p>Generated: {{timestamp}}</p>
  <div class="summary">
    <span class="badge ok">Steps: {{total_steps}}</span>
    <span class="badge ok">OK: {{ok_count}}</span>
    <span class="badge warn">No change: {{no_change_count}}</span>
    <span class="badge err">Errors: {{error_count}}</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Action</th>
        <th>Element</th>
        <th>Result</th>
        <th>Before</th>
        <th>After</th>
      </tr>
    </thead>
    <tbody>
      {{rows}}
    </tbody>
  </table>
</div>
</body>
</html>
"""


def _image_to_base64(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_report(
    steps: List[Dict[str, Any]],
    output_path: str,
    before_dir: str,
    after_dir: str,
) -> str:
    """
    Генерирует HTML-отчет по walkthrough.

    steps: список словарей с ключами:
        - step: int
        - action: str
        - element: str
        - result: str
        - before_image: имя файла
        - after_image: имя файла
        - has_change: bool (опционально)
        - is_error: bool (опционально)
    """
    total = len(steps)
    ok = sum(1 for s in steps if not s.get("is_error"))
    err = sum(1 for s in steps if s.get("is_error"))
    no_change = sum(1 for s in steps if s.get("has_change") is False and not s.get("is_error"))

    row_html = []
    for s in steps:
        before_path = os.path.join(before_dir, s.get("before_image", ""))
        after_path = os.path.join(after_dir, s.get("after_image", ""))
        before_b64 = _image_to_base64(before_path)
        after_b64 = _image_to_base64(after_path)

        before_tag = f'<img src="data:image/jpeg;base64,{before_b64}">' if before_b64 else "—"
        after_tag = f'<img src="data:image/jpeg;base64,{after_b64}">' if after_b64 else "—"

        cls = ""
        if s.get("is_error"):
            cls = " class=\"err\""
        elif s.get("has_change") is False:
            cls = " class=\"no-change\""

        row_html.append(
            f"<tr{cls}>"
            f"<td>{s.get('step', 0)}</td>"
            f"<td>{s.get('action', '')}</td>"
            f"<td>{s.get('element', '')}</td>"
            f"<td>{s.get('result', '')}</td>"
            f"<td>{before_tag}</td>"
            f"<td>{after_tag}</td>"
            f"</tr>"
        )

    html = (
        HTML_TEMPLATE
        .replace("{{timestamp}}", datetime.now().isoformat())
        .replace("{{total_steps}}", str(total))
        .replace("{{ok_count}}", str(ok))
        .replace("{{no_change_count}}", str(no_change))
        .replace("{{error_count}}", str(err))
        .replace("{{rows}}", "\n".join(row_html))
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
