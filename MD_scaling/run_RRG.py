import os
import sys
from topoResearch.topologies.HPC_topo import HPC_topo
from topoResearch.nexullance.ultility import nexullance_exp_container
import topoResearch.global_helpers as gl
from traffic_analyser.traffic_analyser import traffic_analyser
from EFM_experiments.wrappers import run_EFM
import csv
from paths import REPO_ROOT

def write_into_csvfile(filename:csv, content_row:list):
    with open(filename, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(content_row)
        csv_file.flush()

problem_size = 256
benchmark = "Allreduce"
benchargs:str=f" iterations=10 count={problem_size}"

topo_name = "RRG"
# for method in ["MP_APST_4"]:
for method in ["IT", "MP_APST_4"]:
    output_csv_file = f"{str(REPO_ROOT)}/MD_scaling/{topo_name}_{method}.csv"
    write_into_csvfile(output_csv_file, ["V", "D", "num_samples", "ave_time[s]", "std_time[s]"])

    for (V, D) in [(36, 5), (49, 6), (64, 7), (81, 8), (100, 9)]:
            EPR = (D+1)//2
            Cap_links = 16

            config_dict = {
                'UNIFIED_ROUTER_LINK_BW':Cap_links,  #Gbps
                'V':V,
                'D':D,
                'topo_name':topo_name,
                'identifier':"ASP",
                'routing_algo': "", # same for two subnets
                'benchmark': "",
                'benchargs': "",
                'Cores_per_EP': 4
            }

            traffic_trace_file=f"./traffic_traces/{benchmark}{benchargs}_({V},{D}){topo_name}_ECMP_ASP.csv"
            if not os.path.isfile(traffic_trace_file):
                # If traffic trace is missing, first run with ASP to sample traffic demand matrices:
                _ = run_EFM(benchmark, benchargs, "nonadaptive", traffic_trace_file, default_config_dict=config_dict)

            analyser=traffic_analyser(traffic_trace_file, V, D, topo_name, EPR, Cap_links, Cap_links, "", processing_method=2)

            nexu_exp = nexullance_exp_container(topo_name, V, D, EPR, Cap_core=Cap_links, Cap_access=Cap_links)
            for num_samples in [1, 2, 4, 16, 32, 64]:  
                sampled_demand_matrices, weights, sampling_interval_us, scaling_factor = analyser.sample_traffic(num_samples, auto_scale=True)

                if method == "IT":
                    result = nexu_exp.run_and_profile_MD_nexullance_IT(sampled_demand_matrices, weights, repetitions=3)
                elif method.startswith("MP_APST_"):
                    max_path_length = int(method[8:])
                    assert(3<=max_path_length<=5)
                    result = nexu_exp.run_and_profile_MD_nexullance_MP(sampled_demand_matrices, weights, 4, repetitions=3)
                else:
                    print(f"Error: invalid method: ", method)
                    sys.exit(1)
                
                write_into_csvfile(output_csv_file, [V, D, num_samples, result["ave_time[s]"], result["std_time[s]"]])