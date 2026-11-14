from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# One cleaned candle file is shared by the dashboard and the models.
DATA_CSV = ROOT.parent / "frontend" / "public" / "data" / "ko_5min.csv"
ARTIFACTS = ROOT / "artifacts"
REPORTS = ROOT / "reports"

BAR_MIN = 5
BARS_PER_DAY = 78                      # 09:30 to 15:55 New York time
HORIZONS = {10: 2, 15: 3, 30: 6, 60: 12, 120: 24}   # minutes -> bars

# A move smaller than K_NEUTRAL x (typical 5-min move) x sqrt(bars) is NEUTRAL.
K_NEUTRAL = 0.35
VOL_SPAN_BARS = 20 * BARS_PER_DAY      # about 20 sessions of memory for "typical move"

# Evaluation layout, counted in trading sessions.
FINAL_TEST_SESSIONS = 126              # last ~6 months: looked at once, at the end
WF_INITIAL_TRAIN = 378                 # ~18 months before the first walk-forward test
WF_TEST_BLOCK = 63                     # ~3 months per walk-forward test block
VAL_FRACTION = 0.15                    # tail of each training window: early stopping + calibration

CLASSES = ["DOWN", "NEUTRAL", "UP"]    # encoded 0, 1, 2
