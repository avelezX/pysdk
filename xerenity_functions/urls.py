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

from django.urls import path
from server.loan_calculator.loan_calculator import LoanCalculatorServer
from server.main_server import XerenityError, responseHttpError
import json


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
    """
    try:
        calc = LoanCalculatorServer(json.loads(request.body))
        return calc.cash_flow_ibr()
    except XerenityError as xerror:
        return responseHttpError(message=xerror.message, code=xerror.code)
    except Exception as e:
        return responseHttpError(message=str(e), code=400)
    """
    calc = LoanCalculatorServer(json.loads(request.body))
    return calc.cash_flow_ibr()


urlpatterns = [
    path("period_payment", period_payment, name="period_payment"),
    path("cash_flow", cash_flow, name="cash_flow"),
    path("ibr_rates", ibr_rates, name="ibr_rates"),
]
