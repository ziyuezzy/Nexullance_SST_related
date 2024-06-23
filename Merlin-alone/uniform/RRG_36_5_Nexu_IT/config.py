import sst
from sst.merlin.base import *
from sst.merlin.endpoint import *
from sst.merlin.interface import *
from sst.merlin.topology import *
from sst.merlin.targetgen import *
import os

graph_data_path=os.environ['PICKLED_DATA']

LOAD=1.0
# RT_algo='ASP'# the way that the routing table is calculated

UNIFIED_ROUTER_LINK_BW=10 #GBps
V=36
D=5
EPR=(D+1)//2
topo_name="RRG"
topo_full_name=f"({V},{D}){topo_name}topo"
Routing="NEXU_IT_uniform"

if __name__ == "__main__":

    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = EPR
    topo.algorithm = ["nonadaptive_weighted", "nonadaptive_weighted"]
    # topo.algorithm = ["minimal","minimal"]
    # import graph edgelist and path dict
    topo.graph_num_vertices=V
    topo.graph_degree=D
    topo.topo_name=topo_full_name
    topo.edgelist_file=graph_data_path+f"/from_graph_edgelists/{topo_full_name}_edgelist.pickle"
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{Routing}_{topo_full_name}_paths.pickle"
    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{Routing}_{topo_full_name}"
    
    
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
    networkif = LinkControl()
    networkif.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    networkif.input_buf_size = "32kB" 
    networkif.output_buf_size = "32kB" 


    # Set up VN remapping
    networkif.vn_remap = [0]
    

    targetgen=UniformTarget()
    ep = OfferedLoadJob(0,topo.getNumNodes())
    ep.network_interface = networkif
    ep.pattern=targetgen
    ep.offered_load = LOAD
    ep.link_bw = f"{UNIFIED_ROUTER_LINK_BW}GB/s"
    ep.message_size = "1024B"
    ep.collect_time = "200us"
    ep.warmup_time = "200us"
    ep.drain_time = "0us" 
    # ep.pattern = "uniform"

    system = System()
    system.setTopology(topo)
    system.allocateNodes(ep,"linear")

    system.build()
    

    sst.setStatisticLoadLevel(10)

    sst.setStatisticOutput("sst.statOutputCSV");
    sst.setStatisticOutputOptions({
        "filepath" : f"load_{LOAD}.csv",
        "separator" : ", "
    })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"200us"})