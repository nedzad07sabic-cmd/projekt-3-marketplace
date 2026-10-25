"""Build the fictional-data website preview. Python standard library only."""
from pathlib import Path
import base64
import hashlib

p = Path(__file__).resolve().parent
html = (p / "template.html").read_text(encoding="utf-8")
scripts = [(p / name).read_text(encoding="utf-8") for name in ("core.js", "ui.js")]
hashes = " ".join("'sha256-" + base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode("ascii") + "'" for code in scripts)
html = html.replace("__SCRIPT_HASHES__", hashes)
for marker, filename in [("__CSS__", "style.css"), ("__CORE__", "core.js"), ("__UI__", "ui.js")]:
    html = html.replace(marker, (p / filename).read_text(encoding="utf-8"))
output = p.parent / "docs" / "index.html"
output.parent.mkdir(exist_ok=True)
output.write_text(html, encoding="utf-8")
print(f"Built {output}")
