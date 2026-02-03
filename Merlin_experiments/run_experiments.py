#!/usr/bin/env python3
"""
Comprehensive Merlin experiment script comparing three routing methods:
1. Shortest-path routing (ASP)
2. Nexullance IT optimization
3. UGAL adaptive routing

Sweeps offered load from 0.1 to 1.0 and collects throughput metrics.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import argparse
import numpy as np

# Add project root to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sst_ultility.ultility import (
    run_merlin_experiment_with_nexullance,
    run_merlin_simulation
)


def run_comparison_experiment(topo_name: str, V: int, D: int,
                              traffic_pattern: str = "uniform",
                              link_bw: int = 16,
                              num_threads: int = 8,
                              load_start: float = 0.1,
                              load_end: float = 1.0,
                              load_step: float = 0.2,
                              routing_methods: list = None):
    """
    Run comparison experiment across multiple routing methods.
    
    Args:
        topo_name: Topology name (RRG, Slimfly, DDF)
        V: Number of vertices/routers
        D: Degree of routers
        traffic_pattern: Traffic pattern (uniform, shift_1, shift_half)
        link_bw: Link bandwidth in Gbps
        num_threads: Number of SST threads
        load_start: Starting load
        load_end: Ending load
        load_step: Load increment
        routing_methods: List of routing methods to compare ['shortest_path', 'nexullance', 'ugal', 'md_nexullance']
    
    Returns:
        DataFrame with comparison results
    """
    if routing_methods is None:
        routing_methods = ['shortest_path', 'nexullance', 'ugal']
    
    # Expand 'ugal' into ugal_1 through ugal_5 variants
    expanded_routing_methods = []
    for method in routing_methods:
        if method == 'ugal':
            for num_valiant in range(1, 6):
                expanded_routing_methods.append(f'ugal_{num_valiant}')
        else:
            expanded_routing_methods.append(method)
    
    routing_methods = expanded_routing_methods
    
    print("\n" + "="*80)
    print("ROUTING COMPARISON EXPERIMENT")
    print("="*80)
    print(f"Topology:         {topo_name} (V={V}, D={D})")
    print(f"Traffic Pattern:  {traffic_pattern}")
    print(f"Load Range:       {load_start} to {load_end} (step={load_step})")
    print(f"Link Bandwidth:   {link_bw} Gbps")
    print(f"Routing Methods:  {', '.join(routing_methods)}")
    print("="*80 + "\n")
    
    # Store results for all routing methods
    all_results = []
    
    # Generate load values
    loads = np.arange(load_start, load_end + 0.001, load_step)
    
    # Run experiments for each routing method
    for routing_method in routing_methods:
        print("\n" + "="*80)
        print(f"TESTING ROUTING METHOD: {routing_method.upper()}")
        print("="*80)
        
        for load in loads:
            print(f"\nLoad = {load:.1f}")
            
            if routing_method == 'nexullance' or routing_method == 'md_nexullance':
                # Use the nexullance experiment workflow (SD or MD variant)
                result = run_merlin_experiment_with_nexullance(
                    topo_name=topo_name,
                    V=V,
                    D=D,
                    load=load,
                    traffic_pattern=traffic_pattern,
                    link_bw=link_bw,
                    num_threads=num_threads,
                    traffic_collection_rate="200us",
                    demand_scaling_factor=10.0,
                    nexullance_method='MD' if routing_method == 'md_nexullance' else 'SD',
                    num_demand_samples=1
                )
                
                if result:
                    all_results.append({
                        'load': load,
                        'routing_method': routing_method,
                        'throughput_gbps': result['optimized_throughput_gbps'],
                        'baseline_throughput_gbps': result['baseline_throughput_gbps'],
                        'result_file': result.get('throughput_file', '')
                    })
                    print(f"✓ {routing_method}: {result['optimized_throughput_gbps']:.4f} Gbps")
                else:
                    all_results.append({
                        'load': load,
                        'routing_method': routing_method,
                        'throughput_gbps': None,
                        'baseline_throughput_gbps': None,
                        'result_file': None
                    })
                    print(f"✗ {routing_method} FAILED")
                    
            else:
                # Handle ugal variants (ugal_1, ugal_2, etc.)
                if routing_method.startswith('ugal_'):
                    base_method = 'ugal'
                    num_valiant = int(routing_method.split('_')[1])
                    additional_config = {'vn_ugal_num_valiant': str(num_valiant)}
                else:
                    base_method = routing_method
                    additional_config = {}
                
                # Use the routing-specific simulation function
                result = run_merlin_simulation(
                    topo_name=topo_name,
                    V=V,
                    D=D,
                    load=load,
                    traffic_pattern=traffic_pattern,
                    routing_method=base_method,
                    link_bw=link_bw,
                    num_threads=num_threads,
                    calculate_throughput=True,
                    **additional_config
                )
                
                if result:
                    all_results.append({
                        'load': load,
                        'routing_method': routing_method,
                        'throughput_gbps': result['throughput_gbps'],
                        'baseline_throughput_gbps': None,
                        'result_file': result.get('throughput_file', '')
                    })
                    print(f"✓ {routing_method}: {result['throughput_gbps']:.4f} Gbps")
                else:
                    all_results.append({
                        'load': load,
                        'routing_method': routing_method,
                        'throughput_gbps': None,
                        'baseline_throughput_gbps': None,
                        'result_file': None
                    })
                    print(f"✗ {routing_method} FAILED")
    
    # Create results DataFrame
    df = pd.DataFrame(all_results)
    
    # Print summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    # Pivot table for easier viewing
    pivot_df = df.pivot(index='load', columns='routing_method', values='throughput_gbps')
    print("\nThroughput (Gbps) by Load and Routing Method:")
    print("-" * 80)
    print(pivot_df.to_string())
    print("-" * 80)
    
    # Calculate statistics for each routing method
    print("\n" + "="*80)
    print("ROUTING METHOD STATISTICS")
    print("="*80)
    for method in routing_methods:
        method_data = df[df['routing_method'] == method]
        successful = method_data[method_data['throughput_gbps'].notna()]
        if len(successful) > 0:
            print(f"\n{method.upper()}:")
            print(f"  Successful runs:    {len(successful)} / {len(method_data)}")
            print(f"  Average throughput: {successful['throughput_gbps'].mean():.4f} Gbps")
            print(f"  Max throughput:     {successful['throughput_gbps'].max():.4f} Gbps")
            print(f"  Min throughput:     {successful['throughput_gbps'].min():.4f} Gbps")
    
    # Save results to script directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_csv = SCRIPT_DIR / f"routing_comparison_{topo_name}_V{V}_D{D}_{traffic_pattern}_{timestamp}.csv"
    df.to_csv(results_csv, index=False)
    print(f"\nResults saved to: {results_csv}")
    
    return df


def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Compare shortest-path, Nexullance, and UGAL routing methods',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Topology parameters
    parser.add_argument('--topo-name', '-t', type=str, default='RRG',
                        help='Topology name (RRG, Slimfly, DDF)')
    parser.add_argument('--V', type=int, default=16,
                        help='Number of vertices/routers')
    parser.add_argument('--D', type=int, default=5,
                        help='Degree of routers')
    
    # Traffic parameters
    parser.add_argument('--traffic-pattern', '-p', type=str, default='uniform',
                        help='Traffic pattern (uniform, shift_X, shift_half)')
    parser.add_argument('--link-bw', type=int, default=16,
                        help='Link bandwidth in Gbps')
    
    # Load sweep parameters
    parser.add_argument('--load-start', type=float, default=0.1,
                        help='Starting load')
    parser.add_argument('--load-end', type=float, default=1.0,
                        help='Ending load')
    parser.add_argument('--load-step', type=float, default=0.1,
                        help='Load increment step')
    
    # Routing methods
    parser.add_argument('--routing-methods', nargs='+', 
                        default=['shortest_path', 'nexullance', 'md_nexullance', 'ugal', 'ugal_threshold'],
                        choices=['shortest_path', 'nexullance', 'md_nexullance', 'ugal', 'ugal_threshold'],
                        help='Routing methods to compare (ugal will be expanded to ugal_1 through ugal_5)')
    
    # System parameters
    parser.add_argument('--num-threads', type=int, default=8,
                        help='Number of SST threads')
    
    args = parser.parse_args()
    
    # Run comparison experiment
    run_comparison_experiment(
        topo_name=args.topo_name,
        V=args.V,
        D=args.D,
        traffic_pattern=args.traffic_pattern,
        link_bw=args.link_bw,
        num_threads=args.num_threads,
        load_start=args.load_start,
        load_end=args.load_end,
        load_step=args.load_step,
        routing_methods=args.routing_methods
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
