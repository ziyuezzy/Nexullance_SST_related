import os
import glob
import pandas as pd

# Set the path to the folder containing the CSV files
folder_path = '.'


# Loop through all the CSV files in the folder
for file_path in sorted(glob.glob(os.path.join(folder_path, 'STATICS_*.csv'))):
    # print('Processing file:', file_path)
    print(file_path)
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    _time=df[" SimTime"].max()/1E3
    # Filter the DataFrame to only include rows where StatisticName is "send_bit_count" and SimTime is 60000000
    filtered_df = df[(df[' StatisticName'] == ' network_latency') ]
    # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
    filtered_df = filtered_df.drop_duplicates(keep = 'first')
    # Calculate the sum of the Count.u64 column in the filtered DataFrame
    AVE_LAT = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()

    # Print the result
    print(f"Average network latency={round(AVE_LAT)} ns")
    print(f"Job finishing time={_time} ns")
    # print('ave lat is:', AVE_LAT)

# print("inject rate")
# # load ratio
# # Loop through all the CSV files in the folder
# for file_path in sorted(glob.glob(os.path.join(folder_path, '*.csv'))):
#     # print('Processing file:', file_path)
    
#     # Read the CSV file into a pandas DataFrame
#     df = pd.read_csv(file_path)

#     # Filter the DataFrame to only include rows where StatisticName is "send_bit_count" and SimTime is 60000000
#     filtered_df = df[(df['ComponentName'].str.contains('offered') ) & (df[' StatisticName'] == ' send_bit_count') & (df[' SimTime']==120000000)]
#     # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
#     filtered_df = filtered_df.drop_duplicates(keep = 'first')
    
#     # Calculate the sum of the Count.u64 column in the filtered DataFrame
#     AVE_bit = filtered_df[' Sum.u64'].sum()/filtered_df[' Sum.u64'].size
#     # AVE_bit = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()
#     AVE_ratio = AVE_bit/8/120000/32

#     # Print the result
#     print(AVE_ratio)
#     # print('ave lat is:', AVE_bit)