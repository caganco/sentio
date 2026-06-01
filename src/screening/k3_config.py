"""D-192 K3 Illiquidity + Reversal backtest -- frozen Stage-0 config.

TUM-BIST evreni (BIST100 + mid/small-cap + KNOWN_DELISTED) kuralli-veri-kalite-
filtresinden gecirilir. Elle-secim YASAK; filtre OBJEKTiF esik uygular.
Bu dosya OLCUM parametresi (thresholds.py uretim-sabitleri degil).
Stage-0'da commit edilir, sonuc gorulmeden ONCE donar. Post-hoc gevsetme YASAK.

DEC-039 altinda frozen.
"""
from __future__ import annotations

DIRECTIVE = "D-192"
CONFIG_VERSION = "k3-d192-v1"

# ---------------------------------------------------------------------------
# Data window
# ---------------------------------------------------------------------------
DATA_START = "2010-01-01"
DATA_END = "2026-05-15"          # son guvenilir yfinance tarihi

IN_SAMPLE_END = "2019-12-31"     # in-sample: 2010-2019 (10 yil)
OUT_SAMPLE_START = "2020-01-01"  # out-of-sample: 2020-2026 (6 yil)

# Decay split: H2 reversal hala var mi? 2020-sonrasi AYRI olcum.
# Cagan karari: 2020-01-01 (daha katı test; IN=10yr / OUT=6yr dengeli)
DECAY_SPLIT = "2020-01-01"

# ---------------------------------------------------------------------------
# Evren: TUM-BIST + kuralli-veri-kalite-filtresi + KNOWN_DELISTED
# BIST100 DEGIL (en-likit-100; illikidite-varyasyonu yetersiz -> false-negative)
# ---------------------------------------------------------------------------
KNOWN_DELISTED = ["KOZAA.IS", "KOZAL.IS", "IPEKE.IS", "TRALT.IS", "NTHOL.IS"]

# Genis BIST evreni: BIST30 + BIST100 bilesen + secili mid/small-cap
# Veri-kalite-filtresi bu listeden gecerli hisseleri objektif secim yapar
BIST_ALL_TICKERS = [
    # BIST30 ana bilesenler
    "AKBNK.IS", "ARCLK.IS", "ASELS.IS", "BIMAS.IS", "EKGYO.IS",
    "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "HALKB.IS",
    "ISCTR.IS", "KCHOL.IS", "MGROS.IS", "PETKM.IS", "PGSUS.IS",
    "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS",
    "TKFEN.IS", "TOASO.IS", "TUPRS.IS", "VAKBN.IS", "VESTL.IS",
    "YKBNK.IS", "TAVHL.IS", "OYAKC.IS", "KOZAA.IS", "KOZAL.IS",
    # BIST100 ek bilesenler
    "AKSEN.IS", "ALARK.IS", "AYGAZ.IS", "BRSAN.IS", "BRYAT.IS",
    "CCOLA.IS", "CIMSA.IS", "CLEBI.IS", "DOAS.IS", "DOHOL.IS",
    "ECZYT.IS", "EGEEN.IS", "GUBRF.IS", "IPEKE.IS", "ISGYO.IS",
    "ISMEN.IS", "KARSN.IS", "KERVT.IS", "KORDS.IS", "LOGO.IS",
    "MAVI.IS", "NUHCM.IS", "ODAS.IS", "OTKAR.IS", "PARSN.IS",
    "PETUN.IS", "SARKY.IS", "SELGD.IS", "SKBNK.IS", "SOKM.IS",
    "TATGD.IS", "TKFEN.IS", "TRKCM.IS", "TURSG.IS", "ULKER.IS",
    "VESBE.IS", "YATAS.IS", "TRALT.IS", "NTHOL.IS",
    # Ek mid-cap (2010+ islem gecmisi olanlari)
    "ADNAC.IS", "AGESA.IS", "AGHOL.IS", "AKFGY.IS", "AKGRT.IS",
    "ALCTL.IS", "ALKIM.IS", "ANACM.IS", "ARASE.IS", "ASTOR.IS",
    "ATLAS.IS", "AVGYO.IS", "AVISA.IS", "AYCES.IS", "BAGFS.IS",
    "BAKAB.IS", "BANVT.IS", "BARMA.IS", "BERA.IS", "BFREN.IS",
    "BIOEN.IS", "BIZIM.IS", "BMELK.IS", "BSOKE.IS", "BUCIM.IS",
    "BURCE.IS", "BURVA.IS", "CEMTS.IS", "CEOEM.IS", "COHO.IS",
    "DENTA.IS", "DGZTE.IS", "DMSAS.IS", "DNISI.IS", "DOCO.IS",
    "DURDO.IS", "DYOBY.IS", "EGPRO.IS", "EMKEL.IS", "ENJSA.IS",
    "ENRUP.IS", "EPLAS.IS", "EREGL.IS", "ESCOM.IS", "ESEMS.IS",
    "FENER.IS", "FLAP.IS", "FMIZP.IS", "FONET.IS", "FORTE.IS",
    "FRIGO.IS", "FROSK.IS", "GENTS.IS", "GEREL.IS", "GLYHO.IS",
    "GRNYO.IS", "GRSEL.IS", "GSDHO.IS", "GSRAY.IS", "GUBRF.IS",
    "HALKB.IS", "HATEK.IS", "HAYAT.IS", "HDFAS.IS", "HTTBT.IS",
    "HUNER.IS", "ICBCT.IS", "IDGYO.IS", "IHLGM.IS", "IHEVA.IS",
    "IHLAS.IS", "IKYHO.IS", "INDES.IS", "INTEM.IS", "INVEO.IS",
    "ISCTR.IS", "ISFIN.IS", "ISGYO.IS", "ISYHO.IS", "ITTFK.IS",
    "IZFAS.IS", "IZINV.IS", "IZMDC.IS", "JANTS.IS", "KAPLM.IS",
    "KARTN.IS", "KATMR.IS", "KAYSE.IS", "KBORU.IS", "KCHOL.IS",
    "KCVGR.IS", "KENT.IS", "KLGYO.IS", "KLKIM.IS", "KLMSN.IS",
    "KLNMA.IS", "KMPUR.IS", "KNFRT.IS", "KONYA.IS", "KONTR.IS",
    "KORDS.IS", "KRDMD.IS", "KRDMB.IS", "KRPLS.IS", "KRSAN.IS",
    "KUTPO.IS", "LKMNH.IS", "LINK.IS", "LKMNH.IS", "LOGO.IS",
    "LRSHO.IS", "LUKSK.IS", "MAALT.IS", "MARTI.IS", "MEPET.IS",
    "MERCN.IS", "MERIT.IS", "METRO.IS", "MIATK.IS", "MIGROS.IS",
    "MMCAS.IS", "MNDRS.IS", "MOBTL.IS", "MPARK.IS", "MRGYO.IS",
    "MRSHL.IS", "NTTUR.IS", "NUGYO.IS", "NUHCM.IS", "ODESK.IS",
    "OFSYM.IS", "OSMEN.IS", "OYYAT.IS", "PAPIL.IS", "PCILT.IS",
    "PEHOL.IS", "PENGD.IS", "PENTA.IS", "PFKRT.IS", "PKENT.IS",
    "PLTUR.IS", "POLHO.IS", "PRKME.IS", "PRKAB.IS", "QUAGR.IS",
    "RTALB.IS", "RYSAS.IS", "SAFKN.IS", "SANFM.IS", "SANEL.IS",
    "SAYAS.IS", "SDTTR.IS", "SEYKM.IS", "SIGDE.IS", "SILVR.IS",
    "SKBNK.IS", "SKYLP.IS", "SLCTR.IS", "SMART.IS", "SNICA.IS",
    "SNKRN.IS", "SOHO.IS", "SOKM.IS", "SONME.IS", "SPEEK.IS",
    "TARKM.IS", "TASYP.IS", "TATGD.IS", "TCELL.IS", "TGSAS.IS",
    "TLMAN.IS", "TMSN.IS", "TOASO.IS", "TRCAS.IS", "TRILC.IS",
    "TSGYO.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS",
    "TKNSA.IS", "ULAG.IS", "ULAS.IS", "ULUSE.IS", "UNLU.IS",
    "UURUN.IS", "VANGD.IS", "VKFYO.IS", "VKGYO.IS", "YAPRK.IS",
    "YKGYO.IS", "YUNSA.IS", "ZRGYO.IS",
]

# ---------------------------------------------------------------------------
# Veri-kalite filtresi (objektif, elle-secim YASAK -- selection-bias yok)
# ---------------------------------------------------------------------------
UNIVERSE_MIN_TRADING_DAYS_PCT = 0.80  # son DATA pencerede en az %80 islem-gunu
UNIVERSE_MAX_ZERO_VOL_PCT = 0.10      # hacim-0/NaN orani < %10
UNIVERSE_MIN_HISTORY_DAYS = 252       # en az 1 yil tarih (yeni-halka-arz filtresi)
UNIVERSE_MIN_STOCKS_VIABLE = 50       # filtre-sonrasi < 50 hisse -> "infeasible"

# ---------------------------------------------------------------------------
# Amihud ILLIQ (Amihud 2002)
# ---------------------------------------------------------------------------
ILLIQ_WINDOW_DAYS = 20        # rolling aylik pencere
ILLIQ_LAG_MONTHS = 2          # t-2 ay olcum -> t ay getiri (look-ahead guard)
ILLIQ_EPSILON = 1e-9           # log(ILLIQ + eps) icin
ILLIQ_TERCILE_BINS = 3         # T1=illikit, T2=orta, T3=likit
ILLIQ_MIN_OBS = 15             # rolling pencerede en az 15 gun

# Lou-Shu ayrimi: Amihud = price-impact x volume. log(Volume*Close) proxy.
# Shares-outstanding yok yfinance BIST'te -> bu en iyi proxy.
TURNOVER_PROXY = "log_vol_close"   # log(Volume * Close)

# ---------------------------------------------------------------------------
# Short-term reversal (Jegadeesh 1990 / Lehmann 1990)
# ---------------------------------------------------------------------------
REV_WEEK_DAYS = 5     # 1-haftalik lookback
REV_MONTH_DAYS = 21   # 1-aylik lookback
REV_SKIP_DAYS = 1     # look-ahead guard: sinyal t, aksiyon t+1
REV_QUINTILE = 5      # quintile sort; bottom-20% kaybedenler (reversal long)

# ---------------------------------------------------------------------------
# Rebalance ve maliyet
# ---------------------------------------------------------------------------
ILLIQ_REBALANCE_DAYS = 21   # aylik rebalance
REV_REBALANCE_DAYS = 5      # haftalik rebalance (literatur standardi)

# Agresif-slippage modeli (RR-OMEGA uyarisi: illikidite-primini yiyebilir)
# Likit (T3): 20bp komisyon + 30bp spread + 10bp etki = 60bp RT
# Illikit (T1): 20bp komisyon + 130bp spread + 50bp etki = 200bp RT
COST_LIQUID_RT_BPS = 60
COST_ILLIQUID_RT_BPS = 200

# ---------------------------------------------------------------------------
# Null test
# ---------------------------------------------------------------------------
NULL_SEED = 12345
NULL_N_RESAMPLES = 1000
NULL_BOOTSTRAP_BLOCK = 21   # aylik blok
NULL_BOOTSTRAP_N = 2000

# ---------------------------------------------------------------------------
# Karar esigi (Stage-0'da donar)
# ---------------------------------------------------------------------------
NULL_PCTILE_THRESHOLD = 0.95   # fair-null'a karsi >=95. percentile
LOU_SHU_TSTAT_MIN = 1.96       # turnover kontrol sonrasi b-katsayi t-stat

# ---------------------------------------------------------------------------
# Inflation regimes (D-186/D-187 ile ayni)
# ---------------------------------------------------------------------------
INFLATION_REGIMES = [
    ("pre_surge", "2010-01-01", "2021-09-30"),
    ("high_inflation", "2021-10-01", "2024-06-30"),
    ("disinflation", "2024-07-01", "2026-05-15"),
]

# ---------------------------------------------------------------------------
# Olcum butcesi
# ---------------------------------------------------------------------------
MAX_PARAM_VARIATIONS = 3   # N<=3 kural (post-hoc YASAK)

# ---------------------------------------------------------------------------
# Referans sembolleri
# ---------------------------------------------------------------------------
XU100_SYMBOL = "XU100.IS"
USDTRY_SYMBOL = "USDTRY=X"
