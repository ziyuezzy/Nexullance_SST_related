config_dict = {'LOAD': [0.05, 0.1, 0.15000000000000002, 0.2, 0.25, 0.3, 0.35000000000000003, 0.4, 0.45, 0.5, 0.55, 0.6000000000000001, 0.6500000000000001, 0.7000000000000001, 0.7500000000000001, 0.8, 0.8500000000000001, 0.9000000000000001, 0.9500000000000001, 1.0], 'UNIFIED_ROUTER_LINK_BW': 16, 'V': 32, 'D': 6, 'topo_name': 'Slimfly', 'paths': 'Nexullance_MP_APST_4_shift_half', 'routing_algo': 'nonadaptive_weighted', 'traffic_pattern': 'shift_half'}
import os
import sys

graph_data_path=os.environ['PICKLED_DATA']

# Copyright 2009-2024 NTESS. Under the terms
# of Contract DE-NA0003525 with NTESS, the U.S.
# Government retains certain rights in this software.
#
# Copyright (c) 2009-2024, NTESS
# All rights reserved.
#
# This file is part of the SST software package. For license
# information, see the LICENSE file in the top level directory of the
# distribution.

if __name__ == "__main__":
    import sst
    from sst.merlin.base import *
    from sst.merlin.endpoint import *
    from sst.merlin.interface import *
    from sst.merlin.topology import *
    from sst.merlin.targetgen import *

    LOAD=config_dict['LOAD']
    UNIFIED_ROUTER_LINK_BW=config_dict['UNIFIED_ROUTER_LINK_BW']
    V=config_dict['V']
    D=config_dict['D']
    EPR=(D+1)//2
    topo_name=config_dict['topo_name']
    Paths=config_dict['paths']
    routing_algo=config_dict['routing_algo']

    topo_full_name=f"({V},{D}){topo_name}topo"

    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = EPR
    topo.algorithm = [routing_algo, routing_algo]
    # import graph edgelist and path dict
    topo.graph_num_vertices=V
    topo.graph_degree=D
    topo.topo_name=topo_full_name
    topo.edgelist_file=graph_data_path+f"/from_graph_edgelists/{topo_full_name}_edgelist.pickle"
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{Paths}_{topo_full_name}_paths.pickle"

    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{Paths}_{topo_full_name}"
    
    # Set up the routers
    router = hr_router()
    router.link_bw = f"{UNIFIED_ROUTER_LINK_BW}Gb/s"
    router.flit_size = "32B"
    router.xbar_bw = f"{UNIFIED_ROUTER_LINK_BW*2}Gb/s" # 2x crossbar speedup
    router.input_latency = "20ns"
    router.output_latency = "20ns"
    router.input_buf_size = "32kB"
    router.output_buf_size = "32kB"   
    router.num_vns = 2
    router.xbar_arb = "merlin.xbar_arb_rr"

    topo.router = router
    topo.link_latency = "20ns"
    topo.host_link_latency = "10ns"
    
    ### set up the endpoint
    networkif = LinkControl()
    networkif.link_bw = f"{UNIFIED_ROUTER_LINK_BW}Gb/s"
    networkif.input_buf_size = "32kB" 
    networkif.output_buf_size = "32kB" 

    # Set up VN remapping
    networkif.vn_remap = [0]
    
    targetgen = 0
    traffic_pattern = config_dict['traffic_pattern']
    if traffic_pattern == 'uniform':
        targetgen=UniformTarget()
    elif traffic_pattern.startswith("shift_"):
        shift_bits = traffic_pattern[6:]
        if shift_bits == "half":
            shift_bits = (V*EPR)//2
        else:
            try:
                shift_bits = int(shift_bits)
            except ValueError:
                print(f"Error: traffic pattern: ", traffic_pattern)
                sys.exit(1)
        targetgen=ShiftTarget()
        targetgen.shift=shift_bits
    else:
        print(f"Error: invalid traffic pattern: {traffic_pattern}")
        sys.exit(1)

    ep = OfferedLoadJob(0,topo.getNumNodes())
    ep.network_interface = networkif
    ep.pattern=targetgen
    ep.offered_load = LOAD
    ep.link_bw = f"{UNIFIED_ROUTER_LINK_BW}Gb/s"
    ep.message_size = "32B"
    ep.collect_time = "200us"
    ep.warmup_time = "200us"
    ep.drain_time = "1000us" 

    system = System()
    system.setTopology(topo)
    system.allocateNodes(ep,"linear")

    system.build()

    # sst.setStatisticLoadLevel(10)
    # sst.setStatisticOutput("sst.statOutputCSV");
    # sst.setStatisticOutputOptions({
    #     "filepath" : f"load_{LOAD}.csv",
    #     "separator" : ", "
    # })
    # # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})
    # sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"0us"})

    # delete python objects:
    del topo
    del router
    del networkif
    del targetgen
    del ep
    del system