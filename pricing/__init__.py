"""
Pricing module for QuantLib-based derivative pricing.

Usage:
    from pricing import CurveManager, NdfPricer, XccySwapPricer, TesBondPricer, IbrSwapPricer
    from pricing.data.market_data import MarketDataLoader

    # 1. Load market data
    loader = MarketDataLoader()

    # 2. Build curves
    cm = CurveManager()
    cm.build_ibr_curve(loader.fetch_ibr_quotes())
    cm.build_sofr_curve(loader.fetch_sofr_curve())
    cm.set_fx_spot(loader.fetch_usdcop_spot())

    # 3. Create pricers (share same CurveManager)
    ndf = NdfPricer(cm)
    xccy = XccySwapPricer(cm)
    tes = TesBondPricer(cm)
    ibr = IbrSwapPricer(cm)

    # 4. Price instruments
    ndf_result = ndf.price(notional_usd=1_000_000, strike=4200, maturity_date=..., direction='buy')

    # 5. Modify a curve node (instruments auto-reprice via RelinkableHandle)
    cm.set_ibr_node('ibr_5y', 9.75)
"""
from pricing.curves.curve_manager import CurveManager
from pricing.instruments.ndf import NdfPricer
from pricing.instruments.xccy_swap import XccySwapPricer
from pricing.instruments.tes_bond import TesBondPricer
from pricing.instruments.ibr_swap import IbrSwapPricer
from pricing.portfolio import PortfolioEngine
