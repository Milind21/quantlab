import numpy as np
import pandas as pd
from quantlab.regime import regime_series


def test_regime_hysteresis():
    # build SPY that rises (ON), dips slightly (should STAY on due to band), then crashes (OFF)
    up = np.linspace(100, 300, 260)            # > SMA200 -> turns ON
    small_dip = np.linspace(300, 297, 10)      # tiny dip, within 2% band -> stay ON
    crash = np.linspace(297, 180, 40)          # deep -> below (1-band)*SMA200 -> OFF
    close = pd.Series(np.concatenate([up, small_dip, crash]),
                      index=pd.date_range("2019-01-01", periods=310, freq="B"))
    on = regime_series(close, sma_window=200, band=0.02)
    assert on.iloc[:199].sum() == 0            # warm-up: SMA200 NaN -> OFF (defined at idx 199)
    assert on.iloc[259]                         # ON after the long rise
    assert on.iloc[265]                         # STAYS on through the small dip (hysteresis band)
    assert not on.iloc[-1]                       # OFF after the crash
