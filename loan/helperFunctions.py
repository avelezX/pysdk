import QuantLib as ql
from utilities.date_functions import datetime_to_ql
from pricing.curves.ibr_curve import build_ibr_curve


class QlHelperFunctions:
    def __init__(self):
        pass

    def create_curve(self, db_info: dict, value_date, years=None) -> ql.YieldTermStructure:
        """
        Build IBR discount curve using centralized builder.
        years parameter is ignored — all available tenors are used.
        """
        ql_date = datetime_to_ql(value_date) if not isinstance(value_date, ql.Date) else value_date
        curve, _ = build_ibr_curve(db_info, ql_date)
        return curve
