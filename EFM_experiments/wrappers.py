import os, sys
import numpy as np
import pandas as pd
import io
from contextlib import redirect_stdout
import re
import csv
from paths import SST_EFM_TEMP_PATH, REPO_ROOT

from sst_ultility.ultility import run_sst

example_config_dict = {
    'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
    'V':36,
    'D':5,
    'topo_name':"RRG",
    # 'paths':"ASP",
    'identifier':"ASP",
    # 'routing_algo': "ugal_precise",
    'routing_algo': "", # same for two subnets
    'benchmark': "",
    'benchargs': "",
    'Cores_per_EP': 1
}

def run_EFM(benchmark:str="FFT3D", benchargs:str=" nx=100 ny=100 nz=100 npRow=12", 
            routing:str = "nonadaptive", traffic_trace_file:str="", default_config_dict:dict = example_config_dict):
    from topoResearch.pickle_data import pickle_paths

    config_dict = default_config_dict.copy()
    config_dict['routing_algo']=routing
    config_dict['benchmark']=benchmark
    config_dict['benchargs']=benchargs
    if traffic_trace_file:
        config_dict["traffic_trace_file"]=traffic_trace_file

    pickle_paths(config_dict['topo_name'], (config_dict['V'], config_dict['D']))

    # Capture the output
    output = io.StringIO()
    with redirect_stdout(output):
        run_sst(config_dict, "EFM_auto_config.py", SST_EFM_TEMP_PATH, 8) 
    # Get the content of the output as a string
    captured_output = output.getvalue()
    # print("Captured Output:", captured_output)
    # Define regex pattern to capture the simulated time at the end
    time_pattern = re.compile(r'Simulation is complete, simulated time:\s+([\d\.]+)\s+([a-z]+)')
    match = time_pattern.search(captured_output)
    if match:
        simulated_time_value = float(match.group(1))
        unit = match.group(2)
        if unit == "us":
            return simulated_time_value
        elif unit == "ms":
            return simulated_time_value*1_000  # Convert milliseconds to microseconds
        else:
            print("unexpected bench time unit: ", unit)
            sys.exit(1)
    else:
        print("failed to grep benchmark time, here is the output:")
        print(captured_output)

def run_EFM_MD_Nexu(benchmark:str="FFT3D", benchargs:str=" nx=100 ny=100 nz=100 npRow=12", num_samples:int = 20, 
                    nexu_method:str="IT", default_config_dict:dict = example_config_dict) -> tuple: 
    # this will automatically also run the default nonadaptive ASP routing, 
    # therefore the returned tuple contains the benchtime of the nonadaptive ASP routing and the MD_Nexullance

    from topoResearch.pickle_data_MD_nexullance import pickle_MD_nexullance_paths
    from traffic_analyser.traffic_analyser import traffic_analyser
    traffic_trace_file=f"{str(REPO_ROOT)}/EFM_experiments/traffic_traces/{benchmark}{benchargs}.csv"

    # first run with ASP to sample traffic demand matrices:
    ECMP_ASP_bench_time = run_EFM(benchmark, benchargs, "nonadaptive", traffic_trace_file)

    config_dict = default_config_dict.copy()
    # config_dict['paths'] = f"MD_Nexullance_{nexu_method}_{config_dict['benchmark']}{config_dict['benchargs']}_{num_samples}EnrouteSamples"
    config_dict['identifier'] = f"MD_Nexullance_{nexu_method}_{config_dict['benchmark']}{config_dict['benchargs']}_{num_samples}Samples"
    config_dict['routing_algo']="nonadaptive_weighted"
    config_dict['benchmark']=benchmark
    config_dict['benchargs']=benchargs
    
    analyser=traffic_analyser(traffic_trace_file, config_dict["V"], 
                          config_dict["D"], config_dict["topo_name"], 
                          (config_dict["D"]+1)//2, "", processing_method=2)
    sampled_demand_matrices, weights, sampling_interval_us = analyser.sample_traffic(num_samples)
    pickle_MD_nexullance_paths(config_dict["topo_name"], (config_dict["V"], config_dict["D"]), 
                            config_dict['UNIFIED_ROUTER_LINK_BW'], config_dict['UNIFIED_ROUTER_LINK_BW'],
                            config_dict['benchmark']+config_dict['benchargs'], sampled_demand_matrices, weights, f"{num_samples}EnrouteSamples",nexu_method)
    
    # Capture the output
    output = io.StringIO()
    with redirect_stdout(output):
        run_sst(config_dict, "EFM_auto_config.py", SST_EFM_TEMP_PATH, 8) 
    # Get the content of the output as a string
    captured_output = output.getvalue()
    # print("Captured Output:", captured_output)
    # Define regex pattern to capture the simulated time at the end
    time_pattern = re.compile(r'Simulation is complete, simulated time:\s+([\d\.]+)\s+([a-z]+)')
    match = time_pattern.search(captured_output)
    if match:
        simulated_time_value = float(match.group(1))
        unit = match.group(2)
        if unit == "us":
            pass
        elif unit == "ms":
            simulated_time_value = simulated_time_value*1_000  # Convert milliseconds to microseconds
        else:
            print("unexpected bench time unit: ", unit)
            sys.exit(1)
        return (ECMP_ASP_bench_time, simulated_time_value)
    else:
        print("failed to grep benchmark time, here is the output:")
        print(captured_output)


class MD_Nexu_sweeper: # for the same traffic trace
    def __init__(self, benchmark:str="FFT3D", benchargs:str=" nx=100 ny=100 nz=100 npRow=12", 
                 sst_template_file:str = SST_EFM_TEMP_PATH, 
                 default_config_dict:dict = example_config_dict) -> None:
        from traffic_analyser.traffic_analyser import traffic_analyser
        
        self.EFM_temp = sst_template_file
        traffic_trace_file=f"{str(REPO_ROOT)}/EFM_experiments/traffic_traces/{benchmark}{benchargs}.csv"
        self.benchmark = benchmark
        self.benchargs = benchargs

        if not os.path.isfile(traffic_trace_file):
            # If traffic trace is missing, first run with ASP to sample traffic demand matrices:
            _ = run_EFM(benchmark, benchargs, "nonadaptive", traffic_trace_file)

        self.config_dict = default_config_dict.copy()
        self.config_dict['routing_algo']="nonadaptive_weighted"
        self.config_dict['benchmark']=benchmark
        self.config_dict['benchargs']=benchargs

        self.analyser=traffic_analyser(traffic_trace_file, self.config_dict["V"], 
                self.config_dict["D"], self.config_dict["topo_name"], (self.config_dict["D"]+1)//2, 
                self.config_dict['UNIFIED_ROUTER_LINK_BW'], self.config_dict['UNIFIED_ROUTER_LINK_BW'], "", processing_method=2)
        
        self.ave_message_lat_us = self.analyser.get_ave_message_lat_us()
    
    def run_single_data_point(self, num_samples:int, nexu_method:str, traffic_filter_threshold:float=0.0, traffic_scaling_factor:float=1.0, auto_scaling:bool = False):

        if auto_scaling:
            assert(traffic_scaling_factor==1)

        from topoResearch.pickle_data_MD_nexullance import pickle_MD_nexullance_paths
        from topoResearch.topologies.HPC_topo import HPC_topo
        import topoResearch.global_helpers as gl

        config_dict = self.config_dict.copy()
        path_dict_file = f"MD_Nexullance_{nexu_method}_{num_samples}samples"
        if traffic_filter_threshold > 0:
            path_dict_file += f"_{traffic_filter_threshold}FilterThreshold"
        if traffic_scaling_factor != 1.0:
            path_dict_file += f"_{traffic_scaling_factor}xScaling"
        if auto_scaling:
            path_dict_file += "_autoscaled"
        path_dict_file+= f"_{self.benchmark}{self.benchargs}"
        config_dict["identifier"] = path_dict_file

        if not auto_scaling:
            sampled_demand_matrices, weights, sampling_interval_us = self.analyser.sample_traffic(num_samples, traffic_filter_threshold, auto_scaling)
        else:
            sampled_demand_matrices, weights, sampling_interval_us, auto_scaling_factor = self.analyser.sample_traffic(num_samples, traffic_filter_threshold, auto_scaling)

        simulated_time_value=0
        MD_obj_func=0
        ECMP_obj_func=0
        if len(sampled_demand_matrices)>0:

            if not auto_scaling:
                sampled_demand_matrices = [traffic_scaling_factor*matrix for matrix in sampled_demand_matrices]

            MD_obj_func = pickle_MD_nexullance_paths(config_dict["topo_name"], (config_dict["V"], config_dict["D"]), 
                                    config_dict['UNIFIED_ROUTER_LINK_BW'], config_dict['UNIFIED_ROUTER_LINK_BW'],
                                    sampled_demand_matrices, weights, nexu_method, path_dict_file)
            
            # Capture the output while running sst
            output = io.StringIO()
            with redirect_stdout(output):
                run_sst(config_dict, "EFM_auto_config.py", self.EFM_temp, 8) 
                
            captured_output = output.getvalue()
            time_pattern = re.compile(r'Simulation is complete, simulated time:\s+([\d\.]+)\s+([a-z]+)')
            match = time_pattern.search(captured_output)
            if match:
                simulated_time_value = float(match.group(1))
                unit = match.group(2)
                if unit == "us":
                    pass
                elif unit == "ms":
                    simulated_time_value = simulated_time_value*1_000  # Convert milliseconds to microseconds
                else:
                    print("unexpected bench time unit: ", unit)
                    sys.exit(1)
            else:
                print("failed to grep benchmark time, here is the output:")
                print(captured_output)
                sys.exit(1)

            V=config_dict["V"]
            D=config_dict["D"]
            EPR=(D+1)//2
            Cap=config_dict["UNIFIED_ROUTER_LINK_BW"]
            _network = HPC_topo.initialize_child_instance(config_dict["topo_name"], V, D)
            _network.pre_calculate_ECMP_ASP()
            ECMP_ASP_phis=[]
            for M_EPs in sampled_demand_matrices:
                # apply this routing table
                core_link_flows, access_link_flows = _network.distribute_M_EPs_on_weighted_paths(_network.ECMP_ASP, EPR, M_EPs)
                # calculate phi
                phi = gl.network_total_throughput(M_EPs, max(core_link_flows)/Cap, max(access_link_flows)/Cap)/(V*EPR)
                ECMP_ASP_phis.append(phi)
            ECMP_obj_func=gl.cal_MD_obj_func(ECMP_ASP_phis, weights)

        return {"benchtime[us]": simulated_time_value, 
                "scaling_factor": auto_scaling_factor if auto_scaling else traffic_scaling_factor,
                "sampling_interval_us": sampling_interval_us, 
                "obj_func_ECMP_ASP": ECMP_obj_func, 
                "obj_func_MD": MD_obj_func}
    

    def sweep_samples(self, num_samples_list:list, nexu_method:str, traffic_filter_threshold:float=0.0, traffic_scaling_factor:float=1.0, auto_scaling:bool = False):
        result = {  "ave_message_lat_us": self.ave_message_lat_us,
                    "scaling_factor": [],
                    "benchtime[us]": [], 
                    "sampling_interval_us": [], 
                    "obj_func_ECMP_ASP": [], 
                    "obj_func_MD": []}
        for num_samples in num_samples_list:
            data_point = self.run_single_data_point(num_samples, nexu_method, traffic_filter_threshold, traffic_scaling_factor, auto_scaling)
            for key, value in data_point.items():
                result[key].append(value)
        return result

if __name__ == "__main__":
    # print(run_EFM())
    # print(run_EFM_MD_Nexu(nexu_method="MP_APST_5"))
    print(sweep_MD_Nexu_samples(num_samples_list=[40]))