#!/usr/bin/env python
#
# Copyright 2009-2023 NTESS. Under the terms
# of Contract DE-NA0003525 with NTESS, the U.S.
# Government retains certain rights in this software.
#
# Copyright (c) 2009-2023, NTESS
# All rights reserved.
#
# This file is part of the SST software package. For license
# information, see the LICENSE file in the top level directory of the
# distribution.

import sst
from sst.merlin.base import *
from sst.merlin.endpoint import *
from sst.merlin.interface import *
from sst.merlin.topology import *
from sst.ember import *
import os

graph_data_path=os.environ['PICKLED_DATA']
BENCH="Alltoall"
BENCH_PARAMS=" bytes=100"
CPE=2

UNIFIED_ROUTER_LINK_BW=16 #GBps

EXP_SUFFIX=""
if UNIFIED_ROUTER_LINK_BW:
    EXP_SUFFIX+=f"ROUTERLINKS{UNIFIED_ROUTER_LINK_BW}GBps"

EPR=2
V=36
D=7
topo_name="RRG"
topo_full_name=f"({V},{D}){topo_name}topo"
PATHS="ASP"
ROUTING = "ECMP"

if __name__ == "__main__":

    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = EPR
    # topo.algorithm = ["ugal_precise", "ugal_precise"]
    # topo.algorithm = ["nonadaptive_weighted", "nonadaptive_weighted"]
    topo.algorithm = ["nonadaptive", "nonadaptive"]
    # topo.algorithm = ["minimal","minimal"]
    # import graph edgelist and path dict
    topo.graph_num_vertices=V
    topo.graph_degree=D
    topo.topo_name=topo_full_name
    topo.edgelist_file=graph_data_path+f"/from_graph_edgelists/{topo_full_name}_edgelist.pickle"
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{PATHS}_{topo_full_name}_paths.pickle"
    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{PATHS}_{topo_full_name}"
    

    defaults_z = PlatformDefinition.compose("firefly-defaults-Z",[("firefly-defaults","ALL")])
    defaults_z.addParamSet("nic",{
        "num_vNics": CPE,
        "gen_InterNIC_traffic_trace":True,
        "interNIC_traffic_tracefile_path":f"traffic_BENCH_{BENCH+BENCH_PARAMS}_CPE_{CPE}_EPR_{EPR}_ROUTING_{PATHS}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv",
        })
    PlatformDefinition.setCurrentPlatform("firefly-defaults-Z")
    # PlatformDefinition.setCurrentPlatform("firefly-defaults")
    

    # Set up the routers
    router = hr_router()
    router.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    router.flit_size = "16B"
    router.xbar_bw = f"{UNIFIED_ROUTER_LINK_BW*2}GB/s"
    router.input_latency = "20ns"
    router.output_latency = "20ns"
    router.input_buf_size = "32kB"
    router.output_buf_size = "32kB"
    router.num_vns = 2
    router.xbar_arb = "merlin.xbar_arb_rr"

    topo.router = router
    topo.link_latency = "20ns"
    topo.host_link_latency = "1ns"
    
    ### set up the endpoint
    networkif = ReorderLinkControl()
    networkif.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    networkif.input_buf_size = "32kB"
    networkif.output_buf_size = "32kB"

    # Set up VN remapping
    #networkif.vn_remap = [0]
    
    ep = EmberMPIJob(0,topo.getNumNodes(), numCores = CPE*EPR)
    ep.network_interface = networkif
    ep.addMotif("Init")
    ep.addMotif(BENCH+BENCH_PARAMS)
    # ep.addMotif("Fini")
    ep.nic.nic2host_lat= "100ns"
        
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
    #     "filepath" : f"statistics_BENCH_{BENCH+BENCH_PARAMS}_CPE_{CPE}_EPR_{EPR}_ROUTING_{ROUTING}_{PATHS}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv"                                                                                                                                                                                                                                                                                                     ,
    #     "separator" : ", "
    # })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    # sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"0ns"})