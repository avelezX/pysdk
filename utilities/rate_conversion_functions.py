
import QuantLib as ql
# Tasas de interes en quantlib
# https://rkapl123.github.io/QLAnnotatedSource/d5/d7b/namespace_quant_lib.html#a2779d04b4839fd386b5c85bbb96aaf73

def nom_to_effective(nominal_rate,compounding_frequency):
    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1

class interest_rate_convertor:
    """
    A class for calculating and converting interest rates.

    Attributes:
    - tasa (float): The interest rate.
    - tipo (str): Type of interest rate ('Nominal', 'Efectiva', 'Continua').
    - periodicidad (str): Frequency of compounding ('Anual', 'Semestral', etc.).
    - capitalizacion (str): Capitalization period ('Anual', 'Bimensual', etc.).
    - day_count (QuantLib DayCount Convention): Day count convention for interest calculations.

    Methods:
    - ql_object(): Calculate the QuantLib InterestRate object based on input parameters.
    - ql_equivalent(tipo_salida, periodicidad_salida, capitalizacion_salida): 
      Calculate equivalent interest rate based on specified output parameters.
    - tasa_salida_eq(tipo_salida, periodicidad_salida, capitalizacion_salida): 
      Calculate equivalent interest rate as a numerical value based on output parameters.
    """

    def __init__(self, tasa, tipo, periodicidad, capitalizacion, day_count=ql.Actual360()):
        """
        Initialize the tasa_interes object.

        Parameters:
        - tasa (float): The interest rate.
        - tipo (str): Type of interest rate ('Nominal', 'Efectiva', 'Continua').
        - periodicidad (str): Frequency of compounding ('Anual', 'Semestral', etc.).
        - capitalizacion (str): Capitalization period ('Anual', 'Bimensual', etc.).
        - day_count (QuantLib DayCount Convention, optional): Day count convention for interest calculations.
        """

        self.ql_rates_to_user = {'Nominal': ql.Simple, 'Efectiva': ql.Compounded, 'Continua': ql.Continuous}
        self.ql_period_to_user = {'Anual': ql.Annual, 'Semestral': ql.Semiannual, 'Trimestral': ql.Quarterly,
                                  'Bimensual': ql.Bimonthly, 'Mensual': ql.Monthly}
        self.number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1/4, 'Bimensual': 1/6, 'Mensual': 1/12}
        self.ql_day_count = {'act-360': ql.Actual360(), 'act-365': ql.Actual36525(),
                             'act-act': ql.ActualActual(ql.ActualActual.ISDA), '30-360': ql.Thirty360(ql.Thirty360.BondBasis)}

        self.tasa = tasa
        self.tipo = tipo
        self.periodicidad = periodicidad
        self.capitalizacion = capitalizacion
        self.day_count = day_count

        self.ql_tipo = self.ql_rates_to_user[self.tipo]
        self.ql_periodicidad = self.ql_period_to_user[self.periodicidad]
        self.nu_periodicidad = self.number_to_user[self.periodicidad]

        self.ql_capitalizacion = self.ql_period_to_user[self.capitalizacion]
        self.nu_capitalizacion = self.number_to_user[self.capitalizacion]

    def ql_object(self):
        """
        Calculate the QuantLib InterestRate object based on input parameters.

        Returns:
        - ql.InterestRate: QuantLib InterestRate object.
        """

        rate = 0
        if self.number_to_user[self.capitalizacion] > self.number_to_user[self.periodicidad]:
            self.capitalizacion = self.periodicidad
        if self.tipo == 'Nominal':
            rate = self.tasa * (1 / self.nu_periodicidad)
        if self.tipo == 'Efectiva':
            rate = (1 + self.tasa) ** (1 / self.nu_periodicidad) - 1
        if self.tipo == 'Continua':
            e = 2.7182818284590452353603
            rate = e ** (1 / self.nu_periodicidad)
        return ql.InterestRate(rate, self.day_count, self.ql_tipo, self.ql_capitalizacion)

    def ql_equivalent(self, tipo_salida, periodicidad_salida, capitalizacion_salida):
        """
        Calculate equivalent interest rate based on specified output parameters.

        Parameters:
        - tipo_salida (str): Type of output interest rate ('Nominal', 'Efectiva', 'Continua').
        - periodicidad_salida (str): Output frequency of compounding ('Anual', 'Semestral', etc.).
        - capitalizacion_salida (str): Output capitalization period ('Anual', 'Bimensual', etc.).

        Returns:
        - ql.InterestRate: Equivalent QuantLib InterestRate object.
        """

        ql_tipo_salida = self.ql_rates_to_user[tipo_salida]
        if self.number_to_user[capitalizacion_salida] > self.number_to_user[periodicidad_salida]:
            capitalizacion_salida = periodicidad_salida

        num_capitalizacion_salida = self.number_to_user[capitalizacion_salida]
        num_periodicidad_salida = self.number_to_user[periodicidad_salida]

        ql_capitalizacion_salida = self.ql_period_to_user[capitalizacion_salida]
        ql_periodicidad_salida = self.ql_period_to_user[periodicidad_salida]

        rate = self.ql_object()
        rate = rate.equivalentRate(ql_tipo_salida, ql_periodicidad_salida, num_capitalizacion_salida)

        return rate

    def tasa_salida_eq(self, tipo_salida, periodicidad_salida, capitalizacion_salida):
        """
        Calculate equivalent interest rate as a numerical value based on output parameters.

        Parameters:
        - tipo_salida (str): Type of output interest rate ('Nominal', 'Efectiva', 'Continua').
        - periodicidad_salida (str): Output frequency of compounding ('Anual', 'Semestral', etc.).
        - capitalizacion_salida (str): Output capitalization period ('Anual', 'Bimensual', etc.).

        Returns:
        - float: Equivalent interest rate as a numerical value.
        """

        rate = 0
        ql_rate = self.ql_equivalent(tipo_salida, periodicidad_salida, capitalizacion_salida)
        num_periodicidad_salida = self.number_to_user[periodicidad_salida]
        if tipo_salida == 'Nominal':
            rate = ql_rate.rate() * (num_periodicidad_salida)
        if tipo_salida == 'Efectiva':
            rate = (1 + ql_rate.rate()) ** (num_periodicidad_salida) - 1
        if tipo_salida == 'Continua':
            e = 2.7182818284590452353603
            rate = e ** (num_periodicidad_salida)
        return rate
