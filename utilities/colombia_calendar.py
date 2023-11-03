import pandas as pd
import QuantLib as ql

def calculate_easter(year):

    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1

    return ql.Date(day, month, year)

def adjust_to_next_monday(date):
    # Check if the date is a Monday (1 corresponds to Monday in QuantLib)
    if date.weekday() != 2:
        # Find the number of days needed to reach the next Monday
        days_to_next_monday = (2 - date.weekday()) % 7
        # Adjust the date to the next Monday
        date += ql.Period(days_to_next_monday, ql.Days)
    return date




def calendar_colombia():
    colombiaCD = ql.WeekendsOnly()
    days = [1,1,20,7,8,25]
    months = [1,5,7,8,12,12]
    name = ['Año Nuevo','dia trabajo','d independencia','b boyaca','inmaculada','navidad']
    start_year = 1990
    n_years = 100
    for i in range(n_years+1):
        for x,y in zip(days,months):
            date = ql.Date(x,y,start_year+i)
            colombiaCD.addHoliday(date)
            #print('Fijos')
            #print(date)
    days_epifania=[6,19,29,15,12,1,11]
    months_epifania=[1,3,6,8,10,11,11]
    name_epifania=['epifania','san jose','san pedro','asuncion','dia raza','todos santos','independencia']
    for i in range(n_years+1):
        for x,y in zip(days_epifania,months_epifania):
            date = ql.Date(x,y,start_year+i)
            colombiaCD.addHoliday(adjust_to_next_monday(date))
            #print('Lunes siguiente')
            #print(date)



    # Calcula semana santa para los años 1990 a 2100
    for year in range(start_year, start_year + n_years + 1):
        easter_date = calculate_easter(year)

        # List Easter and related holidays
        holidays_semana_santa = [
            easter_date - 3,
            easter_date - 2,
        ]
        for holiday in holidays_semana_santa:
            colombiaCD.addHoliday(holiday)
            #print('Semana santa')
            #print(holiday)
    # Calcula ascension de jesus, corpus cristi, sagrado corazon de jesus
        holidays_pascua = [
            easter_date+43,
            easter_date+64,
            easter_date+71,
        ]
        for holiday in holidays_pascua:
            colombiaCD.addHoliday(adjust_to_next_monday(holiday))
            #print('Pacua')
            #print(holiday)
    return colombiaCD