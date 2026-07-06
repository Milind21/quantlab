from quantlab import portfolio as pf


def test_position_size_risk_then_cap():
    # risk-based: 0.5% of 100k / (100-95)=5 -> 100 shares; cap 5% notional/100 = 50 shares -> cap wins
    sh = pf.position_size(100_000, 100.0, 95.0, risk_per_trade=0.005, position_pct_cap=0.05)
    assert sh == 50
    # wider stop -> risk binds: 0.5%*100k / (100-90)=10 -> 50 risk-shares; cap 50 -> tie -> 50
    sh2 = pf.position_size(100_000, 100.0, 90.0, 0.005, 0.05)
    assert sh2 == 50


def test_position_size_guards():
    assert pf.position_size(100_000, 100.0, 100.0, 0.005, 0.05) == 0   # zero per-share risk
    assert pf.position_size(100_000, 100.0, 120.0, 0.005, 0.05) == 0   # stop above entry


def test_trailing_stop_ratchets():
    s1 = pf.trailing_stop(prev_stop=90.0, highest_close_since_entry=100.0, atr_now=4.0, mult=2.5)
    assert s1 == 90.0                       # 100-10=90, == prev, no change
    s2 = pf.trailing_stop(prev_stop=90.0, highest_close_since_entry=110.0, atr_now=4.0, mult=2.5)
    assert s2 == 100.0                      # ratchets up to 110-10
    s3 = pf.trailing_stop(prev_stop=100.0, highest_close_since_entry=105.0, atr_now=4.0, mult=2.5)
    assert s3 == 100.0                      # never decreases


def test_gap_rule():
    # opens below stop -> fill at OPEN (gapped through), not the stop
    assert pf.stop_fill_price(open_price=85.0, stop_price=90.0, low_price=84.0) == 85.0
    # intrabar low pierces stop -> fill at stop
    assert pf.stop_fill_price(open_price=95.0, stop_price=90.0, low_price=89.0) == 90.0
    # stop not hit -> None
    assert pf.stop_fill_price(open_price=95.0, stop_price=90.0, low_price=91.0) is None


def test_gap_15pct_below_fills_open():
    # the master-plan canary: 15% gap below stop fills at open, never at stop price
    fill = pf.stop_fill_price(open_price=85.0, stop_price=100.0, low_price=84.0)
    assert fill == 85.0


def test_kill_switch():
    assert pf.kill_switch_triggered(equity=79_000, peak_equity=100_000, threshold=0.20) is True
    assert pf.kill_switch_triggered(equity=85_000, peak_equity=100_000, threshold=0.20) is False
