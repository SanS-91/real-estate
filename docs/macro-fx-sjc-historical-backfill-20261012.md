# Macro FX & SJC historical quotes — reviewed batch (12 October 2026)

## What is included
The independent history file `data/processed/macro/historical-fx-gold-observations.json` has 14 facts:
- 6 dated State Bank of Vietnam USD/VND **central reference rates**.
- 4 dated SJC 1-tael gold-bar **buy** quotations.
- 4 corresponding SJC 1-tael gold-bar **sell** quotations.

No invented daily values are inserted between source-attested dates. A missing date is a gap, not proof of zero change. The `1Y` chart shows the dates in the past year; `ALL` includes the 2025 history. The web application does not mix demo history with production for promoted indicator IDs.

## Verified FX reference dates — VND per USD

| Date | Value | First source | Independent corroboration |
|---|---:|---|---|
| 2025-03-10 | 24,754 | https://infographics.vn/interactive-ty-gia-trung-tam-ngay-10-3-2025-1-usd-24754-vnd/214837.vna | https://en.vneconomy.vn/bien-do-mua-va-ban-usd-o-cac-ngan-hang-giam-dan.htm |
| 2025-04-10 | 24,964 | https://infographics.vn/interactive-ty-gia-trung-tam-ngay-10-4-2025-1-usd-24964-vnd/215194.vna | https://vietnamnet.vn/gia-vang-hom-nay-10-4-2025-tang-manh-cho-ky-luc-moi-2389489.html |
| 2025-06-10 | 24,985 | https://infographics.vn/interactive-ty-gia-trung-tam-ngay-10-6-2025-1-usd-24985-vnd/215939.vna | https://vov.vn/thi-truong/ty-gia/ty-gia-usd-hom-nay-106-gia-ban-usd-cho-den-tang-len-26380-dongusd-post1205814.vov |
| 2025-09-30 | 25,187 | https://infographics.vn/interactive-ty-gia-trung-tam-ngay-30-9-2025-1-usd-25187-vnd/217475.vna | https://vietnambiz.vn/ty-gia-usd-hom-nay-309-cung-co-da-tang-truoc-nguy-co-dong-cua-chinh-phu-2025929102116994.htm |
| 2025-10-10 | 25,128 | https://www.vietnamplus.vn/ty-gia-ngay-1010-dong-usd-tai-cac-ngan-hang-thuong-mai-van-theo-da-giam-post1069379.vnp | https://thitruongtaichinhtiente.vn/ngay-10-10-ty-gia-trung-tam-tiep-tuc-giam-72026.html |
| 2026-09-10 | 25,591 | https://thoibaonganhang.vn/sang-109-nhnn-niem-yet-ty-gia-trung-tam-o-muc-25591-dong-187339.html | https://nhipcaukinhte.com.vn/thi-truong/ty-gia-ha-nhiet-nhung-an-so-tu-thi-truong-my-van-con-lon.html |

The series excludes commercial bank buy/sell rates, black-market USD rates and the NSO USD price index.

## Verified SJC gold-bar quotes — VND/tael (1 tael / 10 taels / 1kg bar series)

| Source date | Session | Local quote time | Buy | Sell | First source | Independent corroboration |
|---|---|---|---:|---:|---|---|
| 2025-04-10 | Afternoon / close | ~15:36 | 100,600,000 | 103,600,000 | https://vietnamnet.vn/gia-vang-hom-nay-10-4-2025-tang-manh-cho-ky-luc-moi-2389489.html | https://baonghean.vn/gia-vang-chieu-nay-10-4-2025-gia-vang-trong-nuoc-va-the-gioi-giam-nhe-vi-sieu-thue-125-10294843.html |
| 2025-06-10 | Morning | ~09:00 | 115,700,000 | 117,700,000 | https://vietnamnet.vn/gia-vang-hom-nay-10-6-giam-vang-sjc-nguoc-chieu-di-len-2409808.html | https://infographics.vn/interactive-sang-ngay-10-6-2025-gia-vang-mieng-o-nguong-1157-1177-trieu-dong-luong/215940.vna |
| 2025-10-10 | Afternoon / close | ~16:30 | 140,200,000 | 142,200,000 | https://vietnamnet.vn/gia-vang-hom-nay-10-10-2025-buoc-vao-ngay-lich-su-sjc-se-the-nao-2450991.html | https://baonghean.vn/gia-vang-chieu-nay-10-10-2025-gia-vang-acb-sjc-pnj-vang-nhan-vang-the-gioi-10307995.html |
| 2026-09-10 | Morning | ~09:20 | 143,600,000 | 146,600,000 | https://vietnamnet.vn/gia-vang-hom-nay-10-9-2026-vang-bat-tang-khi-usd-suy-yeu-2553651.html | https://www.vietnamplus.vn/gia-vang-trong-nuoc-di-ngang-ty-gia-tai-ngan-hang-thuong-mai-giam-manh-post1135283.vnp |

Quotes for morning and close are separate sessions. For the same source date only one clearly labeled snapshot is kept in this initial daily series. Do not substitute one session's number for the other. The historical record contains `quote_session`, `quote_time_local` and `product`.

## Data quality and integration
- At least two **distinct publisher ownership groups** must agree on each value; one outlet copying the other does not count as independent corroboration.
- The frontend validates allowed indicator, period, unit, source ID, trusted publisher domain, identical corroborated value, quote session, and gold-bar product.
- In case the live canonical observations contain the same indicator/date, the live record wins. Historical archive never overwrites the automatic live `data/processed/macro/observations.json`.
- Archive is not automatically extended from today's source list: fresh business-day FX/SJC continues through the scheduled candidate collector + controlled promotion path. Additional historical dates require source matching, review, CI, and an append-only PR.
- A source article may have intraday changes: this archive stores **the quoted time/basis**, not an arbitrary daily high/low or a presumed settlement.
- Web QA: `tests/test_macro_historical_fx_gold.cjs`; CPI history QA: `tests/test_macro_official_history.py`.
