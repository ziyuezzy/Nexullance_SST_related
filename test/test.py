import sst
from sst.merlin.base import *
from sst.merlin.endpoint import *
from sst.merlin.interface import *
from sst.merlin.topology import *
from sst.merlin.targetgen import *

if __name__ == "__main__":


    ### Setup the topology
    topo = topoFromGraph()
    topo.hosts_per_router = 1
    topo.algorithm = ["nonadaptive"]
    # topo.algorithm = ["minimal","minimal"]
    # import graph edgelist and path dict
    topo.graph_num_vertices=4
    topo.graph_degree=2
    topo.topo_name="test_Graph"
    topo.edgelist_file="/users/ziyzhang/SST/experiments/pickled_data/from_graph_edgelists/test_graph.pickle"
    topo.pathdict_file="/users/ziyzhang/SST/experiments/pickled_data/from_graph_pathdicts/test_graph.pickle"
    topo.csv_files_path="/users/ziyzhang/SST/experiments/pickled_data/from_graph_pass_down"
    
    # Set up the routers
    router = hr_router()
    router.link_bw = "32GB/s"
    router.flit_size = "32B"
    router.xbar_bw = "64GB/s"  
    router.input_latency = "0ns"
    router.output_latency = "0ns"
    router.input_buf_size = "16kB" #=512flits/vc*32B/flit
    router.output_buf_size = "16kB"  
    router.num_vns = 1
    router.xbar_arb = "merlin.xbar_arb_rr"

    topo.router = router
    topo.link_latency = "1ns"
    topo.host_link_latency = "1ns"
    
    ### set up the endpoint
    networkif = LinkControl()
    networkif.link_bw = "32GB/s"
    networkif.input_buf_size = "8kB" 
    networkif.output_buf_size = "8kB" 

    # networkif2 = LinkControl()
    # networkif2.link_bw = "4GB/s"
    # networkif2.input_buf_size = "1kB"
    # networkif2.output_buf_size = "1kB"

    # Set up VN remapping
    networkif.vn_remap = [0]
    # networkif2.vn_remap = [1]
    

    targetgen=UniformTarget()
    ep = OfferedLoadJob(0,topo.getNumNodes())
    ep.network_interface = networkif
    ep.pattern=targetgen
    ep.offered_load = 1.0
    ep.link_bw = "32GB/s"
    ep.message_size = "32B"
    ep.collect_time = "60us"
    ep.warmup_time = "60us"
    ep.drain_time = "30us" 
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
        "filepath" : "stat_load_1.0_test_ziyue_vn=1.csv"                                                                                                                                                                                                                                                                                                      ,
        "separator" : ", "
    })
    # sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

    sst.enableAllStatisticsForAllComponents({"type":"sst.AccumulatorStatistic","rate":"10000ns"})