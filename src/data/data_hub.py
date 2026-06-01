"""
DataHub — Merkezi veri yonlendirici.

Tum veri kaynaklari buraya register edilir; consumer'lar buradan ceker.
Mevcut fetcher'lar degismez — hub onlari wrapper olarak kullanir.

Kullanim:
    from src.data.data_hub import DataHub

    df   = DataHub.get("yfinance", ticker="AKBNK.IS", lookback="6mo")
    tlref = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS", lookback="1y")
    news = DataHub.get("news", ticker="AKBNK")

    for src in DataHub.list_sources():
        print(src["name"], "-", src["description"])
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class DataSource:
    """Tek bir veri kaynagi tanimi."""

    name: str
    description: str
    data_type: str  # "price" | "macro" | "kap" | "foreign" | "news" | "viop"
    fetcher: Callable[..., Any]
    fallback: Optional[str] = None
    auth_required: bool = False
    tags: list[str] = field(default_factory=list)


class DataHub:
    """
    Merkezi veri router — class-level registry, singleton degil.

    Mimari kural: bu modul engine.py veya MASTER_WEIGHTS import etmez.
    Tum kaynak importlari _hub_sources.py icindeki fonksiyon govdelerinde
    lazy olarak yapilir (modul seviyesinde import yok).
    """

    _registry: dict[str, DataSource] = {}
    _bootstrapped: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def register(cls, source: DataSource) -> None:
        """Yeni kaynak ekle. Var olani ezer (hot-reload destegi)."""
        cls._registry[source.name] = source

    @classmethod
    def get(cls, source_name: str, **kwargs: Any) -> Any:
        """
        Veri cek. Cache-first; basarisiz olursa fallback kaynaga gecer.

        Args:
            source_name: Kayit adi ("yfinance", "evds", "kap", ...)
            **kwargs:    Kaynaga ozgu parametreler (ticker, series, lookback, ...)

        Returns:
            Kaynaktan donen nesne (genellikle pd.DataFrame veya list[dict]).

        Raises:
            KeyError:   Kaynak kayitli degil.
            Exception:  Kaynak ve fallback ikisi de basarisiz.
        """
        cls._ensure_bootstrapped()
        if source_name not in cls._registry:
            available = list(cls._registry)
            raise KeyError(
                f"DataHub: '{source_name}' bilinmiyor (kayitli degil). "
                f"Mevcut kaynaklar: {available}"
            )
        src = cls._registry[source_name]
        try:
            return src.fetcher(**kwargs)
        except Exception as exc:
            if src.fallback:
                log.warning(
                    "DataHub: '%s' hata verdi (%s), fallback -> '%s'",
                    source_name,
                    exc,
                    src.fallback,
                )
                return cls.get(src.fallback, **kwargs)
            raise

    @classmethod
    def list_sources(cls) -> list[dict[str, Any]]:
        """Kayitli tum kaynaklarin metadata listesini dondur."""
        cls._ensure_bootstrapped()
        return [
            {
                "name": s.name,
                "description": s.description,
                "data_type": s.data_type,
                "auth_required": s.auth_required,
                "fallback": s.fallback,
                "tags": s.tags,
            }
            for s in cls._registry.values()
        ]

    @classmethod
    def source_names(cls) -> list[str]:
        """Kayitli kaynak adlarini dondur."""
        cls._ensure_bootstrapped()
        return list(cls._registry)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @classmethod
    def _ensure_bootstrapped(cls) -> None:
        if not cls._bootstrapped:
            from src.data._hub_sources import register_all  # lazy import

            register_all(cls)
            cls._bootstrapped = True

    @classmethod
    def _reset(cls) -> None:
        """Test izolasyonu icin registry'yi temizle."""
        cls._registry = {}
        cls._bootstrapped = False
