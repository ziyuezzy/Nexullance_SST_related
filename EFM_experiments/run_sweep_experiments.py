#!/usr/bin/env python3
"""
EFM Sample Sweep Experiments - Reproducing archive/EFM_experiments/RRG_4CPE
Compares routing methods across multiple MPI benchmarks with MD sample sweep:
- shortest_path: Standard shortest path routing (baseline)
- ugal: Universal Globally-Adaptive Load-balancing routing
- nexullance_MD: Multi-demand Nexullance with varying number of samples (num_samples=1 replaces SD)
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import csv
import argparse
from typing import Optional

# Add project root to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sst_ultility.ultility import (
    run_ember_simulation, 
    run_ember_experiment_with_nexullance,
    _extract_simulation_time_from_output
)


def write_csv_row(filename: str, content_row: list):
    """Append a row to a CSV file."""
    with open(filename, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(content_row)
        csv_file.flush()


def run_benchmark_sample_sweep(
    benchmark_name: str,
    problem_sizes: list,
    param_name: str,
    bench_args_template: str,
    topo_name: str = "RRG",
    V: int = 36,
    D: int = 5,
    cores_per_ep: int = 4,
    sample_counts: Optional[list] = None
) -> dict:
    """
    Generic workflow for running benchmark experiments with sample sweep.
    
    This unified function handles all routing method comparisons (shortest_path, 
    ugal, nexullance_SD, nexullance_MD) across different problem sizes and sample counts.
    
    Args:
        benchmark_name: Name of the benchmark (e.g., "Allreduce", "Alltoall", "FFT3D")
        problem_sizes: List of problem sizes to test
        param_name: Parameter name for CSV output (e.g., "count", "bytes", "nx")
        bench_args_template: Template string for benchmark arguments with {size} placeholder
        topo_name: Topology name (default: "RRG")
        V: Number of vertices/routers (default: 36)
        D: Degree of routers (default: 5)
        cores_per_ep: Cores per endpoint (default: 4)
        sample_counts: List of sample counts for MD method (default: [1,2,4,8,16,32,64,128])
    
    Returns:
        dict: Paths to CSV output files for each routing method
    """
    if sample_counts is None:
        sample_counts = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
    
    # Ensure num_samples=1 is included (replaces SD)
    if 1 not in sample_counts:
        sample_counts = [1] + sorted(sample_counts)
    
    print("\n" + "="*80)
    print(f"{benchmark_name.upper()} SAMPLE SWEEP EXPERIMENTS")
    print("="*80)
    
    # Configuration
    link_bw = 16
    num_threads = 8
    
    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = SCRIPT_DIR / f"{topo_name}_V{V}_D{D}_CPE{cores_per_ep}_sample_sweep"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Network info string for CSV
    network_info = f"{topo_name}_V{V}_D{D}"
    
    # CSV files - consolidated baseline methods and separate MD sweep
    csv_files = {
        "baseline_methods": output_dir / f"{network_info}_{benchmark_name}_{param_name}_baseline_methods_{timestamp}.csv",
        "nexullance_MD": output_dir / f"{network_info}_{benchmark_name}_{param_name}_nexullance_MD_sample_sweep_{timestamp}.csv"
    }
    
    # Write headers
    write_csv_row(str(csv_files["baseline_methods"]), 
                 ["network", param_name, "shortest_path_ms", "ugal_ms", "ugal_speedup"])
    write_csv_row(str(csv_files["nexullance_MD"]), 
                 ["network", param_name, "num_samples", "baseline_sim_time_ms", 
                  "optimized_sim_time_ms", "speedup", "improvement_percent"])
    
    # Main experiment loop
    for size in problem_sizes:
        print(f"\n{'='*80}")
        print(f"Problem Size: {param_name}={size}")
        print(f"{'='*80}")
        
        bench_args = bench_args_template.format(size=size)
        
        # 1. Shortest-path baseline (collect traffic demand once per problem size)
        print(f"\n[1/3] Running SHORTEST-PATH baseline and collecting traffic demand...")
        
        # Generate demand file path to check if it exists
        config = {
            'UNIFIED_ROUTER_LINK_BW': link_bw,
            'V': V,
            'D': D,
            'topo_name': topo_name,
            'benchmark': benchmark_name,
            'benchargs': bench_args,
            'Cores_per_EP': cores_per_ep,
        }
        
        print(f"  Running baseline to get simulation time...")
        from sst_ultility.ultility import _run_sst, _extract_simulation_time_from_output
        baseline_config = {
            'UNIFIED_ROUTER_LINK_BW': link_bw,
            'V': V, 'D': D,
            'topo_name': topo_name,
            'benchmark': benchmark_name,
            'benchargs': bench_args,
            'Cores_per_EP': cores_per_ep,
            'routing_method': 'shortest_path'
        }
        stdout, stderr, returncode, sim_dir = _run_sst(baseline_config, 'EFM', num_threads)
        if returncode == 0:
            output_file = sim_dir / f"simulation_output_{sim_dir.name}.txt"
            baseline_time = _extract_simulation_time_from_output(str(output_file))
            if baseline_time:
                print(f"✓ Baseline time: {baseline_time:.4f} ms")
            else:
                print(f"ERROR: Could not extract baseline time")
                continue
        else:
            print(f"ERROR: Baseline simulation failed")
            continue
        
        # 2. UGAL routing
        print(f"\n[2/3] Running UGAL...")
        from sst_ultility.ultility import _run_sst
        ugal_config = {
            'UNIFIED_ROUTER_LINK_BW': link_bw,
            'V': V, 'D': D,
            'topo_name': topo_name,
            'benchmark': benchmark_name,
            'benchargs': bench_args,
            'Cores_per_EP': cores_per_ep,
            'routing_method': 'ugal'
        }
        stdout, stderr, returncode, sim_dir = _run_sst(ugal_config, 'EFM', num_threads)
        ugal_time = None
        ugal_speedup = None
        if returncode == 0:
            output_file = sim_dir / f"simulation_output_{sim_dir.name}.txt"
            ugal_time = _extract_simulation_time_from_output(str(output_file))
            if ugal_time:
                ugal_speedup = baseline_time / ugal_time
                print(f"✓ UGAL time: {ugal_time:.4f} ms, speedup: {ugal_speedup:.4f}x")
            else:
                print(f"ERROR: Could not extract UGAL time for {param_name}={size}")
        else:
            print(f"ERROR: UGAL simulation failed for {param_name}={size}")
        
        # Write consolidated baseline methods result
        write_csv_row(str(csv_files["baseline_methods"]), 
                     [network_info, size, baseline_time, 
                      ugal_time if ugal_time else '', ugal_speedup if ugal_speedup else ''])
        
        # 3. Multi-demand Nexullance (MD) with sample sweep (starting from num_samples=1)
        print(f"\n[3/3] Running MULTI-DEMAND Nexullance (MD) - SAMPLE SWEEP...")
        for num_samples in sample_counts:
            print(f"  Testing with {num_samples} samples...")
            
            try:
                md_results = run_ember_experiment_with_nexullance(
                    topo_name=topo_name, V=V, D=D,
                    benchmark=benchmark_name, bench_args=bench_args,
                    cores_per_ep=cores_per_ep, link_bw=link_bw,
                    num_threads=num_threads,
                    traffic_collection_rate = "1us",
                    nexullance_method="MD",
                    num_demand_samples=num_samples
                )
                
                if md_results:
                    md_time = md_results['optimized_sim_time_ms']
                    md_speedup = md_results['speedup']
                    md_improvement = md_results['improvement_percent']
                    write_csv_row(str(csv_files["nexullance_MD"]),
                                 [network_info, size, num_samples, baseline_time, md_time, md_speedup, md_improvement])
                    print(f"    ✓ MD ({num_samples} samples): {md_time:.4f} ms, speedup: {md_speedup:.4f}x")
                else:
                    print(f"    ✗ MD failed with {num_samples} samples")
                    
            except ValueError as e:
                print(f"    ⚠ ValueError encountered: {e}")
                print(f"    ⚠ Terminating sample sweep at {num_samples} samples (insufficient data)")
                break
    
    print(f"\n{'='*80}")
    print(f"{benchmark_name.upper()} EXPERIMENTS COMPLETE")
    print(f"{'='*80}")
    print(f"Results saved to: {output_dir}")
    return csv_files


def run_allreduce_sample_sweep(topo_name="RRG", V=36, D=5, cores_per_ep=4):
    """
    Run Allreduce experiments with sample sweep for MD method.
    
    Args:
        topo_name: Topology name (default: "RRG")
        V: Number of vertices/routers (default: 36)
        D: Degree of routers (default: 5)
        cores_per_ep: Cores per endpoint (default: 4)
    
    Problem sizes: [256, 512, 1024, 2048]
    Sample counts: [1, 2, 4, 8, 16, 32, 64, 128] (1 replaces previous SD method)
    """
    return run_benchmark_sample_sweep(
        benchmark_name="Allreduce",
        problem_sizes=[256],
        # problem_sizes=[256, 512, 1024, 2048],
        param_name="count",
        bench_args_template=" iterations=10 count={size}",
        topo_name=topo_name,
        V=V,
        D=D,
        cores_per_ep=cores_per_ep
    )


def run_alltoall_sample_sweep(topo_name="RRG", V=36, D=5, cores_per_ep=4):
    """
    Run Alltoall experiments with sample sweep for MD method.
    
    Args:
        topo_name: Topology name (default: "RRG")
        V: Number of vertices/routers (default: 36)
        D: Degree of routers (default: 5)
        cores_per_ep: Cores per endpoint (default: 4)
    
    Message sizes: [1, 8, 64] bytes
    Sample counts: [1, 2, 4, 8, 16, 32, 64, 128] (1 replaces previous SD method)
    """
    return run_benchmark_sample_sweep(
        benchmark_name="Alltoall",
        problem_sizes=[64],
        # problem_sizes=[1, 8, 64],
        param_name="bytes",
        bench_args_template=" bytes={size}",
        topo_name=topo_name,
        V=V,
        D=D,
        cores_per_ep=cores_per_ep
    )


def run_fft3d_sample_sweep(topo_name="RRG", V=36, D=5, cores_per_ep=4):
    """
    Run FFT3D experiments with sample sweep for MD method.
    
    Args:
        topo_name: Topology name (default: "RRG")
        V: Number of vertices/routers (default: 36)
        D: Degree of routers (default: 5)
        cores_per_ep: Cores per endpoint (default: 4)
    
    Problem sizes: [256, 512, 1024, 2048]
    Sample counts: [1, 2, 4, 8, 16, 32, 64, 128]
    """
    return run_benchmark_sample_sweep(
        benchmark_name="FFT3D",
        problem_sizes=[256],
        # problem_sizes=[256, 512, 1024, 2048],
        param_name="nx",
        bench_args_template=" nx={size} ny={size} nz={size} npRow=12",
        topo_name=topo_name,
        V=V,
        D=D,
        cores_per_ep=cores_per_ep
    )


def main():
    """Run all sample sweep experiments."""
    parser = argparse.ArgumentParser(
        description="EFM Sample Sweep Experiments - Compare routing methods with varying MD sample counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default RRG(36,5) topology:
  python3.12 run_sample_sweep_experiments.py
  
  # Run with custom topology:
  python3.12 run_sample_sweep_experiments.py --topo DDF --V 40 --D 6
  
  # Run with different cores per endpoint:
  python3.12 run_sample_sweep_experiments.py --cores-per-ep 8
        """
    )
    parser.add_argument('--topo', '--topo-name', dest='topo_name', type=str, default='RRG',
                       help='Topology name (default: RRG)')
    parser.add_argument('--V', '--vertices', dest='V', type=int, default=36,
                       help='Number of vertices/routers (default: 36)')
    parser.add_argument('--D', '--degree', dest='D', type=int, default=5,
                       help='Degree of routers (default: 5)')
    parser.add_argument('--cores-per-ep', type=int, default=4,
                       help='Cores per endpoint (default: 4)')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("EFM SAMPLE SWEEP EXPERIMENTS")
    print("Reproducing archive/EFM_experiments/RRG_4CPE with new framework")
    print("="*80)
    print(f"\nTopology Configuration:")
    print(f"  Topology: {args.topo_name}")
    print(f"  Vertices (V): {args.V}")
    print(f"  Degree (D): {args.D}")
    print(f"  Cores per EP: {args.cores_per_ep}")
    print(f"  Endpoints: {args.V * ((args.D + 1) // 2)}")
    print(f"  Total Cores: {args.V * ((args.D + 1) // 2) * args.cores_per_ep}")
    print("\nBenchmarks to run:")
    # print("  - Allreduce (count: 256, 512, 1024, 2048)")
    # print("  - Alltoall (bytes: 1, 8, 64)")
    # print("  - FFT3D (nx=ny=nz: 256, 512, 1024, 2048, npRow=12)")
    print("\nFor each benchmark:")
    print("  1. shortest_path (baseline) - collect traffic demand once")
    print("  2. ugal")
    print("  3. nexullance_MD (multi-demand, sweep samples: 1,2,4,8,16,32,64,128)")
    print("     Note: num_samples=1 replaces the previous SD (single-demand) method")
    print("="*80)
    
    # Run all experiments with specified topology
    run_allreduce_sample_sweep(args.topo_name, args.V, args.D, args.cores_per_ep)
    run_alltoall_sample_sweep(args.topo_name, args.V, args.D, args.cores_per_ep)
    run_fft3d_sample_sweep(args.topo_name, args.V, args.D, args.cores_per_ep)
    
    print("\n" + "="*80)
    print("ALL EXPERIMENTS COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    sys.exit(main())
