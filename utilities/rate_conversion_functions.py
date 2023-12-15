
import QuantLib as ql
# Tasas de interes en quantlib
# https://rkapl123.github.io/QLAnnotatedSource/d5/d7b/namespace_quant_lib.html#a2779d04b4839fd386b5c85bbb96aaf73




def nom_to_effective(nominal_rate,compounding_frequency):
    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1