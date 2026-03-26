"""
URL configuration for xerenity_functions project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import json
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from server.main_server import XerenityError, responseHttpError, responseHttpOk

from server.pricing_api.views import (
    pricing_build, pricing_status, pricing_bump, pricing_reset,
    pricing_ndf, pricing_ndf_implied_curve, pricing_ndf_settlement,
    pricing_ibr_swap, pricing_ibr_par_curve,
    pricing_tes_bond, pricing_xccy_swap,
    pricing_reprice_portfolio,
    pricing_portfolio_reprice,
    pricing_marks_dates,
    pricing_marks,
)


def period_payment(request):
    try:
        from server.loan_calculator.loan_calculator import LoanCalculatorServer
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.period_payment()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def cash_flow(request):
    """

    Entry point for cash flow calculation
    :param request:
    :return:
    """

    try:

        if len(request.body) == 0:
            raise Exception('No se encontraron datos para este credito')

        from server.loan_calculator.loan_calculator import LoanCalculatorServer
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def ibr_rates(request):
    """

    Entry point for ibr rates calculation
    :param request:
    :return:
    """

    try:
        from server.loan_calculator.loan_calculator import LoanCalculatorServer
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow_ibr()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def uvr_rates(request):
    """

    Entry point for uvr rates calculation
    :param request:
    :return:
    """
    try:
        from server.loan_calculator.loan_calculator import LoanCalculatorServer
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow_uvr()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def fwd_rates(request):
    try:
        from server.ibr_quotes_servefr.ibr_quotes_calculator import IbQuotesServer
        calc = IbQuotesServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def uvr_prints(request):
    try:
        from server.uvr_prints_server.uvr_prints_calculator import UVRPrintsServer
        calc = UVRPrintsServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def cpi_implicit(request):
    try:
        from server.uvr_prints_server.uvr_prints_calculator import UVRPrintsServer
        calc = UVRPrintsServer(json.loads(request.body))
        return calc.calculate_cpi_implicit()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def all_loans(request):
    try:
        from server.all_loans_server.all_loans_server import AllLoanServer
        calc = AllLoanServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_management(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_rolling_var(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.rolling_var()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_benchmark_factors(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.benchmark_factors()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_exposure(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.exposure()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_collectors_status(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.collectors_status()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_update_prices(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.update_prices()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio_upsert(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio_upsert()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio_roll(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio_roll()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio_close(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio_close()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio_delete(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio_delete()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def risk_futures_portfolio_edit(request):
    try:
        from server.risk_management_server.risk_management_server import RiskManagementServer
        calc = RiskManagementServer(json.loads(request.body))
        return calc.futures_portfolio_edit()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def wake_up(request):
    return responseHttpOk(body={"message": "Servidor de creditos activado"})


urlpatterns = [
    path("period_payment", csrf_exempt(period_payment), name="period_payment"),
    path("cash_flow", csrf_exempt(cash_flow), name="cash_flow"),
    path("ibr_rates", csrf_exempt(ibr_rates), name="ibr_rates"),
    path("fwd_rates", csrf_exempt(fwd_rates), name="fwd_rates"),
    path("uvr_prints", csrf_exempt(uvr_prints), name="uvr_prints"),
    path("cpi_implicit", csrf_exempt(cpi_implicit), name="cpi_implicit"),
    path("all_loans", csrf_exempt(all_loans), name="all_loans"),
    path("uvr_rates", csrf_exempt(uvr_rates), name="uvr_rates"),
    path("wake_up", csrf_exempt(wake_up), name="wake_up"),
    path("risk_management", csrf_exempt(risk_management), name="risk_management"),
    path("risk_rolling_var", csrf_exempt(risk_rolling_var), name="risk_rolling_var"),
    path("risk_benchmark_factors", csrf_exempt(risk_benchmark_factors), name="risk_benchmark_factors"),
    path("risk_exposure", csrf_exempt(risk_exposure), name="risk_exposure"),
    path("risk_collectors_status", csrf_exempt(risk_collectors_status), name="risk_collectors_status"),
    path("risk_update_prices", csrf_exempt(risk_update_prices), name="risk_update_prices"),
    path("risk_futures_portfolio", csrf_exempt(risk_futures_portfolio), name="risk_futures_portfolio"),
    path("risk_futures_portfolio_upsert", csrf_exempt(risk_futures_portfolio_upsert), name="risk_futures_portfolio_upsert"),
    path("risk_futures_portfolio_roll", csrf_exempt(risk_futures_portfolio_roll), name="risk_futures_portfolio_roll"),
    path("risk_futures_portfolio_close", csrf_exempt(risk_futures_portfolio_close), name="risk_futures_portfolio_close"),
    path("risk_futures_portfolio_delete", csrf_exempt(risk_futures_portfolio_delete), name="risk_futures_portfolio_delete"),
    path("risk_futures_portfolio_edit", csrf_exempt(risk_futures_portfolio_edit), name="risk_futures_portfolio_edit"),
    # Pricing API
    path("pricing/curves/build", pricing_build, name="pricing_build"),
    path("pricing/curves/status", pricing_status, name="pricing_status"),
    path("pricing/curves/bump", pricing_bump, name="pricing_bump"),
    path("pricing/curves/reset", pricing_reset, name="pricing_reset"),
    path("pricing/ndf", pricing_ndf, name="pricing_ndf"),
    path("pricing/ndf/implied-curve", pricing_ndf_implied_curve, name="pricing_ndf_implied_curve"),
    path("pricing/ndf/settlement", pricing_ndf_settlement, name="pricing_ndf_settlement"),
    path("pricing/ibr-swap", pricing_ibr_swap, name="pricing_ibr_swap"),
    path("pricing/ibr/par-curve", pricing_ibr_par_curve, name="pricing_ibr_par_curve"),
    path("pricing/tes-bond", pricing_tes_bond, name="pricing_tes_bond"),
    path("pricing/xccy-swap", pricing_xccy_swap, name="pricing_xccy_swap"),
    path("pricing/reprice-portfolio", pricing_reprice_portfolio, name="pricing_reprice_portfolio"),
    path("pricing/portfolio/reprice", pricing_portfolio_reprice, name="pricing_portfolio_reprice"),
    path("pricing/marks/dates", pricing_marks_dates, name="pricing_marks_dates"),
    path("pricing/marks", pricing_marks, name="pricing_marks"),
]
