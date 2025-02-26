import os
import glob
import pandas as pd

def get_data_in_dir(raw_dir):

    for file_path in sorted(glob.glob(os.path.join(raw_dir, '*.csv'))):
        # print('Processing file:', file_path)
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(file_path)
        # Filter the DataFrame to only include rows where StatisticName is "send_bit_count" and SimTime is 60000000
        filtered_df = df[(df[' StatisticName'] == ' network_latency') & (df[' SimTime']==400000000)]
        # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
        filtered_df = filtered_df.drop_duplicates(keep = 'first')
        # Calculate the sum of the Count.u64 column in the filtered DataFrame
        AVE_LAT = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()

        # Print the result
        print(AVE_LAT)
        # print('ave lat is:', AVE_LAT)
        

# Set the path to the folder containing the CSV files
folder_path = '.'

print("network latency")
# Loop through all the CSV files in the folder
for file_path in sorted(glob.glob(os.path.join(folder_path, '*.csv'))):
    # print('Processing file:', file_path)
    
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Filter the DataFrame to only include rows where StatisticName is "send_bit_count" and SimTime is 60000000
    filtered_df = df[(df[' StatisticName'] == ' network_latency') & (df[' SimTime']==400000000)]
    # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
    filtered_df = filtered_df.drop_duplicates(keep = 'first')
    # Calculate the sum of the Count.u64 column in the filtered DataFrame
    AVE_LAT = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()

    # Print the result
    print(AVE_LAT)
    # print('ave lat is:', AVE_LAT)

print("inject rate")
# load ratio
# Loop through all the CSV files in the folder
for file_path in sorted(glob.glob(os.path.join(folder_path, '*.csv'))):
    # print('Processing file:', file_path)
    
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Filter the DataFrame to only include rows where StatisticName is "send_bit_count" and SimTime is 60000000
    filtered_df = df[(df['ComponentName'].str.contains('offered') ) & (df[' StatisticName'] == ' send_bit_count') & (df[' SimTime']==400000000)]
    # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
    filtered_df = filtered_df.drop_duplicates(keep = 'first')
    
    # Calculate the sum of the Count.u64 column in the filtered DataFrame
    AVE_bit = filtered_df[' Sum.u64'].sum()/filtered_df[' Sum.u64'].size
    # AVE_bit = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()
    AVE_ratio = AVE_bit/8/400000/1

    # Print the result
    print(AVE_ratio)
    # print('ave lat is:', AVE_bit)


print("network throughput")
for file_path in sorted(glob.glob(os.path.join(folder_path, '*.csv'))):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)
    filtered_df = df[(df['ComponentName'].str.contains('offered') ) & (df[' StatisticName'] == ' send_bit_count') & (df[' SimTime']==400000000)]
    # filtered_df = df[(df[' StatisticName'] == ' packet_latency') & (~df[' SimTime'].isin([40000000, 50000000, 60000000]))]
    filtered_df = filtered_df.drop_duplicates(keep = 'first')
    # Calculate the sum of the Count.u64 column in the filtered DataFrame
    TOT_bit = filtered_df[' Sum.u64'].sum()
    # AVE_bit = filtered_df[' Sum.u64'].sum()/filtered_df[' Count.u64'].sum()
    TOT_BW = TOT_bit/8/400000

    # Print the result
    print(TOT_BW)
    # print('ave lat is:', AVE_bit)