#!/usr/bin/env python3
"""
Plot Sample Sweep Results - Compare routing methods across sample counts

This script visualizes the results from run_sweep_experiments.py, showing:
- MD Nexullance speedup vs num_samples (line plot)
- UGAL speedup as a horizontal reference line
- Shortest path as baseline (speedup = 1.0)

Usage:
    # Plot all available benchmarks and sizes in directory:
    python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep
    
    # Plot specific benchmark only:
    python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce
    
    # Plot specific benchmark and size:
    python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce --size 256
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Tuple, List

# Set style for academic paper publication-quality plots
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'serif']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.edgecolor'] = 'black'
plt.rcParams['legend.fancybox'] = False
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['xtick.major.width'] = 1.0
plt.rcParams['ytick.major.width'] = 1.0
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['figure.figsize'] = (8, 5)
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def discover_all_benchmarks(results_dir: Path) -> List[str]:
    """
    Discover all available benchmarks in the results directory.
    
    Args:
        results_dir: Directory containing results
    
    Returns:
        List of benchmark names found
    """
    benchmarks = set()
    
    # Look for baseline CSV files to discover benchmarks
    for csv_file in results_dir.glob('*_baseline_methods_*.csv'):
        filename = csv_file.name
        # Extract benchmark name from filename pattern: network_benchmark_param_baseline_methods_timestamp.csv
        for bench in ['Allreduce', 'Alltoall', 'FFT3D']:
            if f'_{bench}_' in filename:
                benchmarks.add(bench)
                break
    
    return sorted(list(benchmarks))


def find_csv_files(results_dir: Path, benchmark: str) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Find the CSV files for a specific benchmark in the results directory.
    
    Args:
        results_dir: Directory containing results
        benchmark: Benchmark name (e.g., "Allreduce", "Alltoall", "FFT3D")
    
    Returns:
        Tuple of (baseline_csv_path, nexullance_md_csv_path)
    """
    # Find baseline methods CSV
    baseline_pattern = f"*_{benchmark}_*_baseline_methods_*.csv"
    baseline_files = list(results_dir.glob(baseline_pattern))
    baseline_csv = baseline_files[0] if baseline_files else None
    
    # Find MD sample sweep CSV
    md_pattern = f"*_{benchmark}_*_nexullance_MD_sample_sweep_*.csv"
    md_files = list(results_dir.glob(md_pattern))
    md_csv = md_files[0] if md_files else None
    
    return baseline_csv, md_csv


def load_and_filter_data(baseline_csv: Path, md_csv: Path, problem_size: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load CSV files and optionally filter by problem size.
    
    Args:
        baseline_csv: Path to baseline methods CSV
        md_csv: Path to MD sample sweep CSV
        problem_size: Problem size to filter (None = use first available)
    
    Returns:
        Tuple of (baseline_df, md_df) filtered DataFrames
    """
    baseline_df = pd.read_csv(baseline_csv)
    md_df = pd.read_csv(md_csv)
    
    # Determine parameter name (count, bytes, or nx)
    param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
    if not param_cols:
        raise ValueError("Could not determine parameter column (expected 'count', 'bytes', or 'nx')")
    param_name = param_cols[0]
    
    # Filter by problem size if specified
    if problem_size is not None:
        baseline_df = baseline_df[baseline_df[param_name] == problem_size]
        md_df = md_df[md_df[param_name] == problem_size]
        
        if baseline_df.empty or md_df.empty:
            raise ValueError(f"No data found for {param_name}={problem_size}")
    else:
        # Use first available problem size
        problem_size = baseline_df[param_name].iloc[0]
        baseline_df = baseline_df[baseline_df[param_name] == problem_size]
        md_df = md_df[md_df[param_name] == problem_size]
        print(f"Using {param_name}={problem_size} (first available in dataset)")
    
    return baseline_df, md_df


def plot_sample_sweep(baseline_df: pd.DataFrame, md_df: pd.DataFrame, 
                      benchmark: str, problem_size: int, 
                      param_name: str, network_info: str,
                      output_file: Optional[Path] = None):
    """
    Create comparison plot of routing methods.
    
    Args:
        baseline_df: DataFrame with baseline methods results
        md_df: DataFrame with MD sample sweep results
        benchmark: Benchmark name
        problem_size: Problem size value
        param_name: Parameter name (count, bytes, nx)
        network_info: Network configuration string
        output_file: Optional output file path for saving plot
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Extract data
    ugal_speedup = baseline_df['ugal_speedup'].iloc[0] if 'ugal_speedup' in baseline_df.columns else None
    
    # Sort MD data by num_samples for proper line plotting
    md_df_sorted = md_df.sort_values('num_samples')
    num_samples = md_df_sorted['num_samples'].values
    md_speedups = md_df_sorted['speedup'].values
    
    # Plot MD Nexullance speedup vs num_samples (green line with circles)
    ax.plot(num_samples, md_speedups, 'o-', linewidth=1.5, markersize=6, 
            label='MD_Nexullance_IT', color='#2ca02c', markerfacecolor='white', 
            markeredgewidth=1.5, zorder=3)
    
    # Plot UGAL as horizontal reference line (orange dashed)
    if ugal_speedup is not None and pd.notna(ugal_speedup):
        ax.axhline(y=ugal_speedup, color='#ff7f0e', linestyle='--', linewidth=1.5,
                   label=f'UGAL', zorder=2)
    
    # Plot shortest path baseline (gray dotted at 1.0)
    ax.axhline(y=1.0, color='#7f7f7f', linestyle=':', linewidth=1.2,
               label='Shortest Path', zorder=1)
    
    # Formatting
    ax.set_xlabel('Number of Samples', fontsize=12)
    ax.set_ylabel('Speedup over Shortest Path', fontsize=12)
    ax.set_title(f'{benchmark} ({param_name}={problem_size}, {network_info})', 
                 fontsize=13, pad=15)
    
    # Use log scale for x-axis since samples grow exponentially
    ax.set_xscale('log', base=2)
    
    # Set x-axis ticks to actual sample values
    ax.set_xticks(num_samples)
    ax.set_xticklabels([str(int(n)) for n in num_samples], rotation=45, ha='right')
    
    # Grid
    ax.grid(True, which='both', alpha=0.3)
    ax.set_axisbelow(True)
    
    # Legend outside plot box on the right
    ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), framealpha=1.0)
    
    # Add value annotations for key MD data points (first, last, and max)
    if len(num_samples) > 0:
        # Annotate first point
        ax.annotate(f'{md_speedups[0]:.2f}', (num_samples[0], md_speedups[0]), 
                   textcoords="offset points", xytext=(-15, 8), ha='center', 
                   fontsize=8, alpha=0.7)
        # Annotate last point
        ax.annotate(f'{md_speedups[-1]:.2f}', (num_samples[-1], md_speedups[-1]), 
                   textcoords="offset points", xytext=(15, 8), ha='center', 
                   fontsize=8, alpha=0.7)
        # Annotate max point if different from first/last
        max_idx = np.argmax(md_speedups)
        if max_idx != 0 and max_idx != len(num_samples) - 1:
            ax.annotate(f'{md_speedups[max_idx]:.2f}', (num_samples[max_idx], md_speedups[max_idx]), 
                       textcoords="offset points", xytext=(0, 10), ha='center', 
                       fontsize=8, alpha=0.7)
    
    plt.tight_layout()
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def plot_all_problem_sizes(baseline_csv: Path, md_csv: Path, 
                           benchmark: str, network_info: str,
                           output_dir: Path):
    """
    Create separate plots for each problem size in the dataset.
    
    Args:
        baseline_csv: Path to baseline methods CSV
        md_csv: Path to MD sample sweep CSV
        benchmark: Benchmark name
        network_info: Network configuration string
        output_dir: Directory to save plots
    """
    baseline_df = pd.read_csv(baseline_csv)
    md_df = pd.read_csv(md_csv)
    
    # Determine parameter name
    param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
    if not param_cols:
        raise ValueError("Could not determine parameter column")
    param_name = param_cols[0]
    
    # Get all unique problem sizes
    problem_sizes = sorted(baseline_df[param_name].unique())
    
    print(f"\nGenerating plots for {len(problem_sizes)} problem size(s)...")
    
    for size in problem_sizes:
        print(f"  Plotting {param_name}={size}...")
        baseline_filtered = baseline_df[baseline_df[param_name] == size]
        md_filtered = md_df[md_df[param_name] == size]
        
        output_file = output_dir / f"{network_info}_{benchmark}_{param_name}_{size}_sample_sweep.png"
        
        plot_sample_sweep(baseline_filtered, md_filtered, benchmark, size, 
                         param_name, network_info, output_file)
    
    print(f"\nAll plots saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Plot sample sweep experiment results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plot all available benchmarks and sizes (default):
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep
  
  # Plot all sizes for specific benchmark:
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce
  
  # Plot specific benchmark and size:
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce --size 256
        """
    )
    
    parser.add_argument('--results-dir', type=str, required=True,
                       help='Directory containing experiment results')
    parser.add_argument('--benchmark', type=str, default=None,
                       choices=['Allreduce', 'Alltoall', 'FFT3D'],
                       help='Benchmark to plot (default: plot all available)')
    parser.add_argument('--size', type=int, default=None,
                       help='Problem size to plot (default: plot all sizes)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path (only used when plotting single benchmark+size)')
    
    args = parser.parse_args()
    
    # Resolve results directory
    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = Path(__file__).parent / results_dir
    
    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        return 1
    
    # Extract network info from directory name
    network_info = results_dir.name.split('_sample_sweep')[0]
    
    # Create plots subdirectory
    plots_dir = results_dir / 'plots'
    plots_dir.mkdir(exist_ok=True)
    
    try:
        # Discover all available benchmarks if not specified
        if args.benchmark is None:
            benchmarks = discover_all_benchmarks(results_dir)
            if not benchmarks:
                print(f"\nERROR: No benchmark results found in {results_dir}")
                return 1
            print(f"\nDiscovered benchmarks: {', '.join(benchmarks)}")
            print(f"Generating plots for all benchmarks...\n")
        else:
            benchmarks = [args.benchmark]
        
        # Process each benchmark
        total_plots = 0
        for benchmark in benchmarks:
            print(f"\n{'='*60}")
            print(f"Processing {benchmark}...")
            print(f"{'='*60}")
            
            # Find CSV files
            baseline_csv, md_csv = find_csv_files(results_dir, benchmark)
            
            if not baseline_csv or not md_csv:
                print(f"  ⚠ Skipping {benchmark}: CSV files not found")
                continue
            
            print(f"  ✓ Found baseline CSV: {baseline_csv.name}")
            print(f"  ✓ Found MD sweep CSV: {md_csv.name}")
            
            # Plot all sizes or specific size
            if args.size is None:
                # Plot all problem sizes for this benchmark
                plot_all_problem_sizes(baseline_csv, md_csv, benchmark, 
                                       network_info, plots_dir)
                # Count plots generated
                baseline_df_temp = pd.read_csv(baseline_csv)
                param_cols = [col for col in baseline_df_temp.columns if col in ['count', 'bytes', 'nx']]
                if param_cols:
                    total_plots += len(baseline_df_temp[param_cols[0]].unique())
            else:
                # Plot specific size
                baseline_df, md_df = load_and_filter_data(baseline_csv, md_csv, args.size)
                
                # Determine parameter name
                param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
                param_name = param_cols[0]
                problem_size = baseline_df[param_name].iloc[0]
                
                # Determine output file
                if args.output:
                    output_file = Path(args.output)
                else:
                    output_file = plots_dir / f"{network_info}_{benchmark}_{param_name}_{problem_size}_sample_sweep.png"
                
                plot_sample_sweep(baseline_df, md_df, benchmark, problem_size,
                                param_name, network_info, output_file)
                total_plots += 1
        
        print(f"\n{'='*60}")
        print(f"✓ Successfully generated {total_plots} plot(s)")
        print(f"✓ Plots saved to: {plots_dir}")
        print(f"{'='*60}")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
