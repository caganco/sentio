"""
DataHub typed veri modelleri — clean kaynaklarin donus tipleri.

  MacroSnapshot  ->  macro_global_clean
  KAPItem        ->  kap_clean

Signals engine, backtest veya MASTER_WEIGHTS'e BAGIMLI DEGIL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MacroSnapshot:
    """Global makro anlik goruntu.

    Tum alanlar None olabilir (ilgili kaynak indirilemiyorsa).
    Kullanim: DataHub.get("macro_global_clean")
    """

    usdtry: Optional[float]
    usdtry_change_pct: Optional[float]
    vix: Optional[float]
    vix_change_pct: Optional[float]
    oil_brent: Optional[float]
    oil_brent_change_pct: Optional[float]
    sp500: Optional[float]
    sp500_change_pct: Optional[float]
    gold: Optional[float]
    gold_change_pct: Optional[float]

    @classmethod
    def from_dict(cls, d: dict) -> "MacroSnapshot":
        """Ham macro_global dict'ten MacroSnapshot olustur."""
        fields = [
            "usdtry", "usdtry_change_pct",
            "vix", "vix_change_pct",
            "oil_brent", "oil_brent_change_pct",
            "sp500", "sp500_change_pct",
            "gold", "gold_change_pct",
        ]
        return cls(**{f: d.get(f) for f in fields})


@dataclass
class KAPItem:
    """Tek bir KAP bildirimi.

    category: "CRITICAL" | "IMPORTANT" | "NOISE"
    Kullanim: DataHub.get("kap_clean", ticker="THYAO")
    """

    source: str
    ticker: Optional[str]
    title: str
    published: str
    category: str
    url: str

    @classmethod
    def from_dict(cls, d: dict) -> "KAPItem":
        """Ham kap_scraper dict'ten KAPItem olustur."""
        return cls(
            source=d.get("source", ""),
            ticker=d.get("ticker"),
            title=d.get("title", ""),
            published=d.get("published", ""),
            category=d.get("category", "NOISE"),
            url=d.get("url", ""),
        )

    @property
    def is_critical(self) -> bool:
        return self.category == "CRITICAL"
