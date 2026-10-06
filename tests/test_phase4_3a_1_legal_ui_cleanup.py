from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "legal.html").read_text(encoding="utf-8")
legal = (ROOT / "assets/js/legal.js").read_text(encoding="utf-8")
static = (ROOT / "assets/js/localization-static.js").read_text(encoding="utf-8")
dynamic = (ROOT / "assets/js/localization-dynamic.js").read_text(encoding="utf-8")

# Cache busting must force the browser to pick up the legal cleanup.
assert 'assets/js/legal.js?v=4.3A1' in html
assert 'assets/js/localization-static.js?v=4.3A1' in html
assert 'assets/js/localization-dynamic.js?v=4.3A1' in html

# Legal static banner is official, not demo.
assert "Curated official registry." in html
assert "Implementation demo." not in html
assert "['.demo-banner strong', 'Curated official registry.', 'Cơ sở dữ liệu văn bản chính thức.']" in static
assert "Bản mô phỏng triển khai." not in static.split('const LEGAL = [',1)[1].split('];',1)[0]

# Overview metric and dynamic labels must no longer describe the legal data as illustrative.
assert "Official Government document registry" in legal
assert "Illustrative legal database" not in legal
for en, vi in {
    "Official document layer": "Lớp văn bản chính thức",
    "Latest Documents": "Văn bản mới nhất",
    "Effective Timeline": "Lịch hiệu lực",
    "Government": "Chính phủ",
    "National Assembly": "Quốc hội",
    "Official Government document registry": "Danh mục văn bản chính thức từ nguồn Chính phủ",
}.items():
    assert f"'{en}': '{vi}'" in dynamic

assert "Official registry · (\\d+) documents" in dynamic
assert "Cơ sở dữ liệu chính thức · ${match[1]} văn bản" in dynamic

print("Phase 4.3A.1 Legal UI cleanup tests PASS")
