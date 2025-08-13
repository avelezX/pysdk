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
from server.main_server import XerenityError, responseHttpError, responseHttpOk

from server.loan_calculator.loan_calculator import LoanCalculatorServer
from server.ibr_quotes_servefr.ibr_quotes_calculator import IbQuotesServer
from server.uvr_prints_server.uvr_prints_calculator import UVRPrintsServer
from server.all_loans_server.all_loans_server import AllLoanServer


def period_payment(request):
    try:
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
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow_ibr()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def uvr_rates(request):
    """

    Entry point for ibr rates calculation
    :param request:
    :return:
    """
    try:
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow_uvr()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def fwd_rates(request):
    try:
        calc = IbQuotesServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def uvr_prints(request):
    try:
        calc = UVRPrintsServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def cpi_implicit(request):
    try:
        calc = UVRPrintsServer(json.loads(request.body))
        return calc.calculate_cpi_implicit()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)


def all_loans(request):
    calc = AllLoanServer(json.loads(request.body))
    return calc.calculate()
    """
    try:
        calc = AllLoanServer(json.loads(request.body))
        return calc.calculate()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)
    """

def wake_up(request):
    return responseHttpOk(body={"message": "Servidor de creditos activado"})


urlpatterns = [
    path("period_payment", period_payment, name="period_payment"),
    path("cash_flow", cash_flow, name="cash_flow"),
    path("ibr_rates", ibr_rates, name="ibr_rates"),
    path("fwd_rates", fwd_rates, name="fwd_rates"),
    path("uvr_prints", uvr_prints, name="uvr_prints"),
    path("cpi_implicit", cpi_implicit, name="cpi_implicit"),
    path("all_loans", all_loans, name="all_loans"),
    path("uvr_rates", uvr_rates, name="uvr_rates"),
    path("wake_up", wake_up, name="wake_up")
]
