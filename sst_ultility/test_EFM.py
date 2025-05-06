from ultility import run_sst
from paths import SST_EFM_TEMP_PATH

EFM_temp = SST_EFM_TEMP_PATH

config_dict = {
    'LOAD':1.0,
    'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
    'V':36,
    'D':5,
    'topo_name':"RRG",
    'paths':"ASP",
    'routing_algo': "nonadaptive", # same for two subnets
    'benchmark': "FFT3D",
    'benchargs': " nx=100 ny=100 nz=100 npRow=12",
    'Cores_per_EP': 1
}

run_sst(config_dict, "EFM_auto_config.py", EFM_temp) 
