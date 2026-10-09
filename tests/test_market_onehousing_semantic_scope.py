"""Generic bounded trend-section price parsing must not cross project cards."""
import unittest
from datetime import date
from scripts import market_alternative_auto_probe as p

MONTH = "Căn hộ chung cư dự án Vinhomes Grand Park tháng 10/2026"
MODAL = "Đơn giá phổ biến Mức giá xuất hiện nhiều nhất 54.47 triệu/m² 0% Khoảng giá: 36.81 - 331.19 triệu Giá thuê phổ biến"
DATE = date(2026, 10, 9)


class SemanticSourceTests(unittest.TestCase):
    def section(self, body, footer=""):
        return "Vinhomes Grand Park Tổng quan Biến động giá " + body + " Tiện ích nội khu " + footer

    def test_can_use_bounded_project_month_despite_unrelated_footer(self):
        s = self.section(MONTH + " Giá phổ biến " + MODAL,
                         "Dự án cùng khu vực Căn hộ chung cư dự án The Global City tháng 10/2026")
        result = p.onehousing_price_trend_section(s, DATE, "Vinhomes Grand Park")
        self.assertIsNotNone(result)
        self.assertEqual(result["period"], "2026-10")
        self.assertEqual(result["value_vnd_per_m2"], 54470000)

    def test_reject_unrelated_project_inside_price_section(self):
        s = self.section(MONTH + " Căn hộ chung cư dự án The Global City tháng 10/2026 " + MODAL)
        self.assertIsNone(p.onehousing_price_trend_section(s, DATE, "Vinhomes Grand Park"))

    def test_reject_conflicting_price_triples(self):
        other = MODAL.replace("54.47", "55.47")
        s = self.section(MONTH + " " + MODAL + " " + other)
        self.assertIsNone(p.onehousing_price_trend_section(s, DATE, "Vinhomes Grand Park"))

    def test_reject_undated_or_unbounded_price(self):
        self.assertIsNone(p.onehousing_price_trend_section(self.section(MODAL), DATE, "Vinhomes Grand Park"))
        self.assertIsNone(p.onehousing_price_trend_section("Biến động giá " + MONTH + " " + MODAL, DATE, "Vinhomes Grand Park"))

    def test_reject_future_month_and_different_name(self):
        s = self.section(MONTH.replace("10/2026", "12/2026") + " " + MODAL)
        self.assertIsNone(p.onehousing_price_trend_section(s, DATE, "Vinhomes Grand Park"))
        s = self.section(MONTH.replace("Vinhomes Grand Park", "Masteri Centre Point") + " " + MODAL)
        self.assertIsNone(p.onehousing_price_trend_section(s, DATE, "Vinhomes Grand Park"))


if __name__ == "__main__":
    unittest.main()
