"""D-171: kap_xbrl_scorer birim testleri — sentetik veri, ag cagrisi yok."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from src.analytics.kap_xbrl_scorer import (
    build_universe_xbrl_snapshot,
    score_xbrl_surprise,
)

_AS_OF = "2025-12-31"
_PRIOR_PUB = "2024-03-15"
_CUR_PUB = "2025-03-15"


def _hist(gp_prior: float, gp_cur: float, period: str = "FY") -> pd.DataFrame:
    """Bir ticker icin iki yillik (2024/2025) FR gecmisi (gross_profit dolu)."""
    return pd.DataFrame(
        [
            {
                "date": _PRIOR_PUB, "ticker": "X", "year": 2024, "period": period,
                "revenue": None, "gross_profit": gp_prior, "net_income": None,
                "total_assets": None, "equity": None, "publication_date": _PRIOR_PUB,
            },
            {
                "date": _CUR_PUB, "ticker": "X", "year": 2025, "period": period,
                "revenue": None, "gross_profit": gp_cur, "net_income": None,
                "total_assets": None, "equity": None, "publication_date": _CUR_PUB,
            },
        ]
    )


def _patch_fetch(histories: dict[str, pd.DataFrame]):
    """fetch_fundamentals_with_fallback'i ticker -> hist sozlugu ile mock'lar."""
    def _side_effect(ticker, start_year, end_year):  # noqa: ARG001
        return histories.get(ticker, pd.DataFrame())
    return patch(
        "src.analytics.kap_xbrl_scorer.fetch_fundamentals_with_fallback",
        side_effect=_side_effect,
    )


def _direct_universe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["ticker", "metric", "real_surprise", "publication_date"])


class TestScoreXbrlSurprise:
    """D-171: XBRL surprise -> L3 impact [-40, +40]."""

    # ------------------------------------------------------------------
    def test_yoy_positive_surprise_returns_positive_score(self):
        """gross_profit artisi olan ticker universe'de ustte -> pozitif impact."""
        histories = {
            "AAA": _hist(100.0, 150.0),   # +50%
            "BBB": _hist(100.0, 100.0),   # flat
            "CCC": _hist(100.0, 100.0),   # flat
        }
        with _patch_fetch(histories):
            snap = build_universe_xbrl_snapshot(["AAA", "BBB", "CCC"], _AS_OF, None)
        score = score_xbrl_surprise("AAA", _AS_OF, snap)
        assert score > 0.0

    # ------------------------------------------------------------------
    def test_yoy_negative_surprise_returns_negative_score(self):
        """gross_profit dususu olan ticker universe'de altta -> negatif impact."""
        histories = {
            "AAA": _hist(100.0, 50.0),    # -50%
            "BBB": _hist(100.0, 100.0),   # flat
            "CCC": _hist(100.0, 100.0),   # flat
        }
        with _patch_fetch(histories):
            snap = build_universe_xbrl_snapshot(["AAA", "BBB", "CCC"], _AS_OF, None)
        score = score_xbrl_surprise("AAA", _AS_OF, snap)
        assert score < 0.0

    # ------------------------------------------------------------------
    def test_lookahead_guard_filters_future_publication(self):
        """publication_date > as_of_date -> 0.0 (gelecekteki veri kullanilmaz)."""
        universe = _direct_universe([
            {"ticker": "AAA", "metric": "gross_profit",
             "real_surprise": 0.8, "publication_date": "2026-06-01"},
        ])
        assert score_xbrl_surprise("AAA", _AS_OF, universe) == 0.0

    # ------------------------------------------------------------------
    def test_tufe_deflation_reduces_nominal_growth(self):
        """%50 nominal buyume + %65 TUFE -> reel kayip (negatif surprise)."""
        histories = {"AAA": _hist(100.0, 150.0)}  # nominal +50%
        tufe = pd.Series(
            [100.0, 165.0],
            index=pd.to_datetime(["2024-01-01", "2025-01-01"]),
        )  # +65% CPI
        with _patch_fetch(histories):
            snap_real = build_universe_xbrl_snapshot(["AAA"], _AS_OF, tufe)
            snap_nom = build_universe_xbrl_snapshot(["AAA"], _AS_OF, None)
        real_surprise = float(snap_real.loc[snap_real["ticker"] == "AAA", "real_surprise"].iloc[0])
        nom_surprise = float(snap_nom.loc[snap_nom["ticker"] == "AAA", "real_surprise"].iloc[0])
        assert nom_surprise > 0.0       # deflate edilmemis: pozitif
        assert real_surprise < 0.0      # deflate edilmis: reel kayip

    # ------------------------------------------------------------------
    def test_cross_sectional_rank_top_ticker_scores_positive(self):
        """10 ticker, en yuksek surprise -> +40'a yakin skor."""
        universe = _direct_universe([
            {"ticker": f"T{i}", "metric": "gross_profit",
             "real_surprise": i / 10.0, "publication_date": "2025-06-01"}
            for i in range(10)
        ])
        score = score_xbrl_surprise("T9", _AS_OF, universe)
        assert score > 30.0

    # ------------------------------------------------------------------
    def test_missing_data_returns_zero_not_exception(self):
        """Veri yok -> 0.0 (exception firlatmaz)."""
        empty = _direct_universe([])
        assert score_xbrl_surprise("ZZZ", _AS_OF, empty) == 0.0
        assert score_xbrl_surprise("ZZZ", _AS_OF, None) == 0.0
        # ticker universe'de yok
        universe = _direct_universe([
            {"ticker": "AAA", "metric": "gross_profit",
             "real_surprise": 0.5, "publication_date": "2025-01-01"},
        ])
        assert score_xbrl_surprise("ZZZ", _AS_OF, universe) == 0.0

    # ------------------------------------------------------------------
    def test_cap_applied_to_extreme_values(self):
        """surprise > %100 -> [-1,1] cap; output her zaman [-40, +40]."""
        # Snapshot cap: +400% nominal -> real_surprise == 1.0
        histories = {"AAA": _hist(100.0, 500.0)}
        with _patch_fetch(histories):
            snap = build_universe_xbrl_snapshot(["AAA"], _AS_OF, None)
        assert float(snap.loc[snap["ticker"] == "AAA", "real_surprise"].iloc[0]) == 1.0

        # Output cap: asiri surprise degerlerinde bile skor [-40, +40] icinde
        universe = _direct_universe([
            {"ticker": "AAA", "metric": "gross_profit",
             "real_surprise": 99.0, "publication_date": "2025-01-01"},
            {"ticker": "BBB", "metric": "gross_profit",
             "real_surprise": -99.0, "publication_date": "2025-01-01"},
        ])
        score = score_xbrl_surprise("AAA", _AS_OF, universe)
        assert -40.0 <= score <= 40.0
