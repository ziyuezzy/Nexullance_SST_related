
#!/usr/bin/env python3
"""
SST Simulation Utilities
Provides functions for Merlin (synthetic traffic) and EFM (Ember+Firefly+Merlin) experiments.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add project root to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from paths import SIMULATION_RESULTS_DIR, TOPOLOGIES_DIR, TRAFFIC_TRACES_DIR, NEXULLANCE_MODULE_PATH, NEXULLANCE_CONTAINER_CLASS

def convert_nexullance_RT_to_SST_format(nexullance_RT):
    """
    Convert Nexullance routing table format to SST simulator format.
    
    Nexullance C++ format: {(src, dst): [(path, weight), ...]}
    where path is a list of vertices including source
    
    SST required format: {src: {dst: [(weight, path), ...]}}
    where path is a list of hops excluding source vertex
    
    Args:
        nexullance_RT: Routing table from Nexullance SD/MD optimizer
            Format: dict with (src, dst) tuple keys mapping to list of (path, weight) tuples
            
    Returns:
        tuple: (routing_table, max_path_length)
            - routing_table: dict in SST format with nested dict structure,
                           swapped tuple order (weight first), and source vertex excluded from paths
            - max_path_length: maximum path length (hop count) in the routing table
              
    Example:
        Input:  {(0, 3): [([0, 1, 3], 0.5), ([0, 2, 3], 0.5)]}
        Output: ({0: {3: [(0.5, [1, 3]), (0.5, [2, 3])]}}, 2)
    """
    sst_routing_table = defaultdict(lambda: defaultdict(list))
    max_path_length = 0
    
    for (src, dst), path_weight_list in nexullance_RT.items():
        for path, weight in path_weight_list:
            # Calculate hop count (path[1:] excludes source)
            hop_count = len(path) - 1
            max_path_length = max(max_path_length, hop_count)
            
            # Convert to SST format: (weight, path_without_source)
            sst_routing_table[src][dst].append((weight, path[1:]))
    
    # Convert defaultdict to regular dict for cleaner serialization
    return {src: dict(dst_dict) for src, dst_dict in sst_routing_table.items()}, max_path_length

def _calculate_throughput_from_linkcontrol(throughput_file: str, sim_time_ns: int = 400000000) -> float:
    """
    Calculate total network throughput from linkcontrol statistics CSV.
    
    Args:
        throughput_file: Path to throughput statistics CSV file
        sim_time_ns: Simulation time in nanoseconds (default: 400000000 = 400ms)
        
    Returns:
        Total throughput in Gbps
    """
    import pandas as pd
    
    df = pd.read_csv(throughput_file)
    filtered_df = df[
        (df['ComponentName'].str.contains('offered')) & 
        (df[' StatisticName'] == ' send_bit_count') & 
        (df[' SimTime'] == sim_time_ns)
    ]
    filtered_df = filtered_df.drop_duplicates(keep='first')
    
    # Calculate total bits sent
    TOT_bit = filtered_df[' Sum.u64'].sum()
    
    # Convert to Gbps: bits / sim_time_us / 1000
    sim_time_us = sim_time_ns / 1000
    TOT_BW = TOT_bit / 8 / sim_time_us
    
    return TOT_BW

def _extract_simulation_time_from_output(output_file: str) -> float:
    """
    Extract simulation completion time from SST output file.
    
    Parses lines like "Simulation is complete, simulated time: 5.08998 ms"
    and returns the time value in milliseconds.
    
    Args:
        output_file: Path to simulation output text file
        
    Returns:
        Simulation time in milliseconds, or None if not found
    """
    import re
    
    with open(output_file, 'r') as f:
        for line in f:
            # Match pattern: "Simulation is complete, simulated time: <number> <unit>"
            match = re.search(r'Simulation is complete, simulated time:\s*([\d.]+)\s*(\w+)', line)
            if match:
                time_value = float(match.group(1))
                time_unit = match.group(2).lower()
                
                # Convert to milliseconds
                if time_unit == 'ms':
                    return time_value
                elif time_unit == 's':
                    return time_value * 1000
                elif time_unit == 'us':
                    return time_value / 1000
                elif time_unit == 'ns':
                    return time_value / 1_000_000
                else:
                    print(f"Warning: Unknown time unit '{time_unit}', returning raw value")
                    return time_value
    
    print(f"Warning: Could not find simulation time in {output_file}")
    return None

def _generate_traffic_demand_trace_filename(config_dict: dict, template_type: str) -> str:
    """
    Generate a unique, descriptive filename for traffic demand/trace based on simulation parameters.
    
    Args:
        config_dict: Configuration dictionary
        template_type: 'merlin' or 'EFM'
        
    Returns:
        Absolute path to traffic file
    """
    V = config_dict['V']
    D = config_dict['D']
    EPR = (D + 1) // 2
    topo_name = config_dict['topo_name']
    bw_cap = config_dict['UNIFIED_ROUTER_LINK_BW']
    
    if template_type == 'merlin':
        load = config_dict['LOAD']
        pattern = config_dict['traffic_pattern']
        # Format load to avoid decimal points in filename
        load_str = f"{load:.2f}".replace('.', 'p')
        filename = f"traffic_merlin_{topo_name}_V{V}_D{D}_EPR{EPR}_linkBW{bw_cap}_load{load_str}_{pattern}.csv"
    else:  # EFM
        benchmark = config_dict['benchmark']
        bench_args = config_dict.get('benchargs', '')
        # Clean bench args for filename (remove spaces, special chars)
        bench_args_clean = bench_args.strip().replace(' ', '_').replace('=', '')
        cores_per_ep = config_dict.get('Cores_per_EP', 1)
        filename = f"traffic_efm_{topo_name}_V{V}_D{D}_EPR{EPR}_linkBW{bw_cap}_CPE{cores_per_ep}_{benchmark}{bench_args_clean}.csv"
    
    return str(TRAFFIC_TRACES_DIR / filename)

def _generate_throughput_filename(config_dict: dict, template_type: str) -> str:
    """
    Generate a unique, descriptive filename for throughput statistics based on simulation parameters.
    
    Args:
        config_dict: Configuration dictionary
        template_type: 'merlin' or 'EFM'
        
    Returns:
        Absolute path to throughput statistics file
    """
    V = config_dict['V']
    D = config_dict['D']
    EPR = (D + 1) // 2
    topo_name = config_dict['topo_name']
    
    if template_type == 'merlin':
        load = config_dict['LOAD']
        pattern = config_dict['traffic_pattern']
        load_str = f"{load:.2f}".replace('.', 'p')
        filename = f"throughput_merlin_{topo_name}_V{V}_D{D}_EPR{EPR}_load{load_str}_{pattern}.csv"
    else:  # EFM
        benchmark = config_dict['benchmark']
        bench_args = config_dict.get('benchargs', '')
        bench_args_clean = bench_args.strip().replace(' ', '_').replace('=', '')
        filename = f"throughput_EFM_{topo_name}_V{V}_D{D}_EPR{EPR}_{benchmark}_{bench_args_clean}.csv"
    
    return str(SIMULATION_RESULTS_DIR / filename)

def run_merlin_experiment_with_nexullance(topo_name: str, V: int, D: int, load: float,
                                          traffic_pattern: str = "uniform", link_bw: int = 16,
                                          num_threads: int = 8, traffic_collection_rate: str = "10us",
                                          Cap_core: float = None, Cap_access: float = None,
                                          demand_scaling_factor: float = 10.0,
                                          nexullance_method: str = "SD",
                                          num_demand_samples: int = 1):
    """
    Run a complete Merlin experiment with Nexullance optimization:
    1. Run shortest-path (baseline) simulation to collect traffic demand and throughput
    2. Use collected demand to optimize routing with Nexullance
    3. Run simulation with Nexullance routing to measure optimized performance
    
    Args:
        topo_name: Topology name (e.g., "RRG", "Slimfly", "DDF")
        V: Number of vertices/routers
        D: Degree of routers
        load: Offered load (0.0 to 1.0)
        traffic_pattern: Traffic pattern ("uniform", "shift_X", etc.)
        link_bw: Link bandwidth in Gbps (default: 16)
        num_threads: SST threads (default: 8)
        traffic_collection_rate: Statistics collection rate (default: "10us")
        Cap_core: Core link capacity for Nexullance (default: None, uses link_bw)
        Cap_access: Access link capacity for Nexullance (default: None, uses link_bw)
        demand_scaling_factor: Demand scaling factor for Nexullance (default: 10.0)
        nexullance_method: Nexullance method to use: "SD" or "MD" (default: "SD")
        num_demand_samples: Number of demand samples for MD method (default: 1)
        
    Returns:
        dict: Dictionary containing paths to demand file and throughput file
    """
    # Set Cap values to link_bw if not provided
    if Cap_core is None:
        Cap_core = link_bw
    if Cap_access is None:
        Cap_access = link_bw
    
    # Base configuration
    config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'LOAD': load,
        'traffic_pattern': traffic_pattern,
        'traffic_collection_rate': traffic_collection_rate,
        'routing_method': 'shortest_path'  # Baseline uses shortest path
    }
    

    demand_config = config.copy()
    demand_config['LOAD'] = load*0.1
    demand_config['UNIFIED_ROUTER_LINK_BW'] = link_bw*10
    demand_file = _generate_traffic_demand_trace_filename(demand_config, 'merlin')
    demand_config['traffic_demand_file'] = demand_file

    baseline_throughput_file = _generate_throughput_filename(config, 'merlin')
    baseline_throughput_file = baseline_throughput_file.replace('.csv', '_shortest_path.csv')
    
    # STEP 1: Run shortest-path baseline to collect demand and throughput
    if not Path(demand_file).exists() or not Path(baseline_throughput_file).exists():
        print("\n" + "=" * 80)
        print("STEP 1: Running SHORTEST-PATH baseline simulation...")
        print("=" * 80)
        print("  - Collecting traffic demand matrix")
        print("  - Measuring baseline throughput")
        
        # First, collect demand matrix if needed
        if not Path(demand_file).exists():
            
            print(f"Demand will be saved to: {demand_file}")
            stdout, stderr, returncode, sim_dir = _run_sst(demand_config, 'merlin', num_threads)
            
            if returncode != 0:
                print(f"Error: Demand collection failed with return code {returncode}")
                return None
        
        # Then, measure baseline throughput if needed
        if not Path(baseline_throughput_file).exists():
            baseline_config = config.copy()
            baseline_config['throughput_file'] = baseline_throughput_file
            
            print(f"Baseline throughput will be saved to: {baseline_throughput_file}")
            stdout, stderr, returncode, sim_dir = _run_sst(baseline_config, 'merlin', num_threads)
            
            if returncode != 0:
                print(f"Error: Baseline throughput measurement failed with return code {returncode}")
                return None
    else:
        print("\n" + "=" * 80)
        print("STEP 1: Baseline data already exists, skipping...")
        print("=" * 80)
        print(f"Using existing demand file: {demand_file}")
        print(f"Using existing baseline throughput: {baseline_throughput_file}")
    
    print("\n" + "=" * 80)
    method_display = "MD_NEXULLANCE" if nexullance_method == "MD" else "NEXULLANCE"
    print(f"STEP 2: Running simulation with {method_display}-optimized routing...")
    print("=" * 80)
    
    # Step 2: Run simulation with nexullance optimization
    throughput_file = _generate_throughput_filename(config, 'merlin')
    suffix = '_md_nexullance.csv' if nexullance_method == 'MD' else '_nexullance.csv'
    throughput_file = throughput_file.replace('.csv', suffix)
    
    optimized_config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'LOAD': load,
        'traffic_pattern': traffic_pattern,
        'throughput_file': throughput_file,
        'nexullance_demand_matrix_file': demand_file,
        'routing_method': 'md_nexullance' if nexullance_method == 'MD' else 'nexullance',
        'Cap_core': Cap_core,
        'Cap_access': Cap_access,
        'demand_scaling_factor': demand_scaling_factor,
        'num_demand_samples': num_demand_samples
    }
    
    print(f"Using demand matrix: {demand_file}")
    print(f"Using {nexullance_method} optimization method")
    if nexullance_method == 'MD':
        print(f"Number of demand samples: {num_demand_samples}")
    print(f"Nexullance throughput will be saved to: {throughput_file}")
    stdout, stderr, returncode, sim_dir = _run_sst(optimized_config, 'merlin', num_threads)
    
    if returncode != 0:
        print(f"Error: Optimized simulation failed with return code {returncode}")
        return None
    
    print("\n" + "=" * 80)
    print("STEP 3: Calculating and comparing network throughput...")
    print("=" * 80)
    
    # Calculate throughput from baseline simulation (shortest path)
    print("Calculating SHORTEST-PATH baseline throughput from linkcontrol statistics...")
    baseline_throughput = _calculate_throughput_from_linkcontrol(baseline_throughput_file)
    print(f"Baseline (shortest-path routing) throughput: {baseline_throughput:.4f} Gbps")
    
    # Calculate throughput from optimized simulation (nexullance)
    print("Calculating NEXULLANCE optimized throughput from linkcontrol statistics...")
    optimized_throughput = _calculate_throughput_from_linkcontrol(throughput_file)
    print(f"Optimized (Nexullance routing) throughput: {optimized_throughput:.4f} Gbps")
    
    # Calculate speedup
    if baseline_throughput > 0:
        speedup = optimized_throughput / baseline_throughput
        improvement = (speedup - 1.0) * 100
        print(f"\n{'='*80}")
        print(f"PERFORMANCE IMPROVEMENT:")
        print(f"  Speedup: {speedup:.4f}x")
        print(f"  Improvement: {improvement:+.2f}%")
        print(f"{'='*80}")
    else:
        print("Warning: Baseline throughput is zero, cannot calculate speedup")
        speedup = None
        improvement = None
    
    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE!")
    print("=" * 80)
    print(f"Output files:")
    print(f"  - Traffic demand matrix:      {demand_file}")
    print(f"  - Baseline throughput stats:  {baseline_throughput_file}")
    print(f"  - Optimized throughput stats: {throughput_file}")
    
    return {
        'demand_file': demand_file,
        'baseline_throughput_file': baseline_throughput_file,
        'throughput_file': throughput_file,
        'baseline_throughput_gbps': baseline_throughput,
        'optimized_throughput_gbps': optimized_throughput,
        'speedup': speedup,
        'improvement_percent': improvement
    }

def run_ember_experiment_with_nexullance(topo_name: str, V: int, D: int, 
                                        benchmark: str, bench_args: str = "",
                                        cores_per_ep: int = 1, link_bw: int = 16,
                                        num_threads: int = 8, traffic_collection_rate: str = "10us",
                                        Cap_core: float = None, Cap_access: float = None,
                                        demand_scaling_factor: float = 10.0,
                                        nexullance_method: str = "SD",
                                        num_demand_samples: int = 1):
    """
    Run a complete EFM (Ember) experiment with Nexullance optimization:
    1. Run shortest-path (baseline) simulation to collect traffic demand and measure time
    2. Run Nexullance-optimized simulation to get improved execution time
    3. Compare simulation times to calculate speedup
    
    Args:
        topo_name: Topology name (e.g., "RRG", "Slimfly", "DDF")
        V: Number of vertices/routers
        D: Degree of routers
        benchmark: Ember benchmark name (e.g., "FFT3D", "Allreduce")
        bench_args: Benchmark arguments (e.g., " nx=100 ny=100 nz=100 npRow=12")
        cores_per_ep: Number of cores per endpoint (default: 1)
        link_bw: Link bandwidth in Gbps (default: 16)
        num_threads: SST threads (default: 8)
        traffic_collection_rate: Statistics collection rate (default: "10us")
        Cap_core: Core link capacity for Nexullance (default: None, uses link_bw)
        Cap_access: Access link capacity for Nexullance (default: None, uses link_bw)
        demand_scaling_factor: Demand scaling factor for Nexullance (default: 10.0)
        nexullance_method: Nexullance optimization method: 'SD' (single-demand) or 'MD' (multi-demand) (default: 'SD')
        num_demand_samples: Number of demand samples for MD method (default: 1)
        
    Returns:
        dict: Dictionary containing simulation times and speedup metrics
    """
    # Set Cap values to link_bw if not provided
    if Cap_core is None:
        Cap_core = link_bw
    if Cap_access is None:
        Cap_access = link_bw
    
    EPR = (D + 1) // 2
    
    # Base configuration
    config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'benchmark': benchmark,
        'benchargs': bench_args,
        'Cores_per_EP': cores_per_ep,
        'routing_method': 'shortest_path'  # Baseline uses shortest path
    }
    
    demand_file = _generate_traffic_demand_trace_filename(config, 'EFM')
    
    # STEP 1: Run shortest-path baseline to collect demand
    if not Path(demand_file).exists():
        print("\n" + "=" * 80)
        print("STEP 1: Running SHORTEST-PATH baseline EFM simulation...")
        print("=" * 80)
        print("  - Collecting traffic demand matrix")
        print("  - Measuring baseline execution time")
        
        demand_config = config.copy()
        demand_config['traffic_demand_file'] = demand_file
        demand_config['traffic_collection_rate'] = traffic_collection_rate
        
        print(f"Demand will be saved to: {demand_file}")
        stdout, stderr, returncode, baseline_sim_dir = _run_sst(demand_config, 'EFM', num_threads)
        
        if returncode != 0:
            print(f"Error: Baseline simulation with demand collection failed with return code {returncode}")
            return None
    else:
        print("\n" + "=" * 80)
        print("STEP 1: Demand matrix already exists...")
        print("=" * 80)
        print(f"Using existing demand file: {demand_file}")
        
        # Run baseline without demand collection to get timing
        print("Running baseline to measure execution time...")
        baseline_config = config.copy()
        stdout, stderr, returncode, baseline_sim_dir = _run_sst(baseline_config, 'EFM', num_threads)
        
        if returncode != 0:
            print(f"Error: Baseline simulation failed with return code {returncode}")
            return None
    
    # STEP 2: Run optimized simulation (Nexullance routing)
    print("\n" + "=" * 80)
    print(f"STEP 2: Running EFM simulation with NEXULLANCE-optimized routing ({nexullance_method})...")
    print("=" * 80)
    
    optimized_config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'benchmark': benchmark,
        'benchargs': bench_args,
        'Cores_per_EP': cores_per_ep,
        'nexullance_demand_matrix_file': demand_file,
        'Cap_core': Cap_core,
        'Cap_access': Cap_access,
        'demand_scaling_factor': demand_scaling_factor,
        'nexullance_method': nexullance_method,
        'num_demand_samples': num_demand_samples
    }
    
    print(f"Using demand matrix: {demand_file}")
    stdout, stderr, returncode, optimized_sim_dir = _run_sst(optimized_config, 'EFM', num_threads)
    
    if returncode != 0:
        print(f"Error: Optimized simulation failed with return code {returncode}")
        return None
    
    # STEP 3: Extract simulation times and calculate speedup
    print("\n" + "=" * 80)
    print("STEP 3: Calculating speedup from simulation times...")
    print("=" * 80)
    
    baseline_output = baseline_sim_dir / f"simulation_output_{baseline_sim_dir.name}.txt"
    optimized_output = optimized_sim_dir / f"simulation_output_{optimized_sim_dir.name}.txt"
    
    print("Extracting simulation times from output files...")
    
    baseline_sim_time = _extract_simulation_time_from_output(str(baseline_output))
    if baseline_sim_time:
        print(f"Baseline (shortest-path routing) simulation time: {baseline_sim_time:.4f} ms")
    else:
        print("Error: Could not extract baseline simulation time")
        return None
    
    optimized_sim_time = _extract_simulation_time_from_output(str(optimized_output))
    if optimized_sim_time:
        print(f"Optimized (Nexullance routing) simulation time: {optimized_sim_time:.4f} ms")
    else:
        print("Error: Could not extract optimized simulation time")
        return None
    
    # Calculate speedup: baseline_time / optimized_time (larger is better)
    if optimized_sim_time > 0:
        speedup = baseline_sim_time / optimized_sim_time
        improvement = (speedup - 1.0) * 100
        time_reduction = baseline_sim_time - optimized_sim_time
        time_reduction_pct = (1 - optimized_sim_time/baseline_sim_time) * 100
        
        print(f"\n{'='*80}")
        print(f"PERFORMANCE IMPROVEMENT:")
        print(f"  Speedup: {speedup:.4f}x")
        print(f"  Improvement: {improvement:+.2f}%")
        print(f"  Time Reduction: {time_reduction:.4f} ms ({time_reduction_pct:.2f}%)")
        print(f"{'='*80}")
    else:
        print("Error: Optimized simulation time is zero")
        return None
    
    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE!")
    print("=" * 80)
    print(f"Output files:")
    print(f"  - Traffic demand matrix:      {demand_file}")
    print(f"  - Baseline simulation output: {baseline_output}")
    print(f"  - Optimized simulation output: {optimized_output}")
    
    return {
        'demand_file': demand_file,
        'baseline_output_file': str(baseline_output),
        'optimized_output_file': str(optimized_output),
        'baseline_sim_time_ms': baseline_sim_time,
        'optimized_sim_time_ms': optimized_sim_time,
        'speedup': speedup,
        'improvement_percent': improvement
    }

def run_merlin_simulation(topo_name: str, V: int, D: int, load: float,
                          traffic_pattern: str = "uniform", link_bw: int = 16,
                          num_threads: int = 8, output_traffic_demand: bool = False,
                          traffic_demand_file: str = "", traffic_collection_rate: str = "10us",
                          routing_method: str = "shortest_path",
                          calculate_throughput: bool = True,
                          **additional_config):
    """
    Run Merlin synthetic traffic simulation with specified routing method.
    
    Supports:
    - shortest_path: Standard shortest path routing
    - ugal: Universal Globally-Adaptive Load-balancing routing
    - Can also collect traffic demand for later Nexullance optimization
    
    Args:
        topo_name: Topology name (e.g., "RRG", "Slimfly", "DDF")
        V: Number of vertices/routers
        D: Degree of routers
        load: Offered load (0.0 to 1.0)
        traffic_pattern: Traffic pattern ("uniform", "shift_X", etc.)
        link_bw: Link bandwidth in Gbps (default: 16)
        num_threads: SST threads (default: 8)
        output_traffic_demand: Whether to generate traffic demand (default: False)
        traffic_demand_file: Custom path for traffic demand (optional, auto-generated if empty)
        traffic_collection_rate: Statistics collection rate (default: "10us")
        routing_method: Routing method ('shortest_path', 'ugal', 'ugal_threshold', 'nexullance', default: 'shortest_path')
        calculate_throughput: Whether to calculate and return throughput (default: True)
        **additional_config: Additional configuration parameters
        
    Returns:
        - If calculate_throughput=True: dict with throughput_gbps, throughput_file, etc.
        - If calculate_throughput=False: True if successful, False otherwise
    """
    config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'LOAD': load,
        'traffic_pattern': traffic_pattern,
        'routing_method': routing_method
    }
    
    # Generate traffic demand filename if tracing is enabled
    if output_traffic_demand:
        if not traffic_demand_file:
            traffic_demand_file = _generate_traffic_demand_trace_filename(config, 'merlin')
        config['traffic_demand_file'] = traffic_demand_file
        config['traffic_collection_rate'] = traffic_collection_rate
        print(f"Traffic demand will be saved to: {traffic_demand_file}")
    
    if calculate_throughput or not output_traffic_demand:
        # Generate throughput filename
        throughput_file = _generate_throughput_filename(config, 'merlin')
        # Add routing method to filename for clarity
        if routing_method != 'shortest_path':
            throughput_file = throughput_file.replace('.csv', f'_{routing_method}.csv')
        config['throughput_file'] = throughput_file
        config['traffic_collection_rate'] = traffic_collection_rate
    
    if calculate_throughput:
        print(f"\n{'='*80}")
        print(f"Running {routing_method.upper()} routing simulation")
        print(f"  Topology: {topo_name} (V={V}, D={D})")
        print(f"  Load: {load}")
        print(f"  Traffic: {traffic_pattern}")
        if 'throughput_file' in config:
            print(f"  Throughput file: {config['throughput_file']}")
        print(f"{'='*80}\n")
    
    config.update(additional_config)
    
    stdout, stderr, returncode, sim_dir = _run_sst(config, 'merlin', num_threads)
    
    if returncode != 0:
        print(f"ERROR: SST simulation failed")
        return None if calculate_throughput else False
    
    # Calculate and return throughput if requested
    if calculate_throughput and 'throughput_file' in config:
        try:
            throughput_gbps = _calculate_throughput_from_linkcontrol(config['throughput_file'])
            print(f"\n{routing_method.upper()} Throughput: {throughput_gbps:.4f} Gbps")
            
            return {
                'throughput_gbps': throughput_gbps,
                'throughput_file': config['throughput_file'],
                'routing_method': routing_method,
                'sim_dir': str(sim_dir)
            }
        except Exception as e:
            print(f"ERROR: Failed to calculate throughput: {e}")
            return None
    
    return True


def run_ember_simulation(topo_name: str, V: int, D: int, benchmark: str,
                        bench_args: str = "", traffic_trace_file: str = "",
                        cores_per_ep: int = 1, link_bw: int = 16, num_threads: int = 8,
                        enable_traffic_trace: bool = True, 
                        routing_method: str = "shortest_path",
                        **additional_config):
    """
    Run EFM (Ember+Firefly+Merlin) MPI benchmark simulation.
    
    Supports:
    - shortest_path: Standard shortest path routing
    - ugal: Universal Globally-Adaptive Load-balancing routing
    
    Args:
        topo_name: Topology name (e.g., "RRG", "Slimfly", "DDF")
        V: Number of vertices/routers
        D: Degree of routers
        benchmark: Ember benchmark name (e.g., "FFT3D", "Allreduce")
        bench_args: Benchmark arguments (e.g., " nx=100 ny=100 nz=100 npRow=12")
        traffic_trace_file: Custom path for traffic trace (optional, auto-generated if empty)
        cores_per_ep: Number of cores per endpoint (default: 1)
        link_bw: Link bandwidth in Gbps (default: 16)
        num_threads: SST threads (default: 8)
        enable_traffic_trace: Whether to generate traffic trace (default: True)
        routing_method: Routing method ('shortest_path', 'ugal', default: 'shortest_path')
        **additional_config: Additional configuration parameters
        
    Returns:
        True if successful, False otherwise
    """
    config = {
        'UNIFIED_ROUTER_LINK_BW': link_bw,
        'V': V,
        'D': D,
        'topo_name': topo_name,
        'benchmark': benchmark,
        'benchargs': bench_args,
        'Cores_per_EP': cores_per_ep,
        'routing_method': routing_method
    }
    
    # Generate traffic trace filename if tracing is enabled
    if enable_traffic_trace:
        if not traffic_trace_file:
            traffic_trace_file = _generate_traffic_demand_trace_filename(config, 'EFM')
        config['traffic_trace_file'] = traffic_trace_file
        print(f"Traffic trace will be saved to: {traffic_trace_file}")
    
    config.update(additional_config)
    
    stdout, stderr, returncode, sim_dir = _run_sst(config, 'EFM', num_threads)
    return returncode == 0


def _run_sst(config_dict: dict, template_type: str, num_threads: int = 8):
    """
    Internal function to run SST simulation with given config and template.
    
    Args:
        config_dict: Complete configuration dictionary
        template_type: Template type ('EFM' or 'merlin')
        num_threads: Number of SST threads
        
    Returns:
        Tuple of (stdout, stderr, return_code, sim_dir)
    """
    template_map = {
        'EFM': 'sst_EFM_config_template.py',
        'merlin': 'sst_merlin_config_template.py'
    }
    
    if template_type not in template_map:
        raise ValueError(f"Unknown template: {template_type}. Use 'EFM' or 'merlin'")
    
    script_dir = Path(__file__).parent
    template_file = script_dir / template_map[template_type]
    
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")
    
    # Create unique simulation directory using timestamp and PID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sim_id = f"{timestamp}_{os.getpid()}"
    sim_dir = SIMULATION_RESULTS_DIR / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    
    # Create config file in simulation directory
    config_filename = f"sst_config_{template_type}_{sim_id}.py"
    config_file_path = sim_dir / config_filename
    
    # Write configuration file
    with open(config_file_path, 'w') as file:
        # Write all imports at the top
        file.write("import numpy as np\n")
        file.write("import sys\n")
        file.write("import os\n")
        
        # Add all necessary paths
        file.write(f"sys.path.insert(0, r'{PROJECT_ROOT}')\n\n")

        file.write("# Project-specific imports\n")
        file.write("from topoResearch.topologies.HPC_topo import HPC_topo\n")
        file.write("from traffic_analyser.demand_matrix_analyser import demand_matrix_analyser\n")
        file.write("from sst_ultility.ultility import convert_nexullance_RT_to_SST_format\n\n")
        
        # Write Nexullance configuration
        file.write("# Nexullance module configuration\n")
        file.write(f"NEXULLANCE_MODULE_PATH = '{NEXULLANCE_MODULE_PATH}'\n")
        file.write(f"NEXULLANCE_CONTAINER_CLASS = '{NEXULLANCE_CONTAINER_CLASS}'\n\n")
        
        # Write config dict in readable format
        file.write("config_dict = {\n")
        for key, value in config_dict.items():
            file.write(f"    {repr(key)}: {repr(value)},\n")
        file.write("}\n\n")
        
        # Append template content (without imports)
        with open(template_file, 'r') as template_file_handle:
            file.write(template_file_handle.read())
    
    # Run SST simulation
    cmd = ["sst", "-n", f"{num_threads}", str(config_file_path)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    # Save simulation output to files
    output_file = sim_dir / f"simulation_output_{sim_id}.txt"
    with open(output_file, 'w') as f:
        f.write(stdout)
    
    if stderr:
        error_file = sim_dir / f"simulation_errors_{sim_id}.txt"
        with open(error_file, 'w') as f:
            f.write(stderr)
    
    # Print summary
    print(f"SST Simulation Complete:")
    print(f"  - Results saved to: {sim_dir}")
    print(f"  - Config file: {config_filename}")
    print(f"  - Output file: {output_file.name}")
    if stderr:
        print(f"  - Error file: {error_file.name}")
    print(f"\nSST Output:\n{stdout}")
    if stderr:
        print(f"\nSST Errors:\n{stderr}")
        
    return stdout, stderr, process.returncode, sim_dir


