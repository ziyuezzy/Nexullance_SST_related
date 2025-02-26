import os, sys
sys.path.append("/users/ziyzhang/EFM_experiments/")
import numpy as np
import pandas as pd
import io
from contextlib import redirect_stdout
import re
import csv

from sst_ultility.ultility import run_sst
from topoResearch.pickle_data_nexullance import pickle_nexullance_paths
# from get_data import get_data_in_dir

merlin_temp = "/users/ziyzhang/EFM_experiments/sst_ultility/sst_merlin_config_template.py"

for traffic in ["uniform", "shift_1", "shift_half"]:
    for Nexullance_method in ["IT", "MP_APST_4"]:

        config_dict = {
            'LOAD':1.0,
            'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
            'V':36,
            'D':5,
            'topo_name':"DDF",
            'paths':f"Nexullance_",
            'routing_algo': "nonadaptive_weighted", # same for two subnets
            'traffic_pattern': traffic
            # 'traffic_pattern': "shift_54"
        }
        config_dict['paths'] = config_dict['paths'] + f"{Nexullance_method}_" + config_dict['traffic_pattern']

        config_dict['LOAD'] = list(np.arange(0.05, 1.01, 0.05))

        pickle_nexullance_paths(config_dict['topo_name'], (config_dict['V'], config_dict['D']),
                                    config_dict['UNIFIED_ROUTER_LINK_BW'], config_dict['UNIFIED_ROUTER_LINK_BW'], 
                                    config_dict['traffic_pattern'], Nexullance_method)


        # # for debugging
        # run_merlin(config_dict)

        # Capture the output
        output = io.StringIO()
        with redirect_stdout(output):
            run_sst(config_dict, "merlin_auto_config.py", merlin_temp) 
        # Get the content of the output as a string
        captured_output = output.getvalue()
        # print("Captured Output:", captured_output)

        # Initialize an empty dictionary to store the data
        latency_data = {}
        # Define regex pattern to capture "Offered Load" and "Average Latency"
        pattern = re.compile(r'^\s*(\d+\.\d+)\s+([\d\.]+)\s+([a-z]+)')
        # Process each line in the captured_output
        for line in captured_output.splitlines():
            match = pattern.match(line)
            if match:
                offered_load = float(match.group(1))
                latency_value = float(match.group(2))
                unit = match.group(3)
                # Convert latency to nanoseconds if necessary
                if unit == "us":
                    latency_value *= 1000  # convert microseconds to nanoseconds
                # Add to dictionary
                latency_data[offered_load] = latency_value

        # Specify the output CSV file name
        csv_filename = ""
        for key, _v in config_dict.items():
            if key not in ['LOAD', 'UNIFIED_ROUTER_LINK_BW']:
                csv_filename = csv_filename + str(_v) +"_"
        csv_filename+=".csv"

        # Write the dictionary to a CSV file
        with open(csv_filename, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            # Write the header
            writer.writerow(["Offered Load", "Average Latency (ns)"])
            
            # Write the data rows
            for offered_load, latency in latency_data.items():
                writer.writerow([offered_load, latency])

        print(f"Data has been written to {csv_filename}")

    # # The following is legacy code for getting data from statistic csv files.
    # # run sst-merlin to generate data points
    # for load in np.arange(0.0, 1.0, 0.1):
    #     if load == 0.0:
    #         load += 0.01
    #     config_dict['LOAD'] = round(load,3)
    #     pickle_gen(config_dict['topo_name'], (config_dict['V'], config_dict['D']))
    #     run_merlin(config_dict) 

    # # manifest data and write into csv
    # result_cols=["network_lat[ns]", "accepted_load", "phi[Gbps]"]

    # result_df = pd.DataFrame({
    #     key: get_data_in_dir(key, os.path.dirname(os.path.abspath(__file__))) for key in result_cols
    # })