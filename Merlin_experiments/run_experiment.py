import argparse
import numpy as np
import io
from contextlib import redirect_stdout
import re
import csv
from paths import SST_MERLIN_TEMP_PATH, REPO_ROOT
from sst_ultility.ultility import run_sst
from topoResearch.pickle_data import pickle_paths
from topoResearch.pickle_data_nexullance import pickle_nexullance_paths

def run_experiment(config_dict, nexullance_method=None, path_dict="ASP"):
    # Pickle paths
    if path_dict == "ASP":
        pickle_paths(config_dict['topo_name'], (config_dict['V'], config_dict['D']))
    else:
        pickle_nexullance_paths(config_dict['topo_name'], (config_dict['V'], config_dict['D']),
                                config_dict['UNIFIED_ROUTER_LINK_BW'], config_dict['UNIFIED_ROUTER_LINK_BW'],
                                config_dict['traffic_pattern'], nexullance_method)

    # Run SST and capture output
    output = io.StringIO()
    with redirect_stdout(output):
        run_sst(config_dict, "merlin_auto_config.py", SST_MERLIN_TEMP_PATH)
    captured_output = output.getvalue()

    # Parse latency data
    latency_data = {}
    pattern = re.compile(r'^\s*(\d+\.\d+)\s+([\d\.]+)\s+([a-z]+)')
    for line in captured_output.splitlines():
        match = pattern.match(line)
        if match:
            offered_load = float(match.group(1))
            latency_value = float(match.group(2))
            unit = match.group(3)
            if unit == "us":
                latency_value *= 1000
            latency_data[offered_load] = latency_value

    # Generate CSV file name
    csv_filename = REPO_ROOT.as_posix() + "Merlin_experiments/data"
    for key, val in config_dict.items():
        if key not in ['LOAD', 'UNIFIED_ROUTER_LINK_BW']:
            csv_filename += str(val) + "_"
    csv_filename += ".csv"

    # Write to CSV
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Offered Load", "Average Latency (ns)"])
        for load, latency in latency_data.items():
            writer.writerow([load, latency])

    print(f"Data has been written to {csv_filename}")

def main():
    parser = argparse.ArgumentParser(description="Run ASP or Nexullance SST load sweep")
    parser.add_argument("--path_dict", choices=["ASP", "nexullance"], required=True)
    parser.add_argument("--traffic_patterns", nargs="+", default=["uniform", "shift_1", "shift_half"])
    parser.add_argument("--routing_algos", nargs="+", default=["nonadaptive", "ugal_precise", "ugal_threshold"])
    parser.add_argument("--nexullance_methods", nargs="+", default=["IT", "MP_APST_4"])
    parser.add_argument("--V", type=int, default=32, help="Number of routers per row")
    parser.add_argument("--D", type=int, default=6, help="Number of rows")
    parser.add_argument("--topo_name", type=str, default="Slimfly", help="Topology name")

    args = parser.parse_args()

    for traffic in args.traffic_patterns:
        if args.path_dict == "ASP":
            for routing in args.routing_algos:
                config_dict = {
                    'LOAD': list(np.arange(0.05, 1.01, 0.05)),
                    'UNIFIED_ROUTER_LINK_BW': 16,
                    'V': args.V,
                    'D': args.D,
                    'topo_name': args.topo_name,
                    'paths': "ASP",
                    'routing_algo': routing,
                    'traffic_pattern': traffic
                }
                run_experiment(config_dict, path_dict="ASP")
        else:
            for method in args.nexullance_methods:
                config_dict = {
                    'LOAD': list(np.arange(0.05, 1.01, 0.05)),
                    'UNIFIED_ROUTER_LINK_BW': 16,
                    'V': args.V,
                    'D': args.D,
                    'topo_name': args.topo_name,
                    'paths': f"Nexullance_{method}_{traffic}",
                    'routing_algo': "nonadaptive_weighted",
                    'traffic_pattern': traffic
                }
                run_experiment(config_dict, nexullance_method=method, path_dict="nexullance")

if __name__ == "__main__":
    main()
