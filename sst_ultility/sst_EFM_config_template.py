# Note: imports are added by ultility.py when generating config

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
    
    try:
        import networkx as nx
    except ImportError:
        print("NetworkX is required. Please install NetworkX and try again.")
        sys.exit(1)

    UNIFIED_ROUTER_LINK_BW=config_dict['UNIFIED_ROUTER_LINK_BW']
    V=config_dict['V']
    D=config_dict['D']
    EPR=(D+1)//2
    topo_name=config_dict['topo_name']
    
    BENCH=config_dict['benchmark']
    BENCH_PARAMS=config_dict['benchargs']
    CPE=config_dict['Cores_per_EP']

    # Determine routing method
    # Priority: if nexullance_demand_matrix_file is present, use nexullance routing
    # Otherwise, use the specified routing_method (default: shortest_path)
    if 'nexullance_demand_matrix_file' in config_dict:
        routing_method = 'nexullance'
        nexullance_demand_file = config_dict['nexullance_demand_matrix_file']
        Cap_core = config_dict.get('Cap_core', UNIFIED_ROUTER_LINK_BW)
        Cap_access = config_dict.get('Cap_access', UNIFIED_ROUTER_LINK_BW)
        demand_scaling_factor = config_dict.get('demand_scaling_factor', 10.0)
        # Determine if using SD (single-demand) or MD (multi-demand) optimization
        nexullance_method = config_dict.get('nexullance_method', 'SD')  # 'SD' or 'MD'
        num_demand_samples = config_dict.get('num_demand_samples', 1)  # For MD method
    else:
        routing_method = config_dict.get('routing_method', 'shortest_path')

    # Traffic demand collection configuration
    gen_traffic_demand = 'traffic_demand_file' in config_dict
    traffic_demand_file = config_dict['traffic_demand_file'] if gen_traffic_demand else ""
    traffic_collection_rate = config_dict.get('traffic_collection_rate', '100us')
    # throughput_file = config_dict.get('throughput_file', f"efm_{BENCH}.csv")

    topo_full_name=f"({V},{D}){topo_name}"

    ### Setup the topology using new anytopo system
    # Create the HPC topology instance and get NetworkX graph
    hpc_topo = HPC_topo.initialize_child_instance(topo_name + "topo", V, D)
    hpc_topo.set_endpoints_per_router(EPR)
    G = hpc_topo.get_nx_graph()
    
    # Setup anytopo
    topo = topoAny()
    topo.topo_name = topo_full_name
    topo.import_graph(G)
    
    # All three routing methods use source routing mode
    topo.routing_mode = "source_routing"
    
    # Calculate routing table and configure routing algorithm based on routing_method
    if routing_method == 'ugal':
        # UGAL adaptive routing with source routing table
        routing_table = topo.calculate_routing_table()
        topo.source_routing_algo = "UGAL"
        topo.vn_ugal_num_valiant = config_dict.get('vn_ugal_num_valiant', '1')
        print(f"Using UGAL adaptive routing with source routing table")
        
    elif routing_method == 'nexullance':
        # Nexullance optimized routing with weighted paths
        print(f"Running Nexullance {nexullance_method} optimization with demand matrix from: {nexullance_demand_file}")
        
        # Load and analyze traffic demand
        analyzer = demand_matrix_analyser(
            input_csv_path=nexullance_demand_file,
            V=V, D=D, topo_name=topo_name, EPR=EPR,
            Cap_core=Cap_core, Cap_access=Cap_access,
            suffix="nexullance_opt",
            use_per_interval=True
        )
        
        # Create Nexullance container using configured module
        # Import the nexullance module dynamically based on configuration
        nexullance_module = __import__(NEXULLANCE_MODULE_PATH, fromlist=[NEXULLANCE_CONTAINER_CLASS])
        nexullance_container_class = getattr(nexullance_module, NEXULLANCE_CONTAINER_CLASS)
        nexu_container = nexullance_container_class(
            topo_name=topo_name, V=V, D=D, EPR=EPR,
            Cap_core=Cap_core, Cap_access=Cap_access,
            Demand_scaling_factor=demand_scaling_factor
        )
        
        if nexullance_method == 'MD':
            # Multi-demand Nexullance MD optimization
            print(f"Using Multi-Demand Nexullance MD with {num_demand_samples} samples")
            
            # Get sampled demand matrices using sample_traffic API
            M_EPs_samples, weights, sampling_interval_us = analyzer.sample_traffic(
                num_samples=num_demand_samples,
                filtering_threshold=0.0,
                auto_scale=False
            )
            print(f"Loaded {len(M_EPs_samples)} demand matrix samples (sampling interval: {sampling_interval_us:.2f} us)")
            for i, M_EPs in enumerate(M_EPs_samples):
                print(f"  Sample {i+1} shape: {M_EPs.shape}, sum: {np.sum(M_EPs):.2e}, weight: {weights[i]:.4f}")
            
            # Run Nexullance MD optimization with multiple demand matrices
            obj_value, nexullance_RT = nexu_container.run_MD_nexullance_IT_return_RT(
                M_EPs_s=M_EPs_samples,
                M_EPs_weights=weights,
                _debug=False
            )
            print(f"Nexullance MD optimization complete. Objective: {obj_value:.4f}, Routing table size: {len(nexullance_RT)}")
            
        else:
            # Single-demand Nexullance SD optimization (default)
            print(f"Using Single-Demand Nexullance SD")
            
            # Get accumulated demand matrix
            M_EPs = analyzer.get_accumulated_demand_matrix(plot=False)
            print(f"Loaded demand matrix shape: {M_EPs.shape}")
            print(f"Demand matrix sum: {np.sum(M_EPs):.2e}")
            
            # Run Nexullance SD optimization
            nexullance_RT = nexu_container.run_nexullance_IT_return_RT(
                M_EPs=M_EPs,
                traffic_name="optimized",
                _debug=False
            )
            print(f"Nexullance IT optimization complete. Routing table size: {len(nexullance_RT)}")
        
        # Convert nexullance routing table to SST format
        routing_table, max_path_length = convert_nexullance_RT_to_SST_format(nexullance_RT)
        topo.source_routing_algo = "weighted"
        topo.vcs_per_vn = max_path_length
        print(f"Routing table converted to SST format with {len(routing_table)} source endpoints")
        print(f"Using Nexullance weighted routing ({nexullance_method})")
        
    else:
        # Default: shortest path routing
        routing_table = topo.calculate_routing_table()
        print(f"Using default shortest path routing")

    # Use standard firefly defaults - traffic tracing is now handled by endpointNIC plugins
    PlatformDefinition.setCurrentPlatform("firefly-defaults")  


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
    router.oql_track_port = True

    topo.router = router
    topo.link_latency = "20ns"
    topo.host_link_latency = "10ns"
    
    ### set up the endpoint with endpointNIC and plugins
    endpointNIC = EndpointNIC(use_reorderLinkControl=True, topo=topo)
    
    # Add source routing plugin
    endpointNIC.addPlugin("sourceRoutingPlugin", routing_table=routing_table)
    
    # Add traffic demand collection plugin if enabled
    if gen_traffic_demand:
        endpointNIC.addPlugin("demandMatrixPlugin", metric="bytes")
    
    # Configure network interface parameters
    endpointNIC.link_bw = f"{UNIFIED_ROUTER_LINK_BW}Gb/s"
    endpointNIC.input_buf_size = "32kB"
    endpointNIC.output_buf_size = "32kB"
    endpointNIC.vn_remap = [0]
    
    ep = EmberMPIJob(0,topo.getNumNodes(), numCores = CPE*EPR)
    ep.setEndpointNIC(endpointNIC)
    ep.addMotif("Init")
    ep.addMotif(BENCH+BENCH_PARAMS)
    ep.addMotif("Fini")
    ep.nic.nic2host_lat= "10ns"
        
    system = System()
    system.setTopology(topo)
    system.allocateNodes(ep,"linear")

    system.build()

    # Enable statistics collection
    if gen_traffic_demand:
        # Collect traffic demand matrix
        sst.setStatisticLoadLevel(1)
        sst.setStatisticOutput("sst.statOutputCSV")
        sst.setStatisticOutputOptions({
            "filepath" : traffic_demand_file,
            "separator" : ", "
        })
        sst.enableAllStatisticsForComponentType("merlin.demandMatrixPlugin",
                                            {"type":"sst.AccumulatorStatistic","rate":traffic_collection_rate})
    # else:
    #     # Collect throughput statistics
    #     sst.setStatisticLoadLevel(10)
    #     sst.setStatisticOutput("sst.statOutputCSV");
    #     sst.setStatisticOutputOptions({
    #         "filepath" : throughput_file,
    #         "separator" : ", "
    #     })
    #     sst.enableAllStatisticsForComponentType("merlin.linkcontrol", {"type":"sst.AccumulatorStatistic","rate":"0ns"})

