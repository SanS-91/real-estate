from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

assert 'class="article-title-link"' in js
assert 'target="_blank"' in js
assert 'rel="noopener noreferrer"' in js
assert 'href="${esc(article.url)}"' in js
assert '.article-title-link:hover' in css

print("Market news source-link UI tests PASS")
