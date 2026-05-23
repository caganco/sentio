"""HMM Regime-Conditional Weight Detection (D-123, SPEC_HMM_REGIME_WEIGHTS_1).

3-state GaussianHMM (BULL/NEUTRAL/BEAR) tabanlı rejim tespiti.
Input:  BIST100 günlük log-return + 20d rolling vol (annualized) + USD/TRY log-change.
Output: Rejim etiketi → engine weight_override dict.

Feature flag: thresholds.ENABLE_HMM_WEIGHTS=False → bu modül aktif değil.
Caller: scripts/daily_update.py (once/run). engine.py bağımlılık-serbest: string param alır.

Dayanak: RR-003 §3-B; Hamilton (1989); Asness/Moskowitz/Pedersen (2013); Lo (2004).
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.signals.thresholds import (
    HMM_COVARIANCE_TYPE,
    HMM_FEATURE_NAMES,
    HMM_MIN_TRAIN_DAYS,
    HMM_MODEL_PATH,
    HMM_N_COMPONENTS,
    HMM_N_ITER,
    HMM_PREDICT_MIN_DAYS,
    HMM_RANDOM_STATE,
    HMM_RETRAIN_INTERVAL_DAYS,
    HMM_TOL,
    HMM_VOL_LOOKBACK,
    HMM_WALK_FORWARD_WINDOW_MONTHS,
    HMM_WEIGHTS_BEAR,
    HMM_WEIGHTS_BULL,
    HMM_WEIGHTS_NEUTRAL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metadata dataclass
# ---------------------------------------------------------------------------

@dataclass
class HMMModelMetadata:
    """HMM model kimliği ve eğitim penceresi bilgisi."""
    train_date: str               # ISO date: "2026-05-22"
    train_window_start: str       # ISO date
    train_window_end: str         # ISO date
    n_train_samples: int          # eğitimde kullanılan gün sayısı
    state_labels: dict[int, str]  # {0: "BULL", 1: "NEUTRAL", 2: "BEAR"}
    feature_names: list[str]      # ["bist_log_return", "roll_vol_20d", "usdtry_log_change"]
    model_version: str = "v1"


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """BIST100 + USDTRY günlük kapanışlarından HMM gözlem matrisi üretir.

    Features (3-dim):
        [0] bist_log_return    = log(close_t / close_{t-1})
        [1] roll_vol_20d       = rolling(20).std(log_ret) * sqrt(252)  [annualized]
        [2] usdtry_log_change  = log(usdtry_t / usdtry_{t-1})

    StandardScaler ile normalize edilir (μ=0, σ=1 per feature).
    """

    def __init__(self, vol_lookback: int = HMM_VOL_LOOKBACK) -> None:
        self.vol_lookback = vol_lookback
        self._scaler: object = None   # sklearn.preprocessing.StandardScaler

    def extract(
        self,
        bist_closes: pd.Series,
        usdtry_closes: pd.Series,
        fit_scaler: bool = True,
    ) -> np.ndarray:
        """Ham fiyat serilerinden normalize edilmiş feature matrisi üretir.

        Args:
            bist_closes: BIST100 kapanış serileri (index=date, chronological).
            usdtry_closes: USD/TRY kapanış serileri (aynı index veya uyumlu).
            fit_scaler: True → yeni veriye fit et (train için).
                        False → mevcut scaler uygula (predict için).

        Returns:
            np.ndarray shape (T, 3) — NaN satırlar temizlenmiş.
        """
        from sklearn.preprocessing import StandardScaler

        bist_log_ret = np.log(bist_closes / bist_closes.shift(1))
        roll_vol = bist_log_ret.rolling(self.vol_lookback).std() * np.sqrt(252)
        usdtry_log_chg = np.log(usdtry_closes / usdtry_closes.shift(1))

        df = pd.DataFrame({
            "bist_log_return":   bist_log_ret,
            "roll_vol_20d":      roll_vol,
            "usdtry_log_change": usdtry_log_chg,
        }).dropna()

        X = df.values.astype(np.float64)

        if fit_scaler or self._scaler is None:
            self._scaler = StandardScaler()
            X = self._scaler.fit_transform(X)
        else:
            X = self._scaler.transform(X)

        return X

    def extract_recent(
        self,
        bist_closes: pd.Series,
        usdtry_closes: pd.Series,
        n_days: int = HMM_PREDICT_MIN_DAYS,
    ) -> np.ndarray:
        """Son n_days günlük observation matrisi üretir (predict için).

        Scaler daha önce fit edilmiş olmalı (extract(fit_scaler=True) ile).
        """
        tail_n = n_days + self.vol_lookback + 5
        bist_tail = bist_closes.tail(tail_n)
        usdtry_tail = usdtry_closes.tail(tail_n)
        return self.extract(bist_tail, usdtry_tail, fit_scaler=False)


# ---------------------------------------------------------------------------
# BISTRegimeHMM
# ---------------------------------------------------------------------------

class BISTRegimeHMM:
    """3-state GaussianHMM wrapper. BULL / NEUTRAL / BEAR rejim tespiti.

    Kullanım::

        hmm = BISTRegimeHMM.load_or_retrain()
        regime = hmm.predict_current_regime()   # "BULL"/"NEUTRAL"/"BEAR"
    """

    REGIME_LABELS = {"BULL", "NEUTRAL", "BEAR"}

    def __init__(self) -> None:
        self.model: object = None           # hmmlearn.hmm.GaussianHMM
        self.metadata: HMMModelMetadata | None = None
        self.extractor: FeatureExtractor = FeatureExtractor()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, X: np.ndarray, metadata: HMMModelMetadata) -> None:
        """GaussianHMM eğit; state'leri etiketle.

        Args:
            X: Normalize edilmiş feature matrisi (T, 3). NaN içermemeli.
            metadata: Eğitim bağlamı. state_labels bu metod tarafından doldurulur.

        Raises:
            ValueError: Yetersiz veri veya convergence uyarısı.
        """
        import warnings
        from hmmlearn.hmm import GaussianHMM

        if X.shape[0] < HMM_MIN_TRAIN_DAYS:
            raise ValueError(
                f"Yetersiz eğitim verisi: {X.shape[0]} gün < {HMM_MIN_TRAIN_DAYS} minimum"
            )

        hmm = GaussianHMM(
            n_components=HMM_N_COMPONENTS,
            covariance_type=HMM_COVARIANCE_TYPE,
            n_iter=HMM_N_ITER,
            tol=HMM_TOL,
            random_state=HMM_RANDOM_STATE,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            hmm.fit(X)

        convergence_issues = [
            w for w in caught
            if "did not converge" in str(w.message).lower()
            or "convergence" in str(w.category.__name__).lower()
        ]
        if convergence_issues:
            logger.warning(
                "BISTRegimeHMM.train: EM convergence uyarısı — "
                "n_iter=%d artırılabilir veya tol gevşetilebilir", HMM_N_ITER
            )

        state_labels = self._label_states(hmm)
        metadata.state_labels = state_labels
        self.model = hmm
        self.metadata = metadata

        logger.info(
            "BISTRegimeHMM trained: %d samples, states=%s",
            X.shape[0], state_labels,
        )

    def _label_states(self, hmm: object) -> dict[int, str]:
        """State 0/1/2 → BULL/NEUTRAL/BEAR etiketleme.

        Kural: means_[:, 0] (log_return boyutu) sırasına göre:
            - Maksimum → BULL
            - Minimum  → BEAR
            - Orta     → NEUTRAL
        """
        mean_returns = hmm.means_[:, 0]
        sorted_states = np.argsort(mean_returns)   # ascending; [0]=min, [-1]=max
        return {
            int(sorted_states[-1]): "BULL",
            int(sorted_states[0]):  "BEAR",
            int(sorted_states[1]):  "NEUTRAL",
        }

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_regime(self, X_recent: np.ndarray) -> str:
        """En güncel gözlem dizisinden rejim etiketini döndür.

        Args:
            X_recent: (T, 3) ndarray — son T güne ait normalize edilmiş features.

        Returns:
            "BULL", "NEUTRAL", veya "BEAR"
        """
        if self.model is None or self.metadata is None:
            raise RuntimeError(
                "BISTRegimeHMM: Model eğitilmemiş — train() veya load() çağır."
            )
        states = self.model.predict(X_recent)
        current_state = int(states[-1])
        return self.metadata.state_labels[current_state]

    def predict_regime_proba(self, X_recent: np.ndarray) -> dict[str, float]:
        """Son gözlem için rejim posterior olasılıkları.

        Returns:
            {"BULL": 0.72, "NEUTRAL": 0.20, "BEAR": 0.08} — toplamı 1.0.
        """
        if self.model is None or self.metadata is None:
            raise RuntimeError("BISTRegimeHMM: Model eğitilmemiş.")

        posteriors = self.model.predict_proba(X_recent)   # (T, n_components)
        last_posterior = posteriors[-1]
        return {
            self.metadata.state_labels[i]: round(float(last_posterior[i]), 4)
            for i in range(HMM_N_COMPONENTS)
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path | None = None) -> Path:
        """Model + metadata + scaler'ı pickle ile kaydet."""
        save_path = Path(path or HMM_MODEL_PATH)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model":    self.model,
            "metadata": asdict(self.metadata),
            "scaler":   self.extractor._scaler,
        }
        with open(save_path, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("BISTRegimeHMM saved → %s", save_path)
        return save_path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "BISTRegimeHMM":
        """Daha önce kaydedilmiş modeli yükle."""
        load_path = Path(path or HMM_MODEL_PATH)
        with open(load_path, "rb") as f:
            payload = pickle.load(f)
        inst = cls()
        inst.model = payload["model"]
        inst.extractor._scaler = payload["scaler"]
        meta_dict = payload["metadata"]
        # state_labels keys are stored as strings in JSON-serialized dicts via asdict;
        # restore int keys for correct indexing
        raw_labels = meta_dict.get("state_labels", {})
        meta_dict["state_labels"] = {int(k): v for k, v in raw_labels.items()}
        inst.metadata = HMMModelMetadata(**meta_dict)
        logger.info(
            "BISTRegimeHMM loaded from %s (trained %s)",
            load_path, inst.metadata.train_date,
        )
        return inst

    @classmethod
    def load_or_retrain(
        cls,
        model_path: str | Path | None = None,
        force: bool = False,
    ) -> "BISTRegimeHMM":
        """Kaydedilmiş model varsa ve HMM_RETRAIN_INTERVAL_DAYS'den genç ise yükle.

        Aksi halde yeniden eğit ve kaydet.

        Args:
            model_path: Override için; None → HMM_MODEL_PATH
            force: True → her zaman yeniden eğit

        Returns:
            Hazır BISTRegimeHMM instance.
        """
        mpath = Path(model_path or HMM_MODEL_PATH)
        if not force and mpath.exists():
            try:
                inst = cls.load(mpath)
                train_date = date.fromisoformat(inst.metadata.train_date)
                age_days = (date.today() - train_date).days
                if age_days <= HMM_RETRAIN_INTERVAL_DAYS:
                    logger.info(
                        "BISTRegimeHMM: cached model kullanılıyor (yaş=%d gün)", age_days
                    )
                    return inst
                logger.info(
                    "BISTRegimeHMM: model %d gün eski (> %d) → retrain",
                    age_days, HMM_RETRAIN_INTERVAL_DAYS,
                )
            except Exception as exc:
                logger.warning("BISTRegimeHMM.load başarısız (%s) → retrain", exc)

        return cls._retrain_and_save(mpath)

    @classmethod
    def _retrain_and_save(cls, save_path: Path) -> "BISTRegimeHMM":
        """Veriyi çek, feature matrisi oluştur, eğit, kaydet."""
        bist_closes, usdtry_closes = _fetch_hmm_features()

        today = date.today()
        # Approximate 36 months using timedelta
        from datetime import timedelta
        start_date = today - timedelta(days=HMM_WALK_FORWARD_WINDOW_MONTHS * 30)

        if hasattr(bist_closes.index, "date"):
            bist_window = bist_closes[bist_closes.index.date >= start_date]
            usdtry_window = usdtry_closes[usdtry_closes.index.date >= start_date]
        else:
            bist_window = bist_closes[bist_closes.index >= str(start_date)]
            usdtry_window = usdtry_closes[usdtry_closes.index >= str(start_date)]

        extractor = FeatureExtractor()
        X = extractor.extract(bist_window, usdtry_window, fit_scaler=True)

        meta = HMMModelMetadata(
            train_date=today.isoformat(),
            train_window_start=start_date.isoformat(),
            train_window_end=today.isoformat(),
            n_train_samples=X.shape[0],
            state_labels={},           # train() will populate
            feature_names=list(HMM_FEATURE_NAMES),
        )

        inst = cls()
        inst.extractor = extractor
        inst.train(X, meta)
        inst.save(save_path)
        return inst

    def predict_current_regime(
        self,
        n_predict_days: int = HMM_PREDICT_MIN_DAYS,
    ) -> str:
        """Canlı kullanım için kısa yol: son N günlük veriyi çek → predict.

        Returns:
            "BULL", "NEUTRAL", veya "BEAR"
        """
        bist_closes, usdtry_closes = _fetch_hmm_features()
        X_recent = self.extractor.extract_recent(
            bist_closes, usdtry_closes, n_days=n_predict_days
        )
        regime = self.predict_regime(X_recent)
        proba = self.predict_regime_proba(X_recent)
        logger.info("HMM current regime: %s | proba=%s", regime, proba)
        return regime


# ---------------------------------------------------------------------------
# Data fetching helper
# ---------------------------------------------------------------------------

def _fetch_hmm_features() -> tuple[pd.Series, pd.Series]:
    """BIST100 + USDTRY kapanış serilerini döndür.

    Önce src.data.database.get_prices() dener; başarısız olursa yfinance.
    """
    try:
        from src.data.database import get_prices
        bist_df = get_prices("XU100.IS", limit_days=365 * 5)
        usdtry_df = get_prices("USDTRY=X", limit_days=365 * 5)
        if (
            bist_df is not None and not bist_df.empty
            and usdtry_df is not None and not usdtry_df.empty
            and "Close" in bist_df.columns and "Close" in usdtry_df.columns
        ):
            combined = pd.DataFrame({
                "bist":   bist_df["Close"],
                "usdtry": usdtry_df["Close"],
            }).dropna()
            if len(combined) >= HMM_MIN_TRAIN_DAYS:
                return combined["bist"], combined["usdtry"]
    except Exception as exc:
        logger.debug("DB price fetch for HMM başarısız: %s → yfinance deneniyor", exc)

    import yfinance as yf
    df = yf.download(
        ["XU100.IS", "USDTRY=X"],
        period="5y",
        progress=False,
        auto_adjust=True,
    )
    close = df["Close"].dropna()
    return close["XU100.IS"], close["USDTRY=X"]


# ---------------------------------------------------------------------------
# Engine integration point
# ---------------------------------------------------------------------------

def get_hmm_weight_override(regime: str) -> dict[str, float]:
    """Rejim etiketinden engine weight_override dict'i döndür.

    Args:
        regime: "BULL", "NEUTRAL", veya "BEAR" (case-insensitive)

    Returns:
        dict[str, float] — normalize edilmiş, tüm MASTER_WEIGHTS key'lerini içerir.

    Raises:
        ValueError: Geçersiz rejim etiketi.
    """
    mapping = {
        "BULL":    HMM_WEIGHTS_BULL,
        "NEUTRAL": HMM_WEIGHTS_NEUTRAL,
        "BEAR":    HMM_WEIGHTS_BEAR,
    }
    regime_upper = regime.upper()
    if regime_upper not in mapping:
        raise ValueError(
            f"Geçersiz HMM rejim etiketi: '{regime}'. "
            f"Geçerli değerler: BULL, NEUTRAL, BEAR"
        )
    return dict(mapping[regime_upper])
