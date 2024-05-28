import os
import glob
import pandas as pd
# TODO: get the traffic matrix from the csv files

def get_data(file_path):
    _Time = 400000000

    # read the csv file and store the data in a pandas dataframe
    df = pd.read_csv(file_path)

    filtered_df = df[(df[' StatisticName'] == ' network_latency') & (df[' SimTime']==_Time)]
    filtered_df = filtered_df.drop_duplicates(keep = 'first', subset=['ComponentName'])
    AVE_LAT = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()

    filtered_df = df[(df['ComponentName'].str.contains('offered') ) & (df[' StatisticName'] == ' send_bit_count') & (df[' SimTime']==_Time)]
    filtered_df = filtered_df.drop_duplicates(keep = 'first', subset=['ComponentName'])
    TOT_bit = filtered_df[' Sum.u64'].sum()
    TOT_BW = TOT_bit/8/(_Time/1000)

    EP_BW = TOT_BW/filtered_df[' Sum.u64'].size/1 # divided by the number of endpoints, and access link capcity 1GBps
