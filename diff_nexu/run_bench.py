from EFM_experiments.wrappers import run_EFM
from traffic_analyser.traffic_analyser import traffic_analyser
from paths import REPO_ROOT
import os
import pickle

traffic_trace_dir = f"{str(REPO_ROOT)}/diff_nexu/traffic_traces/"
data_dir = f"{str(REPO_ROOT)}/diff_nexu/data/"

V=36
D=5
EPR = (D+1)//2
Cap_links = 16  #Gbps
topo_name = "RRG"

default_config_dict = {
    'UNIFIED_ROUTER_LINK_BW':Cap_links,
    'V':V,
    'D':D,
    'topo_name':topo_name,
    # 'paths':"ASP",
    'identifier':"ASP",
    # 'routing_algo': "ugal_precise",
    'routing_algo': "", # same for two subnets
    'benchmark': "",
    'benchargs': "",
    'Cores_per_EP': 4
}

bench = "FFT3D"
problem_size = 256
benchargs:str=f" nx={problem_size} ny={problem_size} nz={problem_size} npRow=12"


# bench = "Alltoall"
# problem_size = 64
# benchargs:str=f" bytes={problem_size}"

# bench = "Allreduce"
# problem_size = 2048
# benchargs:str=f" iterations=10 count={problem_size}"

traffic_trace_file= f"{traffic_trace_dir}/{bench}{benchargs}_({V},{D}){topo_name}_ECMP_ASP.csv"
if not os.path.isfile(traffic_trace_file):
    # If traffic trace is missing, first run with ASP to sample traffic demand matrices:
    _ = run_EFM(bench, benchargs, "nonadaptive", traffic_trace_file, default_config_dict=default_config_dict)

analyser=traffic_analyser(traffic_trace_file, V, D, topo_name, EPR, Cap_links, Cap_links, "", processing_method=2)
result = {
            'topo_name': topo_name,
            'V': V,
            'D': D,
            'EPR': EPR,
            'Cap_links': Cap_links,
            'benchmark': bench,
            'benchargs': benchargs,
            'traffic_trace_file': traffic_trace_file,
            'ave_latency[us]': analyser.get_ave_message_lat_us(),

            'matrices': [],
            'num_samples': [],
            'sample_interval': [],
            }

for num_samples in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:  
    sampled_demand_matrices, num_samples, sample_interval = analyser.sample_ranged_traffic_raw(num_samples=num_samples)
    result['matrices'].append(sampled_demand_matrices)
    result['num_samples'].append(num_samples)
    result['sample_interval'].append(sample_interval)

# dump into pickle file
filename = f"{data_dir}/{bench}{benchargs}_({V},{D}){topo_name}_ECMP_ASP_sent.pickle"
with open(filename, 'wb') as f:
    pickle.dump(result, f)
    f.close()
    print(f"result saved to {filename}")

for num_samples in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:  
    sampled_demand_matrices, num_samples, sample_interval = analyser.sample_ranged_traffic_raw(num_samples=num_samples, method="enroute")
    result['matrices'].append(sampled_demand_matrices)
    result['num_samples'].append(num_samples)
    result['sample_interval'].append(sample_interval)

# dump into pickle file
filename = f"{data_dir}/{bench}{benchargs}_({V},{D}){topo_name}_ECMP_ASP_enroute.pickle"
with open(filename, 'wb') as f:
    pickle.dump(result, f)
    f.close()
    print(f"result saved to {filename}")