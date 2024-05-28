import os
import glob
import pandas as pd

def get_data(abs_folder_path):
    _Time = 400000000
    # initialize a new pandas dataframe to store the results
    results_df = pd.DataFrame(columns=['load', 'ave_nlat', 'Phi', 'L_access'])
    for file_path in sorted(glob.glob(os.path.join(abs_folder_path, '*.csv'))):
        # the file name should be "load_{load}.csv", we will extract the load value from it
        load_value = float(os.path.basename(file_path).split('_')[1][:3])

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

        # append the data to the results_df
        results_df.loc[len(results_df.index)] = [load_value, AVE_LAT, TOT_BW, EP_BW]
    
    return results_df