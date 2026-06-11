from __future__ import annotations

from datetime import date
from typing import TypedDict


REFERENCE_VALID_FROM = date(1900, 1, 1)
DEFAULT_SHARE_ASSET_TYPE = "share"


class DataSourceSeed(TypedDict):
    code: str
    name: str
    source_type: str
    url: str | None
    license_note: str | None


class SectorSeed(TypedDict):
    code: str
    name: str
    description: str | None


class IssuerMappingSeed(TypedDict):
    secids: tuple[str, ...]
    issuer_name: str
    sector_code: str


class BenchmarkSeed(TypedDict):
    code: str
    name: str
    benchmark_type: str
    sector_code: str | None
    description: str | None


DATA_SOURCE_SEEDS: tuple[DataSourceSeed, ...] = (
    {
        "code": "moex",
        "name": "Moscow Exchange",
        "source_type": "moex",
        "url": "https://iss.moex.com/iss",
        "license_note": None,
    },
    {
        "code": "cbr",
        "name": "Bank of Russia",
        "source_type": "cbr",
        "url": "https://www.cbr.ru",
        "license_note": None,
    },
    {
        "code": "manual_seed",
        "name": "Manual curated seed data",
        "source_type": "manual_seed",
        "url": None,
        "license_note": "Curated manually for demo/reference classification",
    },
)


SECTOR_SEEDS: tuple[SectorSeed, ...] = (
    {"code": "finance", "name": "Finance", "description": None},
    {"code": "oil_gas", "name": "Oil & Gas", "description": None},
    {"code": "metals_mining", "name": "Metals & Mining", "description": None},
    {"code": "it", "name": "Information Technology", "description": None},
    {"code": "telecom", "name": "Telecommunications", "description": None},
    {"code": "consumer", "name": "Consumer", "description": None},
    {"code": "utilities", "name": "Utilities", "description": None},
    {"code": "transport", "name": "Transport", "description": None},
    {"code": "real_estate", "name": "Real Estate", "description": None},
    {"code": "chemicals", "name": "Chemicals", "description": None},
    {"code": "market_index", "name": "Market Index", "description": None},
)


CURATED_ISSUER_MAPPINGS: tuple[IssuerMappingSeed, ...] = (
    {"secids": ("SBER", "SBERP"), "issuer_name": "Sberbank", "sector_code": "finance"},
    {"secids": ("VTBR",), "issuer_name": "VTB", "sector_code": "finance"},
    {"secids": ("MOEX",), "issuer_name": "Moscow Exchange", "sector_code": "finance"},
    {"secids": ("T", "TCSG"), "issuer_name": "T-Bank / TCS Group", "sector_code": "finance"},
    {"secids": ("GAZP",), "issuer_name": "Gazprom", "sector_code": "oil_gas"},
    {"secids": ("LKOH",), "issuer_name": "Lukoil", "sector_code": "oil_gas"},
    {"secids": ("ROSN",), "issuer_name": "Rosneft", "sector_code": "oil_gas"},
    {"secids": ("NVTK",), "issuer_name": "Novatek", "sector_code": "oil_gas"},
    {"secids": ("TATN", "TATNP"), "issuer_name": "Tatneft", "sector_code": "oil_gas"},
    {"secids": ("SNGS", "SNGSP"), "issuer_name": "Surgutneftegas", "sector_code": "oil_gas"},
    {"secids": ("GMKN",), "issuer_name": "Nornickel", "sector_code": "metals_mining"},
    {"secids": ("NLMK",), "issuer_name": "NLMK", "sector_code": "metals_mining"},
    {"secids": ("CHMF",), "issuer_name": "Severstal", "sector_code": "metals_mining"},
    {"secids": ("MAGN",), "issuer_name": "MMK", "sector_code": "metals_mining"},
    {"secids": ("ALRS",), "issuer_name": "ALROSA", "sector_code": "metals_mining"},
    {"secids": ("RUAL",), "issuer_name": "RUSAL", "sector_code": "metals_mining"},
    {"secids": ("PLZL",), "issuer_name": "Polyus", "sector_code": "metals_mining"},
    {"secids": ("YDEX", "YNDX"), "issuer_name": "Yandex", "sector_code": "it"},
    {"secids": ("VKCO",), "issuer_name": "VK", "sector_code": "it"},
    {"secids": ("OZON",), "issuer_name": "Ozon", "sector_code": "consumer"},
    {"secids": ("MTSS",), "issuer_name": "MTS", "sector_code": "telecom"},
    {"secids": ("RTKM", "RTKMP"), "issuer_name": "Rostelecom", "sector_code": "telecom"},
    {"secids": ("MGNT",), "issuer_name": "Magnit", "sector_code": "consumer"},
    {"secids": ("FIVE",), "issuer_name": "X5 Group", "sector_code": "consumer"},
    {"secids": ("HYDR",), "issuer_name": "RusHydro", "sector_code": "utilities"},
    {"secids": ("FEES",), "issuer_name": "Federal Grid Company / Rosseti", "sector_code": "utilities"},
    {"secids": ("AFLT",), "issuer_name": "Aeroflot", "sector_code": "transport"},
    {"secids": ("PHOR",), "issuer_name": "PhosAgro", "sector_code": "chemicals"},
)


BENCHMARK_SEEDS: tuple[BenchmarkSeed, ...] = (
    {
        "code": "russian_market",
        "name": "Russian Market Benchmark",
        "benchmark_type": "market",
        "sector_code": None,
        "description": "Placeholder market benchmark. Link to IMOEX instrument later when reliable metadata is available.",
    },
    {
        "code": "finance_sector",
        "name": "Finance Sector Benchmark",
        "benchmark_type": "sector",
        "sector_code": "finance",
        "description": "Sector benchmark placeholder for future event-study comparisons.",
    },
    {
        "code": "oil_gas_sector",
        "name": "Oil & Gas Sector Benchmark",
        "benchmark_type": "sector",
        "sector_code": "oil_gas",
        "description": "Sector benchmark placeholder for future event-study comparisons.",
    },
    {
        "code": "metals_mining_sector",
        "name": "Metals & Mining Sector Benchmark",
        "benchmark_type": "sector",
        "sector_code": "metals_mining",
        "description": "Sector benchmark placeholder for future event-study comparisons.",
    },
    {
        "code": "it_sector",
        "name": "Information Technology Sector Benchmark",
        "benchmark_type": "sector",
        "sector_code": "it",
        "description": "Sector benchmark placeholder for future event-study comparisons.",
    },
)
