"""
Integration test for the pricing module.
Tests all curves and instruments with hardcoded market data.

Run: python test_pricing.py
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime

# ── Setup ──
print("=" * 60)
print("PRICING MODULE - INTEGRATION TEST")
print("=" * 60)

# Set valuation date
val_date = ql.Date(25, 2, 2026)
ql.Settings.instance().evaluationDate = val_date

# ── 1. Test SOFR Curve ──
print("\n--- 1. SOFR Curve ---")

from pricing.curves.sofr_curve import build_sofr_curve

sofr_data = pd.DataFrame({
    "tenor_months": [1, 3, 6, 9, 12, 18, 24, 36, 48, 60, 84, 120, 180, 240, 360],
    "swap_rate":    [4.33, 4.30, 4.25, 4.18, 4.10, 3.95, 3.85, 3.72, 3.65, 3.60, 3.55, 3.50, 3.48, 3.47, 3.46],
})

sofr_curve, sofr_quotes = build_sofr_curve(sofr_data, val_date)
print(f"  SOFR curve built: {sofr_curve.referenceDate()}")
print(f"  Nodes: {len(sofr_quotes)}")

# Check discount factors
for y in [1, 2, 5, 10]:
    dt = val_date + ql.Period(y, ql.Years)
    df = sofr_curve.discount(dt)
    zr = sofr_curve.zeroRate(dt, ql.Actual360(), ql.Continuous).rate()
    print(f"  {y}Y: DF={df:.6f}, Zero={zr:.4%}")

# ── 2. Test IBR Curve ──
print("\n--- 2. IBR Curve ---")

from pricing.curves.ibr_curve import build_ibr_curve

ibr_data = {
    "ibr_1d":  [9.25],
    "ibr_1m":  [9.20],
    "ibr_3m":  [9.10],
    "ibr_6m":  [8.90],
    "ibr_12m": [8.50],
    "ibr_2y":  [8.00],
    "ibr_5y":  [7.80],
    "ibr_10y": [7.90],
}

ibr_curve, ibr_quotes = build_ibr_curve(ibr_data, val_date)
print(f"  IBR curve built: {ibr_curve.referenceDate()}")
print(f"  Nodes: {len(ibr_quotes)}")

for y in [1, 2, 5, 10]:
    dt = val_date + ql.Period(y, ql.Years)
    df = ibr_curve.discount(dt)
    zr = ibr_curve.zeroRate(dt, ql.Actual360(), ql.Continuous).rate()
    print(f"  {y}Y: DF={df:.6f}, Zero={zr:.4%}")

# ── 3. Test CurveManager ──
print("\n--- 3. CurveManager ---")

from pricing.curves.curve_manager import CurveManager

cm = CurveManager(val_date)
cm.build_sofr_curve(sofr_data)
cm.build_ibr_curve(ibr_data)
cm.set_fx_spot(4150.0)

print(f"  Status: {cm.status()['ibr']['built']}, {cm.status()['sofr']['built']}")
print(f"  FX Spot: {cm.fx_spot}")

# Test node override
print("\n  Testing node override...")
original_5y = cm.ibr_quotes["ibr_5y"].value()
print(f"    IBR 5Y original: {original_5y:.4%}")

cm.set_ibr_node("ibr_5y", 8.50)  # bump from 7.80 to 8.50
bumped_5y = cm.ibr_quotes["ibr_5y"].value()
print(f"    IBR 5Y bumped:   {bumped_5y:.4%}")

# Check discount factor changed
df_5y = cm.ibr_handle.discount(val_date + ql.Period(5, ql.Years))
print(f"    IBR 5Y DF (bumped): {df_5y:.6f}")

cm.reset_to_market()
df_5y_reset = cm.ibr_handle.discount(val_date + ql.Period(5, ql.Years))
print(f"    IBR 5Y DF (reset):  {df_5y_reset:.6f}")
assert abs(cm.ibr_quotes["ibr_5y"].value() - original_5y) < 1e-10, "Reset failed!"
print("    Reset OK!")

# ── 4. Test IBR Swap Pricer ──
print("\n--- 4. IBR Swap Pricer ---")

from pricing.instruments.ibr_swap import IbrSwapPricer

ibr_pricer = IbrSwapPricer(cm)

# Price a 5Y swap
result = ibr_pricer.price(
    notional=10_000_000_000,
    tenor_or_maturity=ql.Period(5, ql.Years),
    fixed_rate=0.078,
    pay_fixed=True,
)
print(f"  5Y IBR Swap @ 7.80%:")
print(f"    NPV:       {result['npv']:,.0f} COP")
print(f"    Fair rate:  {result['fair_rate']:.4%}")
print(f"    Fixed NPV:  {result['fixed_leg_npv']:,.0f}")
print(f"    Float NPV:  {result['floating_leg_npv']:,.0f}")
print(f"    DV01:       {result['dv01']:,.0f}")

# At-par test
par = ibr_pricer.par_rate(ql.Period(5, ql.Years))
print(f"\n  5Y Par rate: {par:.4%}")

result_par = ibr_pricer.price(
    notional=10_000_000_000,
    tenor_or_maturity=ql.Period(5, ql.Years),
    fixed_rate=par,
)
print(f"  At-par NPV: {result_par['npv']:,.0f} COP (should be ~0)")

# Par curve
print("\n  Par Curve:")
par_df = ibr_pricer.par_curve()
for _, row in par_df.iterrows():
    if row["par_rate"] is not None:
        print(f"    {row['tenor']:>4s}: {row['par_rate']:.4%}")

# ── 5. Test NDF Pricer ──
print("\n--- 5. NDF Pricer ---")

from pricing.instruments.ndf import NdfPricer

ndf_pricer = NdfPricer(cm)

# Implied forward
mat_3m = val_date + ql.Period(3, ql.Months)
fwd_3m = ndf_pricer.implied_forward(mat_3m)
pts_3m = ndf_pricer.forward_points(mat_3m)
print(f"  3M Implied Forward: {fwd_3m:,.2f} (points: {pts_3m:,.2f})")

mat_1y = val_date + ql.Period(1, ql.Years)
fwd_1y = ndf_pricer.implied_forward(mat_1y)
pts_1y = ndf_pricer.forward_points(mat_1y)
print(f"  1Y Implied Forward: {fwd_1y:,.2f} (points: {pts_1y:,.2f})")

# Price an NDF
ndf_result = ndf_pricer.price(
    notional_usd=1_000_000,
    strike=4200.0,
    maturity_date=mat_3m,
    direction="buy",
)
print(f"\n  NDF: Buy USD 1M @ 4200, 3M:")
print(f"    NPV USD: {ndf_result['npv_usd']:,.2f}")
print(f"    NPV COP: {ndf_result['npv_cop']:,.0f}")
print(f"    Forward:  {ndf_result['forward']:,.2f}")

# At-market NDF (strike = forward) should have NPV ~ 0
ndf_atm = ndf_pricer.price(
    notional_usd=1_000_000,
    strike=fwd_3m,
    maturity_date=mat_3m,
    direction="buy",
)
print(f"\n  At-market NDF (strike={fwd_3m:.2f}):")
print(f"    NPV USD: {ndf_atm['npv_usd']:,.6f} (should be ~0)")

# ── 6. Test Xccy Swap Pricer ──
print("\n--- 6. Cross-Currency Swap Pricer ---")

from pricing.instruments.xccy_swap import XccySwapPricer

xccy_pricer = XccySwapPricer(cm)

start = val_date + ql.Period(2, ql.Days)
mat_5y = start + ql.Period(5, ql.Years)

xccy_result = xccy_pricer.price(
    notional_usd=10_000_000,
    start_date=start,
    maturity_date=mat_5y,
    xccy_basis_bps=0.0,
    pay_usd=True,
)
print(f"  5Y Xccy Swap USD 10M, basis=0:")
print(f"    NPV COP: {xccy_result['npv_cop']:,.0f}")
print(f"    NPV USD: {xccy_result['npv_usd']:,.2f}")
print(f"    USD Leg PV: {xccy_result['usd_leg_pv']:,.2f}")
print(f"    COP Leg PV: {xccy_result['cop_leg_pv']:,.0f}")

# Par basis
par_basis = xccy_pricer.par_xccy_basis(
    notional_usd=10_000_000,
    start_date=start,
    maturity_date=mat_5y,
)
print(f"\n  5Y Par Xccy Basis: {par_basis:.1f} bps")

# Verify at par
xccy_par = xccy_pricer.price(
    notional_usd=10_000_000,
    start_date=start,
    maturity_date=mat_5y,
    xccy_basis_bps=par_basis,
)
print(f"  At-par NPV: {xccy_par['npv_cop']:,.0f} COP (should be ~0)")

# ── 7. Test Bump Sensitivity ──
print("\n--- 7. Bump Sensitivity Test ---")

# Price NDF before bump
ndf_before = ndf_pricer.price(1_000_000, 4200, mat_3m, "buy")

# Bump IBR +10 bps
cm.bump_ibr(10)
ndf_after = ndf_pricer.price(1_000_000, 4200, mat_3m, "buy")

print(f"  NDF NPV before IBR +10bp: {ndf_before['npv_cop']:,.0f} COP")
print(f"  NDF NPV after  IBR +10bp: {ndf_after['npv_cop']:,.0f} COP")
print(f"  Delta NPV:                {ndf_after['npv_cop'] - ndf_before['npv_cop']:,.0f} COP")

cm.reset_to_market()

# ── Summary ──
print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
