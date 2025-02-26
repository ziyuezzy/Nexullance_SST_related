config_dict = {'UNIFIED_ROUTER_LINK_BW': 16, 'V': 36, 'D': 5, 'topo_name': 'RRG', 'identifier': 'MD_Nexullance_MP_APST_4_128samples_autoscaled_Alltoall bytes=64', 'routing_algo': 'nonadaptive_weighted', 'benchmark': 'Alltoall', 'benchargs': ' bytes=64', 'Cores_per_EP': 4}
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
    from sst.ember import *

    UNIFIED_ROUTER_LINK_BW=config_dict['UNIFIED_ROUTER_LINK_BW']
    V=config_dict['V']
    D=config_dict['D']
    EPR=(D+1)//2
    topo_name=config_dict['topo_name']
    identifier=config_dict['identifier']
    routing_algo=config_dict['routing_algo']

    # BENCH="FFT3D"
    # BENCH_PARAMS=" nx=100 ny=100 nz=100 npRow=12"
    # CPE=1
    BENCH=config_dict['benchmark']
    BENCH_PARAMS=config_dict['benchargs']
    CPE=config_dict['Cores_per_EP']

    gen_InterNIC_traffic_trace: bool = 'traffic_trace_file' in config_dict.keys()
    Traffic_trace_file=""
    if gen_InterNIC_traffic_trace:
        Traffic_trace_file=config_dict['traffic_trace_file']


    EXP_SUFFIX=""

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
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{identifier}_{topo_full_name}_paths.pickle"
    # topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{Paths}_{topo_full_name}_paths.pickle"
    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{identifier}_{topo_full_name}"

    defaults_z = PlatformDefinition.compose("firefly-defaults-Z",[("firefly-defaults","ALL")])
    defaults_z.addParamSet("nic",{
        "num_vNics": CPE,
        "gen_InterNIC_traffic_trace": gen_InterNIC_traffic_trace,
        "interNIC_traffic_tracefile_path": Traffic_trace_file,
        # "interNIC_traffic_tracefile_path":f"traffic_BENCH_{BENCH+BENCH_PARAMS}_EPR_{EPR}_ROUTING_{Paths}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv",
        })
    PlatformDefinition.setCurrentPlatform("firefly-defaults-Z")
    # PlatformDefinition.setCurrentPlatform("firefly-defaults")  


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
    networkif = ReorderLinkControl()
    networkif.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    networkif.input_buf_size = "32kB"
    networkif.output_buf_size = "32kB"

    # Set up VN remapping
    networkif.vn_remap = [0]
    
    ep = EmberMPIJob(0,topo.getNumNodes(), numCores = CPE*EPR)
    ep.network_interface = networkif
    ep.addMotif("Init")
    ep.addMotif(BENCH+BENCH_PARAMS)
    ep.addMotif("Fini")
    ep.nic.nic2host_lat= "10ns"
        
    system = System()
    system.setTopology(topo)
    system.allocateNodes(ep,"linear")

    system.build()

    # sst.setStatisticLoadLevel(9)

    # sst.setStatisticOutput("sst.statOutputCSV");
    # sst.setStatisticOutputOptions({
    #     "filepath" : "stats.csv",
    #     "separator" : ", "
    # })

    # sst.setStatisticLoadLevel(10)

    # sst.setStatisticOutput("sst.statOutputCSV");
    # sst.setStatisticOutputOptions({
    #     "filepath" : f"statistics_BENCH_{BENCH+BENCH_PARAMS}_EPR_{EPR}_ROUTING_{PATHS}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv"                                                                                                                                                                                                                                                                                                     ,
    #     "separator" : ", "
    # })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    # sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"0ns"})

