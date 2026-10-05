from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    macro = (ROOT / "assets/js/macro.js").read_text(encoding="utf-8")
    loc = (ROOT / "assets/js/localization-dynamic.js").read_text(encoding="utf-8")
    html = (ROOT / "macro.html").read_text(encoding="utf-8")

    assert "function observationStatusLabel(row)" in macro
    assert "observationStatusLabel(row)" in macro
    assert "customer-rate ranges published by the State Bank of Vietnam and independently corroborated through secondary sources" in macro
    assert "'Historical series': 'Chuỗi lịch sử'" in loc
    assert "'Value': 'Giá trị'" in loc
    assert "các biên lãi suất khách hàng do NHNN công bố được đối chiếu qua các nguồn độc lập" in loc
    assert "macro.js?v=4.2J3.2" in html
    assert "localization-dynamic.js?v=4.2J3.2" in html

    print("Phase 4.2J.3.1 labeling/localization cleanup tests PASS")

if __name__ == "__main__":
    main()
