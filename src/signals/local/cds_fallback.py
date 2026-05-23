"""CDS client with fallback chain: primary (scraping) → secondary (iShares proxy) → cache."""
import logging
from datetime import datetime

from .cache_store import LocalMacroCache
from .cds_client import CDSClient

logger = logging.getLogger(__name__)


class CDSFallbackClient:
    """CDS data source with tiered fallback: primary → secondary (iShares) → cache."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache
        self.cds_client = CDSClient(cache)
        self.model_params = self._load_model_params()

    def fetch_and_store(self) -> bool:
        """
        Try to fetch CDS via: primary → secondary (iShares proxy) → cache.

        Returns True if any source succeeded and stored data.
        """
        # 1. Try primary (worldgovernmentbonds.com scraping)
        if self.cds_client.fetch_and_store():
            logger.info("CDS: Primary source (scraping) success")
            return True

        logger.warning("CDS: Primary source failed, trying secondary (iShares proxy)")

        # 2. Try secondary (iShares TUR ETF proxy model)
        try:
            cds_est = self._estimate_cds_via_ishares()
            if cds_est is not None:
                self.cache.store_cds(
                    data_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    cds_bps=cds_est,
                    source="ishares_proxy",
                    confidence=0.6,
                )
                logger.warning(f"CDS: Secondary source (iShares proxy) ~ {cds_est:.0f} bps")
                return True
        except Exception as e:
            logger.warning(f"CDS: Secondary source failed: {e.__class__.__name__}")

        logger.warning("CDS: Secondary failed, checking cache (< 24h)")

        # 3. Try tertiary (cache fallback, if recent)
        cached = self.cache.get_latest_cds()
        if cached:
            cache_date = datetime.fromisoformat(cached["data_date"])
            age_hours = (datetime.utcnow() - cache_date).total_seconds() / 3600

            if age_hours < 24:
                logger.warning(
                    f"CDS: Cache fallback {cached['cds_bps']:.0f} bps "
                    f"({age_hours:.1f}h old, source: {cached.get('source', '?')})"
                )
                return True
            else:
                logger.error(
                    f"CDS: Cache too old ({age_hours:.1f}h), skipping"
                )

        # 4. All failed
        logger.error("CDS: All sources failed, no recent cache")
        return False

    def _estimate_cds_via_ishares(self) -> float | None:
        """
        Estimate Turkey 5Y CDS using iShares TUR + macro model.

        Model: CDS_est = base + α*(USD/TRY - baseline) + β*VIX + γ*TUR_excess_return
        """
        # Fetch input data
        usd_try = self._get_usd_try()
        vix = self._get_vix()
        tur_return = self._get_tur_etf_return()

        if None in [usd_try, vix, tur_return]:
            logger.warning("CDS proxy: Missing input data (USD/TRY, VIX, or TUR)")
            return None

        # Model calculation
        p = self.model_params
        fx_impact = p["alpha"] * (usd_try - p["usd_try_baseline"])
        vix_impact = p["beta"] * vix
        equity_impact = p["gamma"] * tur_return

        cds_est = p["base"] + fx_impact + vix_impact + equity_impact

        # Bounds: realistic Turkey CDS [100, 800] bps
        cds_est = max(100.0, min(800.0, cds_est))

        logger.debug(
            f"CDS proxy model: {cds_est:.0f} = {p['base']:.0f} "
            f"+ {fx_impact:.0f}(FX) + {vix_impact:.0f}(VIX) + {equity_impact:.0f}(TUR)"
        )

        return cds_est

    def _get_usd_try(self) -> float | None:
        """Fetch USD/TRY exchange rate via yfinance."""
        try:
            import yfinance as yf

            usd_try = yf.Ticker("USDTRY=X").history(period="1d")
            if usd_try.empty:
                return None
            return float(usd_try["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"Failed to fetch USD/TRY: {e}")
            return None

    def _get_vix(self) -> float | None:
        """Fetch VIX index via yfinance."""
        try:
            import yfinance as yf

            vix = yf.Ticker("^VIX").history(period="1d")
            if vix.empty:
                return None
            return float(vix["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"Failed to fetch VIX: {e}")
            return None

    def _get_tur_etf_return(self) -> float | None:
        """Fetch iShares TUR ETF 1-day return."""
        try:
            import yfinance as yf

            tur = yf.Ticker("TUR").history(period="5d")
            if tur.empty or len(tur) < 2:
                return None

            # 1-day return (as percentage)
            return_1d = float(tur["Close"].pct_change().iloc[-1]) * 100
            return return_1d
        except Exception as e:
            logger.warning(f"Failed to fetch TUR ETF: {e}")
            return None

    def _load_model_params(self) -> dict:
        """Load CDS estimation model parameters."""
        # Quarterly-calibrated coefficients
        # These should be loaded from config file in production
        return {
            "base": 250.0,  # Base CDS level (bps)
            "alpha": 30.0,  # USD/TRY sensitivity (bps per FX point)
            "beta": 2.0,    # VIX sensitivity (bps per VIX point)
            "gamma": -100.0,  # TUR equity sensitivity (bps per 1% return)
            "usd_try_baseline": 30.0,  # Reference FX level
        }

    def get_latest_cds(self) -> dict | None:
        """Get latest CDS data from cache."""
        return self.cache.get_latest_cds()

    def score(self):
        """Generate CDS signal score (delegated to CDSClient)."""
        return self.cds_client.score()

    def cds_to_score(self, cds_bps: float) -> tuple[float, str]:
        """Convert CDS to signal score (delegated to CDSClient)."""
        return self.cds_client.cds_to_score(cds_bps)
