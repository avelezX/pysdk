

import pandas as pd

def yyyyqq_to_datetime(df : pd.DataFrame):
    """
    Converts YYYYQQ to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string").str.slice(0,4,1) + "-Q" + df['fecha'].astype("string").str.slice(5,6,1), format= 'mixed')
    
    return df

def yyyy_mm_to_datetime(df : pd.DataFrame):
    """
    Converts YYYY-MM to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string")+'-01',format = '%Y-%m-%d')

    return df

def yyyy_slash_mm_to_datetime(df : pd.DataFrame):
    """
    Converts YYYY/MM to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string")+'/01',format = '%Y/%m/%d')

    return df

def yyyymm_to_datetime(df : pd.DataFrame):
    """
    Converts YYYYMM to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string") + '01',format = '%Y%m%d')

    return df

def yyyy_mm_dd_to_datetime(df : pd.DataFrame):
    """
    Converts YYYY-MM-DD to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string"),format = '%Y-%m-%d')

    return df


def yyyy_mm_dd_H_M_S_to_datetime(df : pd.DataFrame):
    """
    Converts YYYY-MM-DD to Datetime
    """
    df['fecha'] = pd.to_datetime(df['fecha'].astype("string"),format = '%Y-%m-%d %H:%M:%S')

    return df

def get_max_by_date(df : pd.DataFrame):
    """
    The GDP file brings some sub groups of supply and demand, this is to get the largest one which is the one that groups all of the others
    """
    #df = df.groupby('fecha').agg(valor=('valor', 'max')).reset_index()
    df = df.groupby('fecha').max('valor').reset_index()

    return df
