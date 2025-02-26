from ultility import run_sst

merlin_temp = "/users/ziyzhang/EFM_experiments/sst_ultility/sst_merlin_config_template.py"

config_dict = {
    'LOAD':1.0,
    'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
    'V':36,
    'D':5,
    'topo_name':"RRG",
    'paths':"ASP",
    'routing_algo': "nonadaptive", # same for two subnets
    'traffic_pattern': "uniform"
}

run_sst(config_dict, "merlin_auto_config.py", merlin_temp) 

config_dict = {
    'LOAD':0.1,
    'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
    'V':36,
    'D':5,
    'topo_name':"RRG",
    'paths':"ASP",
    'routing_algo': "nonadaptive", # same for two subnets
    'traffic_pattern': "uniform"
}

run_sst(config_dict, "merlin_auto_config.py", merlin_temp) 

