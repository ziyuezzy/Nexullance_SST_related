#!/usr/bin/env python3
"""
EFM Scaling Experiments: Application Performance and Runtime Analysis

For a given topology type (Slimfly, DDF, Polarfly), sweep through different network sizes
and measure:
1. Application speedup of Nexullance and UGAL vs shortest path (lower sim_time_ms is better)
2. Simulation runtime scaling with network size

Uses topology configurations from global_helpers.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import time
import json

# Add project root to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sst_ultility.ultility import (
    run_ember_experiment_with_nexullance,
    _run_sst,
    _extract_simulation_time_from_output
)
from topoResearch.global_helpers import sf_configs_t1k, ddf_configs_t1k, pf_regular_configs_t1k


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

BENCHMARK_DEFAULTS = {
    'Allreduce': {'param_name': 'count',  'default_size': 256,  'template': ' iterations=10 count={size}'},
    'Alltoall':  {'param_name': 'bytes',  'default_size': 64,   'template': ' bytes={size}'},
    'FFT3D':     {'param_name': 'nx',     'default_size': 256,  'template': ' nx={size} ny={size} nz={size} npRow=12'},
}


def get_bench_args(benchmark: str, problem_size: int) -> str:
    """Build bench_args string for the given benchmark and problem size."""
    if benchmark not in BENCHMARK_DEFAULTS:
        raise ValueError(f"Unknown benchmark '{benchmark}'. Choose from: {list(BENCHMARK_DEFAULTS)}")
    return BENCHMARK_DEFAULTS[benchmark]['template'].format(size=problem_size)


# ---------------------------------------------------------------------------
# Topology config helpers
# ---------------------------------------------------------------------------

def get_topology_configs(topo_name: str, max_routers: int = 1000):
    """
    Get topology configurations for the specified topology type.

    Args:
        topo_name: Topology name (Slimfly, DDF, Polarfly)
        max_routers: Maximum number of routers to include

    Returns:
        List of (V, D) tuples
    """
    topo_name_lower = topo_name.lower()

    if 'slimfly' in topo_name_lower or topo_name_lower == 'sf':
        configs = sf_configs_t1k
    elif 'ddf' in topo_name_lower:
        configs = ddf_configs_t1k
    elif 'polarfly' in topo_name_lower or topo_name_lower == 'pf':
        configs = pf_regular_configs_t1k
    else:
        raise ValueError(f"Unknown topology: {topo_name}. Use 'Slimfly', 'DDF', or 'Polarfly'")

    filtered_configs = [(v, d) for v, d in configs if v <= max_routers]

    print(f"\n{topo_name} configurations (V ≤ {max_routers}):")
    print(f"  Number of configs: {len(filtered_configs)}")
    if filtered_configs:
        print(f"  Router range: {filtered_configs[0][0]} to {filtered_configs[-1][0]}")

    return filtered_configs


# ---------------------------------------------------------------------------
# Single experiment runner
# ---------------------------------------------------------------------------

def run_single_experiment(topo_name: str, V: int, D: int, routing_method: str,
                          benchmark: str, bench_args: str,
                          cores_per_ep: int, link_bw: int, num_threads: int,
                          num_samples: int = 32):
    """
    Run a single EFM experiment and measure both application time and wall-clock runtime.

    Args:
        routing_method: 'shortest_path', 'ugal', or 'nexullance'
        num_samples: Number of demand samples for nexullance MD method

    Returns:
        dict with sim_time_ms, runtime_seconds, success
    """
    start_time = time.time()

    try:
        if routing_method == 'nexullance':
            result = run_ember_experiment_with_nexullance(
                topo_name=topo_name,
                V=V,
                D=D,
                benchmark=benchmark,
                bench_args=bench_args,
                cores_per_ep=cores_per_ep,
                link_bw=link_bw,
                num_threads=num_threads,
                traffic_collection_rate=f"{int(V)}us",  # using a 'magic linear formula' here, the sampling interval (us) equals to the number of switches.
                nexullance_method="MD",
                num_demand_samples=num_samples
            )
            sim_time = result['optimized_sim_time_ms'] if result else None

        else:
            # shortest_path or ugal — run directly via _run_sst
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
            stdout, stderr, returncode, sim_dir = _run_sst(config, 'EFM', num_threads)
            if returncode == 0:
                output_file = sim_dir / f"simulation_output_{sim_dir.name}.txt"
                sim_time = _extract_simulation_time_from_output(str(output_file))
            else:
                sim_time = None

        runtime_seconds = time.time() - start_time
        return {
            'success': sim_time is not None,
            'sim_time_ms': sim_time,
            'runtime_seconds': runtime_seconds
        }

    except Exception as e:
        runtime_seconds = time.time() - start_time
        print(f"ERROR in {routing_method}: {e}")
        return {
            'success': False,
            'sim_time_ms': None,
            'runtime_seconds': runtime_seconds,
            'error': str(e)
        }


# ---------------------------------------------------------------------------
# Main scaling loop
# ---------------------------------------------------------------------------

def run_scaling_experiment(topo_name: str,
                           benchmark: str = "Allreduce",
                           problem_size: int = 256,
                           cores_per_ep: int = 4,
                           link_bw: int = 16,
                           num_threads: int = 8,
                           max_routers: int = 1000,
                           routing_methods: list = None,
                           num_samples: int = 32):
    """
    Run EFM scaling experiments across different network sizes.

    Args:
        topo_name: Topology name (Slimfly, DDF, Polarfly)
        benchmark: Ember benchmark name (Allreduce, Alltoall, FFT3D)
        problem_size: Problem size for the benchmark
        cores_per_ep: Number of cores per endpoint
        link_bw: Link bandwidth in Gbps
        num_threads: Number of SST threads
        max_routers: Maximum number of routers to include
        routing_methods: List of routing methods to compare
        num_samples: Number of MD samples for nexullance

    Returns:
        DataFrame with scaling results
    """
    if routing_methods is None:
        routing_methods = ['shortest_path', 'ugal', 'nexullance']

    bench_args = get_bench_args(benchmark, problem_size)
    configs = get_topology_configs(topo_name, max_routers)

    print("\n" + "="*80)
    print("EFM SCALING EXPERIMENT")
    print("="*80)
    print(f"Topology:         {topo_name}")
    print(f"Configurations:   {len(configs)} network sizes")
    print(f"Benchmark:        {benchmark} (size={problem_size})")
    print(f"  bench_args:     {bench_args.strip()}")
    print(f"Cores per EP:     {cores_per_ep}")
    print(f"Link Bandwidth:   {link_bw} Gbps")
    print(f"Routing Methods:  {', '.join(routing_methods)}")
    if 'nexullance' in routing_methods:
        print(f"  MD samples:     {num_samples}")
    print("="*80 + "\n")

    all_results = []

    for config_idx, (V, D) in enumerate(configs):
        EPR = (D + 1) // 2
        num_endpoints = V * EPR
        total_cores = num_endpoints * cores_per_ep

        print("\n" + "="*80)
        print(f"Configuration {config_idx+1}/{len(configs)}: V={V}, D={D}, EPR={EPR}")
        print(f"  Endpoints: {num_endpoints}, Total cores: {total_cores}")
        print("="*80)

        config_results = {
            'V': V,
            'D': D,
            'EPR': EPR,
            'num_endpoints': num_endpoints,
            'total_cores': total_cores
        }

        # Run each routing method
        for routing_method in routing_methods:
            print(f"\n  Testing {routing_method}...", end=" ", flush=True)

            result = run_single_experiment(
                topo_name=topo_name,
                V=V,
                D=D,
                routing_method=routing_method,
                benchmark=benchmark,
                bench_args=bench_args,
                cores_per_ep=cores_per_ep,
                link_bw=link_bw,
                num_threads=num_threads,
                num_samples=num_samples
            )

            config_results[f'{routing_method}_sim_time_ms'] = result['sim_time_ms']
            config_results[f'{routing_method}_runtime'] = result['runtime_seconds']
            config_results[f'{routing_method}_success'] = result['success']

            if result['success']:
                print(f"✓ {result['sim_time_ms']:.4f} ms (wall: {result['runtime_seconds']:.1f}s)")
            else:
                print(f"✗ FAILED (wall: {result['runtime_seconds']:.1f}s)")

        # Calculate speedups relative to shortest_path (lower sim_time_ms = higher speedup)
        baseline_ok = config_results.get('shortest_path_success', False)
        if baseline_ok:
            baseline_sim_time = config_results['shortest_path_sim_time_ms']
            for method in routing_methods:
                if method != 'shortest_path' and config_results.get(f'{method}_success', False):
                    method_time = config_results[f'{method}_sim_time_ms']
                    if method_time and method_time > 0:
                        config_results[f'{method}_speedup'] = baseline_sim_time / method_time
                    else:
                        config_results[f'{method}_speedup'] = None
                elif method != 'shortest_path':
                    config_results[f'{method}_speedup'] = None

        all_results.append(config_results)

        # Save intermediate results after every configuration
        df_intermediate = pd.DataFrame(all_results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        intermediate_csv = SCRIPT_DIR / f"scaling_{topo_name}_{benchmark}_intermediate_{timestamp}.csv"
        df_intermediate.to_csv(intermediate_csv, index=False)

        # Stop early if nothing succeeded for this configuration
        any_success = any(config_results.get(f"{m}_success", False) for m in routing_methods)
        if not any_success:
            print("No methods succeeded for this configuration. Terminating scaling sweep early.")
            break

    # Final DataFrame
    df = pd.DataFrame(all_results)

    print_scaling_summary(df, topo_name, benchmark, problem_size, routing_methods)

    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_csv = SCRIPT_DIR / f"scaling_{topo_name}_{benchmark}_{timestamp}.csv"
    df.to_csv(results_csv, index=False)
    print(f"\n✓ Final results saved to: {results_csv}")

    # Save metadata
    metadata = {
        'topo_name': topo_name,
        'benchmark': benchmark,
        'problem_size': problem_size,
        'bench_args': bench_args.strip(),
        'cores_per_ep': cores_per_ep,
        'link_bw': link_bw,
        'num_threads': num_threads,
        'max_routers': max_routers,
        'routing_methods': routing_methods,
        'num_samples': num_samples,
        'num_configs': len(configs),
        'timestamp': timestamp
    }
    metadata_json = SCRIPT_DIR / f"scaling_{topo_name}_{benchmark}_{timestamp}_metadata.json"
    with open(metadata_json, 'w') as f:
        json.dump(metadata, f, indent=2)

    return df


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_scaling_summary(df: pd.DataFrame, topo_name: str, benchmark: str,
                          problem_size: int, routing_methods: list):
    """Print a summary of scaling experiment results."""

    print("\n" + "="*80)
    print("SCALING EXPERIMENT SUMMARY")
    print("="*80)
    print(f"Topology: {topo_name}, Benchmark: {benchmark}, Size: {problem_size}")

    successful_df = df[df.get('shortest_path_success', pd.Series(False, index=df.index)) == True].copy() \
        if 'shortest_path_success' in df.columns else df.copy()

    if len(successful_df) > 0:
        print(f"\nSuccessful experiments: {len(successful_df)} / {len(df)}")
        print(f"Network size range: V={successful_df['V'].min()} to {successful_df['V'].max()}")

        for method in routing_methods:
            sim_col = f'{method}_sim_time_ms'
            success_col = f'{method}_success'
            if sim_col in successful_df.columns:
                method_ok = successful_df[successful_df.get(success_col, pd.Series(False)) == True]
                if len(method_ok) > 0:
                    print(f"\n{method.upper()}:")
                    print(f"  Success rate:      {len(method_ok)} / {len(successful_df)}")
                    print(f"  Avg sim time:      {method_ok[sim_col].mean():.4f} ms")
                    print(f"  Sim time range:    {method_ok[sim_col].min():.4f} – {method_ok[sim_col].max():.4f} ms")
                    if method != 'shortest_path':
                        speedup_col = f'{method}_speedup'
                        if speedup_col in method_ok.columns:
                            valid = method_ok[speedup_col].dropna()
                            if len(valid) > 0:
                                print(f"  Avg speedup:       {valid.mean():.4f}x")
                                print(f"  Max speedup:       {valid.max():.4f}x")

    print("="*80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="EFM Scaling Experiments: measure application speedup and runtime scaling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sweep Slimfly network sizes with Allreduce benchmark
  python3 run_scaling_experiments.py --topo-name Slimfly --benchmark Allreduce --problem-size 256

  # DDF with Alltoall, limit to 500 routers
  python3 run_scaling_experiments.py --topo-name DDF --benchmark Alltoall --problem-size 64 --max-routers 500

  # Polarfly, custom num_samples for nexullance
  python3 run_scaling_experiments.py --topo-name Polarfly --num-samples 64

  # Skip nexullance, only compare shortest_path and ugal
  python3 run_scaling_experiments.py --topo-name DDF --routing-methods shortest_path ugal
        """
    )

    # Topology
    parser.add_argument('--topo-name', '-t', type=str, required=True,
                        help='Topology name: Slimfly/SF, DDF, Polarfly/PF')
    parser.add_argument('--max-routers', type=int, default=1000,
                        help='Maximum number of routers (default: 1000)')

    # Benchmark
    parser.add_argument('--benchmark', '-b', type=str, default='Allreduce',
                        choices=list(BENCHMARK_DEFAULTS),
                        help='Ember benchmark name (default: Allreduce)')
    parser.add_argument('--problem-size', type=int, default=None,
                        help='Problem size for the benchmark (default: benchmark-specific default)')
    parser.add_argument('--cores-per-ep', type=int, default=4,
                        help='Cores per endpoint (default: 4)')
    parser.add_argument('--link-bw', type=int, default=16,
                        help='Link bandwidth in Gbps (default: 16)')

    # Routing
    parser.add_argument('--routing-methods', nargs='+',
                        default=['shortest_path', 'ugal', 'nexullance'],
                        help='Routing methods to compare (default: shortest_path ugal nexullance)')
    parser.add_argument('--num-samples', type=int, default=32,
                        help='Number of MD samples for nexullance (default: 32)')

    # System
    parser.add_argument('--num-threads', type=int, default=8,
                        help='Number of SST threads (default: 8)')

    args = parser.parse_args()

    # Resolve default problem size
    problem_size = args.problem_size
    if problem_size is None:
        problem_size = BENCHMARK_DEFAULTS[args.benchmark]['default_size']

    run_scaling_experiment(
        topo_name=args.topo_name,
        benchmark=args.benchmark,
        problem_size=problem_size,
        cores_per_ep=args.cores_per_ep,
        link_bw=args.link_bw,
        num_threads=args.num_threads,
        max_routers=args.max_routers,
        routing_methods=args.routing_methods,
        num_samples=args.num_samples
    )


if __name__ == "__main__":
    sys.exit(main())
