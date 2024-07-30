#import sys
#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from datetime import datetime
from utilities.colombia_calendar import calendar_colombia
from utilities.date_functions import datetime_to_ql
from utilities.colombia_calendar import calendar_colombia
from bond_functions.tes_quant_lib_details import tes_quantlib_det
import pandas as pd
import QuantLib as ql
import pandas as pd

class tes_bond_structure:
    """
    A class for creating and managing bond structures using QuantLib.

    Attributes:
        emision (datetime.date): Bond issuance date.
        maturity (datetime.date): Bond maturity date.
        cupon (float): Bond coupon rate.
        name (str): Bond name.
        supabase: Supabase instance.
        calendar: QuantLib calendar for Colombia.

    Methods:
        ql_bond_structure: Create a QuantLib bond structure.
        db_bond_call: Make a database call for financial variables.
        db_bond_call_last_trading_day: Make a database call for the last trading day's historical prices.
    """

    def __init__(self, emision=None, maturity=None, cupon=None, name=None, supabase=None):
        """
        Initialize the tes_bond_structure instance.

        Args:
            emision (datetime.date): Bond issuance date.
            maturity (datetime.date): Bond maturity date.
            cupon (float): Bond coupon rate.
            name (str): Bond name.
            supabase: Supabase instance.
        """
        self.emision = emision
        self.maturity = maturity
        self.cuopon = cupon  # Fix typo in variable name
        self.name = name
        self.supabase = supabase
        self.calendar = tes_quantlib_det['calendar']

    def ql_bond_structure(self):
        """
        Create a QuantLib bond structure.

        Returns:
            QuantLib.Bond: QuantLib bond structure.
        """
        start_date = ql.Date(self.emision.day, self.emision.month, self.emision.year)
        maturity_date = ql.Date(self.maturity.day, self.maturity.month, self.maturity.year)

        schedule = ql.MakeSchedule(start_date, maturity_date, ql.Period('1Y'))

        coupon_rate = self.cuopon  # Fix typo in variable name

        interest = ql.FixedRateLeg(schedule, tes_quantlib_det['day_count'], [100.], [coupon_rate])
        bond = ql.Bond(0, self.calendar, start_date, interest)
        return bond
