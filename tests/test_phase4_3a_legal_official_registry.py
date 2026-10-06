from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
docs=json.loads((ROOT/'data/mock/legal/documents.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'data/mock/core/sources.json').read_text(encoding='utf-8'))
html=(ROOT/'legal.html').read_text(encoding='utf-8')
js=(ROOT/'assets/js/legal.js').read_text(encoding='utf-8')
records=docs['data']; source_ids={x['id'] for x in sources['data']}; doc_ids={x['id'] for x in records}
assert docs['record_count']==len(records)==9
assert all('DEMO' not in x['document_number'].upper() for x in records)
assert all(x['primary_source_id']=='gov-vietnam-legal-documents' for x in records)
assert 'gov-vietnam-legal-documents' in source_ids
assert all(x['official_url'].startswith('https://vanban.chinhphu.vn/') for x in records)
assert all(x['status']=='effective' for x in records)
expected={'31/2024/QH15':'2024-08-01','27/2023/QH15':'2024-08-01','29/2023/QH15':'2024-08-01','43/2024/QH15':'2024-08-01','95/2024/NĐ-CP':'2024-08-01','96/2024/NĐ-CP':'2024-08-01','102/2024/NĐ-CP':'2024-08-01','71/2024/NĐ-CP':'2024-08-01','226/2025/NĐ-CP':'2025-08-15'}
assert {x['document_number']:x['effective_date'] for x in records}==expected
for record in records:
    for rel in record.get('related_documents',[]): assert rel['document_id'] in doc_ids,(record['id'],rel)
assert 'Curated official registry.' in html
assert 'Implementation demo.' not in html
assert 'Official registry · ${data.documents.length} documents' in js
assert 'Unable to load Legal demo data' not in js
print('Phase 4.3A official legal registry tests PASS')
