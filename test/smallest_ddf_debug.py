import sst
from sst.merlin.base import *
from sst.merlin.endpoint import *
from sst.merlin.interface import *
from sst.merlin.topology import *
from sst.merlin.targetgen import *
import os
graph_data_path = os.environ.get('PICKLED_DATA')

LOAD=1.0
topology='ddf'
RT_algo='unipath'# the way that the routing table is calculated
V=6
D=2

if __name__ == "__main__":


    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = 2
    topo.algorithm = ["ugal"]
    # topo.algorithm = ["nonadaptive"]
    # topo.algorithm = ["minimal","minimal"]
    # import graph edgelist and path dict
    topo.graph_num_vertices=V
    topo.graph_degree=D
    topo.topo_name=f"({V}, {D})_{topology}"
    topo.edgelist_file=graph_data_path+f"/from_graph_edgelists/{topo.topo_name}_edgelist.pickle"
    topo.pathdict_file=graph_data_path+f"/from_graph_pathdicts/{RT_algo}_{topo.topo_name}_paths.pickle"
    topo.csv_files_path=graph_data_path+f"/from_graph_pass_down/{topo.topo_name}_{RT_algo}"

    # Set up the routers
    router = hr_router()
    router.link_bw = "32GB/s"
    router.flit_size = "32B"
    router.xbar_bw = "64GB/s" #TODO: how much is this equivalent to the router speed-up in booksim?
    router.input_latency = "0ns"
    router.output_latency = "0ns"
    router.input_buf_size = "2kB" #=64flits/vc*32B/flit
    router.output_buf_size = "2kB"  
    router.num_vns = 1
    router.xbar_arb = "merlin.xbar_arb_rr"

    topo.router = router
    topo.link_latency = "1ns"
    topo.host_link_latency = "1ns"
    
    ### set up the endpoint
    networkif = LinkControl()
    networkif.link_bw = "32GB/s"
    networkif.input_buf_size = "2kB" 
    networkif.output_buf_size = "2kB" 

    # networkif2 = LinkControl()
    # networkif2.link_bw = "4GB/s"
    # networkif2.input_buf_size = "1kB"
    # networkif2.output_buf_size = "1kB"

    # Set up VN remapping
    networkif.vn_remap = [0]
    # networkif2.vn_remap = [1]
    

    targetgen=ShiftTarget()
    targetgen.shift=6
    ep = OfferedLoadJob(0,topo.getNumNodes())
    ep.network_interface = networkif
    ep.pattern=targetgen
    ep.offered_load = LOAD
    ep.link_bw = "32GB/s"
    ep.message_size = "160B"
    ep.collect_time = "60us"
    ep.warmup_time = "60us"
    ep.drain_time = "0us" 
    # ep.pattern = "uniform"

    # #orignal setup for eps:
    # ep = TestJob(0,topo.getNumNodes() // 2)
    # ep.network_interface = networkif
    # #ep.num_messages = 10
    # #ep.message_size = "8B"
    # #ep.send_untimed_bcast = False
        
    # ep2 = TestJob(1,topo.getNumNodes() // 2)
    # ep2.network_interface = networkif2
    # #ep.num_messages = 10
    # #ep.message_size = "8B"
    # #ep.send_untimed_bcast = False
        
    system = System()
    system.setTopology(topo)
    system.allocateNodes(ep,"linear")
    # system.allocateNodes(ep2,"linear")

    system.build()
    

    sst.setStatisticLoadLevel(10)

    sst.setStatisticOutput("sst.statOutputCSV");
    sst.setStatisticOutputOptions({
        "filepath" : f"{topo.topo_name}_load_{LOAD}.csv",
        "separator" : ", "
    })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"30000ns"})