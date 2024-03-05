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
BENCH="Alltoallv"
BENCH_PARAMS=""
# BENCH_PARAMS=" nsPerElement=1 npRow=2"
# BENCH="PingPong"
# BENCH_PARAMS=" messageSize=1024 iterations=1"

CoresPerNic=1
UNIFIED_ROUTER_LINK_BW=16#GB/s
EXP_SUFFIX=""
FASTER_ALLTOALL=False
if UNIFIED_ROUTER_LINK_BW:
    # EXP_SUFFIX+=f"ROUTER_LINKS_{UNIFIED_ROUTER_LINK_BW}GBps_{CoresPerNic}cpNic"
    EXP_SUFFIX+=f"ROUTER_LINKS_{UNIFIED_ROUTER_LINK_BW}GBps_{CoresPerNic}cpNic"
if FASTER_ALLTOALL:
    EXP_SUFFIX+="_FasterAlltoall"

EPR=1
V=6
D=2
topo_name="DDF"
topo_full_name=f"({V},{D}){topo_name}topo"
Routing="ASP"

if __name__ == "__main__":

    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = EPR
    topo.algorithm = ["nonadaptive", "nonadaptive"]
    # topo.algorithm = ["nonadaptive", "nonadaptive"]
    # topo.algorithm = ["minimal","minimal"]
    # import graph edgelist and path dict
    topo.graph_num_vertices=V
    topo.graph_degree=D
    topo.topo_name=topo_full_name
    topo.edgelist_file=graph_data_path+f"/from_graph_edgelists/{topo_full_name}_edgelist.pickle"
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{Routing}_{topo_full_name}_paths.pickle"
    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{Routing}_{topo_full_name}"
    
    defaults_z = PlatformDefinition.compose("firefly-defaults-Z",[("firefly-defaults","ALL")])
    defaults_z.addParamSet("nic",{
        "num_vNics": CoresPerNic,
        "gen_InterNIC_traffic_trace":True,
        "interNIC_traffic_tracefile_path":f"traffic_BENCH_{BENCH+BENCH_PARAMS}_EPR_{EPR}_ROUTING_{Routing}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv",
        # "dmaBW_GBs": 100,
        # "alltoall_doesnot_wait": True
        # # TODO: no effect of these two?
        # "numSendMachines": 20,
        # "numRecvNicUnits": 20,        
        # # TODO: test latencies
        # "nic2host_lat": "10ns",
        # "rxMatchDelay_ns": 10,
        # "txDelay_ns": 10,
        # "hostReadDelay_ns": 10,
        })
    defaults_z.addParamSet("firefly.functionsm",{
        'verboseLevel': 10,
        'faster_alltoall': FASTER_ALLTOALL,
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
    router.input_buf_size = "8kB"
    router.output_buf_size = "8kB"
    router.num_vns = 2
    router.xbar_arb = "merlin.xbar_arb_rr"

    topo.router = router
    topo.link_latency = "20ns"
    topo.host_link_latency = "1ns"
    
    ### set up the endpoint
    networkif = ReorderLinkControl()
    networkif.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    networkif.input_buf_size = "4kB"
    networkif.output_buf_size = "4kB"

    # Set up VN remapping
    #networkif.vn_remap = [0]
    
    ep = EmberMPIJob(0,topo.getNumNodes(), numCores = CoresPerNic*EPR)
    # ep = EmberMPIJob(0,topo.getNumNodes(), numCores = CoresPerNic*EPR, nicsPerNode = EPR)
    ep.network_interface = networkif
    ep.addMotif("Init")
    ep.addMotif(BENCH+BENCH_PARAMS)
    ep.addMotif("Fini")
    ep.nic.nic2host_lat= "100ns"
    # ep.nicnumSendMachines: 20
    # ep.nicnumRecvNicUnits: 20

    # # TODO: nic parameters by Z
    # ep.nic.nic2host_lat= "10ns"
    # ep.nic.rxMatchDelay_ns= 10
    # ep.nic.txDelay_ns= 10
    # ep.nic.hostReadDelay_ns= 10
    # ep.nic.verboseLevel= 0
    # ep.nic.verboseMask= 0

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

    sst.setStatisticLoadLevel(10)

    sst.setStatisticOutput("sst.statOutputCSV");
    sst.setStatisticOutputOptions({
        "filepath" : f"statistics_BENCH_{BENCH+BENCH_PARAMS}_EPR_{EPR}_ROUTING_{Routing}_V_{V}_D_{D}_TOPO_{topo_name}_SUFFIX_{EXP_SUFFIX}_.csv"                                                                                                                                                                                                                                                                                                     ,
        "separator" : ", "
    })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"0ns"})