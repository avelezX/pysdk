import pandas as pd


def all_local_fvars():
    readed_pd = pd.read_csv('financial_variables/fvars.tsv', delimiter='\t+', engine='python')

    readed_pd = readed_pd.reset_index()  # make sure indexes pair with number of rows

    for index, row in readed_pd.iterrows():
        yield (index, row)

def all_local_fvars2():
    readed_pd = pd.read_csv('financial_variables/fvars.tsv', delimiter='\t+', engine='python')

    readed_pd = readed_pd.reset_index()  # make sure indexes pair with number of rows

    for index, row in readed_pd.iterrows():
        yield (index, row)