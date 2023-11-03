
import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv
from bond_functions.bond_structure import tes_bond_structure
from bond_functions.bond_curve_structures import BondCurve
from bond_functions.tes_quant_lib_details import depo_helpers,tes_quantlib_det
from utilities.date_functions import ql_to_datetime
import datetime as dt
import QuantLib as ql
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt


#####################################
#----------Creating graphs----------#
#--------Monthly---------#


# Assuming today is the 19th of October, 2023


# Filter dates
def total_cpi_mom_plot(total_cpi_monthly,today):
    dates_before_today = total_cpi_monthly.index < today
    dates_after_today = total_cpi_monthly.index >= today

    # Create a Plotly figure
    fig = go.Figure()

    # Add traces for dates before today
    fig.add_trace(go.Scatter(x=total_cpi_monthly.index[dates_before_today], 
                            y=total_cpi_monthly['Total'][dates_before_today]*100,
                            mode='lines',
                            name='Inflacion Historica'))

    # Add traces for dates after today
    fig.add_trace(go.Scatter(x=total_cpi_monthly.index[dates_after_today], 
                            y=total_cpi_monthly['Total'][dates_after_today]*100,
                            mode='lines',
                            name='Implicita'))

    # Update layout
    fig.update_layout(
        title='Inflacion historica e implicita- Mensual',
        xaxis=dict(title='Fecha'),
        yaxis=dict(title='Total'),
    )
    # Show the plot
    fig.show()
    fig.write_html('total_cpi_mom_plot.html')


#####################################
#----------Creating graphs----------#
#--------Yearly---------#

# Filter dates
def total_cpi_yoy_plot(total_cpi_yoy,today):
    dates_before_today = total_cpi_yoy.index < today
    dates_after_today = total_cpi_yoy.index >= today

    # Create a Plotly figure
    fig = go.Figure()

    # Add traces for dates before today
    fig.add_trace(go.Scatter(x=total_cpi_yoy.index[dates_before_today], 
                            y=total_cpi_yoy['Total'][dates_before_today]*100,
                            mode='lines',
                            name='Historica'))

    # Add traces for dates after today
    fig.add_trace(go.Scatter(x=total_cpi_yoy.index[dates_after_today], 
                            y=total_cpi_yoy['Total'][dates_after_today]*100,
                            mode='lines+markers',
                            name='Implicita'))

    # Update layout
    fig.update_layout(
        title='Inflacion historica e implicita-Anual',
        xaxis=dict(title='Fecha',tickmode='array', ticks='inside'),
        yaxis=dict(title='Total YoY',tickmode='array', ticks='inside'),
    )


    # Show the plot
    fig.show()
    fig.write_html('total_cpi_yoy_plot.html')




############################
#------YEarly JPG Graph

def total_cpi_yoy_image(total_cpi_yoy,today):
    # Filter dates
    dates_before_today = total_cpi_yoy.index < today
    dates_after_today = total_cpi_yoy.index >= today

    # Set the style for seaborn
    sns.set(style="whitegrid")

    # Create a time series plot using seaborn
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=total_cpi_yoy.index[dates_before_today], 
                y=total_cpi_yoy['Total'][dates_before_today]*100,
                label='Historica')
    sns.lineplot(x=total_cpi_yoy.index[dates_after_today], 
                y=total_cpi_yoy['Total'][dates_after_today]*100,
                markers=True, label='Implicita')

    # Set titles and labels
    plt.title('Inflacion historica e implicita-Anual')
    plt.xlabel('Fecha')
    plt.ylabel('Total YoY (%)')

    # Set y-axis format to display percentages with two decimal places
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}%'))

    # Display the plot
    plt.legend()
    plt.tight_layout()
    plt.xticks(total_cpi_yoy.index[::12], [str(year) for year in total_cpi_yoy.index[::12].year], rotation=45)
    plt.savefig('total_cpi_yoy_image.jpg', format='jpg')
    plt.show()


############################
#------Monthly JPG Graph
def total_cpi_mom_image(total_cpi_monthly,today):
    # Filter dates
    dates_before_today = total_cpi_monthly.index < today
    dates_after_today = total_cpi_monthly.index >= today

    # Set the style for seaborn
    sns.set(style="whitegrid")

    # Create a time series plot using seaborn
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=total_cpi_monthly.index[dates_before_today], 
                y=total_cpi_monthly['Total'][dates_before_today]*100,
                label='Historica')
    sns.lineplot(x=total_cpi_monthly.index[dates_after_today], 
                y=total_cpi_monthly['Total'][dates_after_today]*100,
                markers=True, label='Implicita')

    # Set titles and labels
    plt.title('Inflacion historica e implicita-Mensual')
    plt.xlabel('Fecha')
    plt.ylabel('Total MoM (%)')

    # Set y-axis format to display percentages with two decimal places
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}%'))

    # Display the plot
    plt.legend()
    plt.tight_layout()
    plt.xticks(total_cpi_monthly.index[::12], [str(year) for year in total_cpi_monthly.index[::12].year], rotation=45)
    plt.savefig('total_cpi_mom_image.jpg', format='jpg')
    plt.show()




def uvr_image(uvr,today):
    # Filter dates
    dates_before_today = uvr.index < today
    dates_after_today = uvr.index >= today

    # Set the style for seaborn
    sns.set(style="whitegrid")

    # Create a time series plot using seaborn
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=uvr.index[dates_before_today], 
                y=uvr['valor'][dates_before_today],
                label='Historica')
    
    sns.lineplot(x=uvr.index[dates_after_today], 
                y=uvr['valor'][dates_after_today],
                markers=True, label='Implicita')

    # Set titles and labels
    plt.title('UVR historica e implicita')
    plt.xlabel('Fecha')
    plt.ylabel('valor UVR')

    # Set y-axis format to display percentages with two decimal places
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))

    # Display the plot
    plt.legend()
    plt.tight_layout()
    #plt.xticks(uvr.index[::12], [str(year) for year in uvr.index[::12].year], rotation=45)
    plt.savefig('uvr_image.jpg', format='jpg')
    plt.show()

def uvr_plot(uvr,today):
    dates_before_today = uvr.index < today
    dates_after_today = uvr.index >= today

    # Create a Plotly figure
    fig = go.Figure()
    #print(dates_after_today)
    # Add traces for dates before today
    fig.add_trace(go.Scatter(x=uvr.index[dates_before_today], 
                            y=uvr['valor'][dates_before_today],
                            mode='lines',
                            name='Historica'))

    # Add traces for dates after today
    fig.add_trace(go.Scatter(x=uvr.index[dates_after_today], 
                            y=uvr['valor'][dates_after_today],
                            mode='lines+markers',
                            name='Implicita'))

    # Update layout
    fig.update_layout(
        title='UVR historica e implicita-Anual',
        xaxis=dict(title='Fecha',tickmode='array', ticks='inside'),
        yaxis=dict(title='valor UVR',tickmode='array', ticks='inside'),
    )
    # Show the plot
    fig.show()
    fig.write_html('uvr_plot.html')     
