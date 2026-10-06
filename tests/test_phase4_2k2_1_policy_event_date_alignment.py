from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from collectors.policy_news_common import parse_policy_news


def test_vietnamplus_effective_date_uses_article_year_not_current_sidebar_dates():
    html = """
    <html><body>
      <div class='sidebar'>01/10/2026</div>
      <h1>Ngân hàng Nhà nước giảm lãi suất điều hành lần thứ 4 liên tiếp</h1>
      <time datetime='2023-06-16T12:55:00+07:00'>16/06/2023 12:55</time>
      <p>NHNN quyết định điều chỉnh các mức lãi suất, áp dụng từ ngày 19/6 tới đây.</p>
      <p>Quyết định số 1123/QĐ-NHNN; lãi suất cho vay qua đêm trong thanh toán điện tử liên ngân hàng giảm từ 5,5%/năm xuống 5%/năm; lãi suất tái cấp vốn giảm từ 5,0%/năm xuống 4,5%/năm; lãi suất tái chiết khấu giảm từ 3,5%/năm xuống 3,0%/năm.</p>
    </body></html>
    """
    rows = parse_policy_news(html, 'https://www.vietnamplus.vn/example.vnp', '2026-10-05T00:00:00Z', 'vna-vietnamplus')
    assert len(rows) == 3
    assert {r['period'] for r in rows} == {'2023-06-19'}
    assert {r['source_record_id'] for r in rows} == {'1123/QĐ-NHNN'}


def test_banking_times_hom_nay_effective_date():
    html = """
    <html><head><meta property='article:published_time' content='2023-06-19T08:07:00+07:00'></head><body>
      <p>Ngày 16/6/2023, NHNN ban hành các quyết định, có hiệu lực từ hôm nay 19/6/2023.</p>
      <p>Lãi suất cho vay qua đêm trong thanh toán điện tử liên ngân hàng giảm từ 5,5%/năm xuống 5%/năm; lãi suất tái cấp vốn giảm từ 5,0%/năm xuống 4,5%/năm; lãi suất tái chiết khấu giảm từ 3,5%/năm xuống 3,0%/năm.</p>
    </body></html>
    """
    rows = parse_policy_news(html, 'https://thoibaonganhang.vn/example.html', '2026-10-05T00:00:00Z', 'banking-times-vn')
    assert len(rows) == 3
    assert {r['period'] for r in rows} == {'2023-06-19'}


if __name__ == "__main__":
    test_vietnamplus_effective_date_uses_article_year_not_current_sidebar_dates()
    test_banking_times_hom_nay_effective_date()
    print("Phase 4.2K.2.1 policy event date alignment tests PASS")
