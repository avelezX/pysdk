




def nom_to_effective(nominal_rate,compounding_frequency):
    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1