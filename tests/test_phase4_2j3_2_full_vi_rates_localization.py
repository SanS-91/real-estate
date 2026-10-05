from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_rates_vi_localization_contract():
    loc = (ROOT / "assets/js/localization-dynamic.js").read_text(encoding="utf-8")
    macro = (ROOT / "assets/js/macro.js").read_text(encoding="utf-8")
    html = (ROOT / "macro.html").read_text(encoding="utf-8")

    assert "'Interbank Overnight Rate': 'Lãi suất liên ngân hàng qua đêm'" in loc
    assert "'Policy Refinancing Rate': 'Lãi suất tái cấp vốn'" in loc
    assert "Theo dõi chuỗi lãi suất tiền gửi, cho vay, liên ngân hàng và lãi suất điều hành" in loc
    assert "Production đã đối chiếu được hiển thị theo biên thấp–cao đã công bố." in loc

    # Keep chart-note translation robust: coverage and methodology are separate text nodes.
    assert '<span>${esc(seriesCoverageNote(selected))}</span>' in macro
    assert '<span>${esc(ind?.methodology_note || \'\')}</span>' in macro

    assert "assets/js/macro.js?v=4.2J3.2" in html
    assert "assets/js/localization-dynamic.js?v=4.2J3.2" in html
