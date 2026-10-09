"""Fail-closed source/month parser tests for unattended OneHousing ingestion."""
from __future__ import annotations
from datetime import date
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from market_alternative_auto_probe import onehousing_monthly

def section(name, month, modal="73.74", lo="57", hi="100.19", complete=True):
    heading=f"Căn hộ chung cư dự án {name} tháng {month}/2026 "
    if not complete:
        return heading + "Dữ liệu tháng mới chưa công bố mức giá "
    return (heading + "Tổng quan dự án. Đơn giá phổ biến "
            "Mức giá xuất hiện nhiều nhất trong các tin rao: "
            + modal + " triệu/m² | Khoảng giá: "+lo+" - "+hi
            +" triệu | Giá thuê phổ biến 16 triệu/tháng. ")

today=date(2026,10,9)
older=section("Lumière Boulevard",9,modal="73.40",lo="57.44",hi="100.06")
newer=section("Lumière Boulevard",10)
other=section("Masteri Centre Point",10,modal="70.90",lo="53.06",hi="224.87")
parsed=onehousing_monthly(older+newer,today,"Lumière Boulevard")
assert parsed and parsed["period"]=="2026-10"
assert parsed["value_vnd_per_m2"]==73_740_000
assert parsed["range_low_vnd_per_m2"]==57_000_000
assert parsed["range_high_vnd_per_m2"]==100_190_000

# HTML order is not chronological; choose publisher date rather than first occurrence.
parsed=onehousing_monthly(newer+older,today,"Lumière Boulevard")
assert parsed and parsed["period"]=="2026-10"
assert onehousing_monthly(older+newer+other,today,"Masteri Centre Point")["value_vnd_per_m2"]==70_900_000

# Never pull a neighbor project's modal price into an incomplete project month.
assert onehousing_monthly(older+section("Lumière Boulevard",10,complete=False)+other,today,"Lumière Boulevard") is None
assert onehousing_monthly(section("Lumière Boulevard",10,complete=False)+other,today,"Lumière Boulevard") is None

# A newer page heading with no complete price is NOT permission to replay old numbers.
assert onehousing_monthly(older+section("Lumière Boulevard",10,complete=False),today,"Lumière Boulevard") is None
assert onehousing_monthly(section("Lumière Boulevard",10,complete=False)+older,today,"Lumière Boulevard") is None

# Duplicate identical publisher blocks are okay; conflicting ones are not.
assert onehousing_monthly(newer+newer,today,"Lumière Boulevard")["period"]=="2026-10"
assert onehousing_monthly(newer+section("Lumière Boulevard",10,modal="74.77"),today,"Lumière Boulevard") is None

# No sibling/parent cross-contamination and no synthetic future months.
assert onehousing_monthly(newer,today,"Vinhomes Grand Park") is None
assert onehousing_monthly(newer,today,"Masteri Centre Point") is None
assert onehousing_monthly(section("Lumière Boulevard",11),today,"Lumière Boulevard") is None
assert onehousing_monthly(older+section("Lumière Boulevard",11),today,"Lumière Boulevard")["period"]=="2026-09"
print("PASS: independently bounded project sections, newest source month, duplicate consistency and fail-closed price parsing.")
