#!/usr/bin/env python3
"""
Plot Sample Sweep Results - Compare routing methods across sample counts

This script visualizes the results from run_sweep_experiments.py, showing:
- MD Nexullance speedup vs num_samples (line plot)
- UGAL speedup vs num_valiant (line plot)
- Shortest path as baseline (speedup = 1.0)

Usage:
    # Plot all result directories in current folder (default):
    python3 plot_sweep_results.py
    
    # Plot specific results directory:
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


def discover_all_result_directories(search_dir: Path = None) -> List[Path]:
    """
    Discover all sample_sweep result directories in the specified directory.
    
    Args:
        search_dir: Directory to search in (default: current directory)
    
    Returns:
        List of result directory paths
    """
    if search_dir is None:
        search_dir = Path.cwd()
    
    # Find all directories matching *_sample_sweep pattern
    result_dirs = [d for d in search_dir.glob('*_sample_sweep') if d.is_dir()]
    
    # Filter to only include directories with actual CSV files
    valid_result_dirs = []
    for d in result_dirs:
        if list(d.glob('*_baseline_methods_*.csv')):
            valid_result_dirs.append(d)
    
    return sorted(valid_result_dirs)


def find_csv_files(results_dir: Path, benchmark: str) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """
    Find the CSV files for a specific benchmark in the results directory.
    
    Args:
        results_dir: Directory containing results
        benchmark: Benchmark name (e.g., "Allreduce", "Alltoall", "FFT3D")
    
    Returns:
        Tuple of (baseline_csv_path, ugal_sweep_csv_path, nexullance_md_csv_path)
    """
    # Find baseline methods CSV
    baseline_pattern = f"*_{benchmark}_*_baseline_methods_*.csv"
    baseline_files = list(results_dir.glob(baseline_pattern))
    baseline_csv = baseline_files[0] if baseline_files else None
    
    # Find UGAL sweep CSV
    ugal_pattern = f"*_{benchmark}_*_ugal_sweep_*.csv"
    ugal_files = list(results_dir.glob(ugal_pattern))
    ugal_csv = ugal_files[0] if ugal_files else None
    
    # Find MD sample sweep CSV
    md_pattern = f"*_{benchmark}_*_nexullance_MD_sample_sweep_*.csv"
    md_files = list(results_dir.glob(md_pattern))
    md_csv = md_files[0] if md_files else None
    
    return baseline_csv, ugal_csv, md_csv


def load_and_filter_data(baseline_csv: Path, ugal_csv: Optional[Path], md_csv: Path, 
                         problem_size: Optional[int] = None) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
    """
    Load CSV files and optionally filter by problem size.
    
    Args:
        baseline_csv: Path to baseline methods CSV
        ugal_csv: Path to UGAL sweep CSV (optional)
        md_csv: Path to MD sample sweep CSV
        problem_size: Problem size to filter (None = use first available)
    
    Returns:
        Tuple of (baseline_df, ugal_df, md_df) filtered DataFrames
    """
    baseline_df = pd.read_csv(baseline_csv)
    ugal_df = pd.read_csv(ugal_csv) if ugal_csv else None
    md_df = pd.read_csv(md_csv)
    
    # Determine parameter name (count, bytes, or nx)
    param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
    if not param_cols:
        raise ValueError("Could not determine parameter column (expected 'count', 'bytes', or 'nx')")
    param_name = param_cols[0]
    
    # Filter by problem size if specified
    if problem_size is not None:
        baseline_df = baseline_df[baseline_df[param_name] == problem_size]
        if ugal_df is not None:
            ugal_df = ugal_df[ugal_df[param_name] == problem_size]
        md_df = md_df[md_df[param_name] == problem_size]
        
        if baseline_df.empty or md_df.empty:
            raise ValueError(f"No data found for {param_name}={problem_size}")
    else:
        # Use first available problem size
        problem_size = baseline_df[param_name].iloc[0]
        baseline_df = baseline_df[baseline_df[param_name] == problem_size]
        if ugal_df is not None:
            ugal_df = ugal_df[ugal_df[param_name] == problem_size]
        md_df = md_df[md_df[param_name] == problem_size]
        print(f"Using {param_name}={problem_size} (first available in dataset)")
    
    return baseline_df, ugal_df, md_df


def plot_sample_sweep(baseline_df: pd.DataFrame, ugal_df: Optional[pd.DataFrame], md_df: pd.DataFrame, 
                      benchmark: str, problem_size: int, 
                      param_name: str, network_info: str,
                      output_file: Optional[Path] = None):
    """
    Create comparison plot of routing methods including UGAL sweep.
    
    Args:
        baseline_df: DataFrame with baseline methods results
        ugal_df: DataFrame with UGAL sweep results (optional)
        md_df: DataFrame with MD sample sweep results
        benchmark: Benchmark name
        problem_size: Problem size value
        param_name: Parameter name (count, bytes, nx)
        network_info: Network configuration string
        output_file: Optional output file path for saving plot
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Sort MD data by num_samples for proper line plotting
    md_df_sorted = md_df.sort_values('num_samples')
    num_samples = md_df_sorted['num_samples'].values
    md_speedups = md_df_sorted['speedup'].values
    
    # Plot MD Nexullance speedup vs num_samples (green line with circles)
    ax.plot(num_samples, md_speedups, 'o-', linewidth=1.5, markersize=6, 
            label='MD_Nexullance_IT', color='#2ca02c', markerfacecolor='white', 
            markeredgewidth=1.5, zorder=3)
    
    # Plot UGAL sweep if available - each as a horizontal line
    if ugal_df is not None and not ugal_df.empty:
        ugal_df_sorted = ugal_df.sort_values('num_valiant')
        num_valiant = ugal_df_sorted['num_valiant'].values
        ugal_speedups = ugal_df_sorted['speedup'].values
        
        # Define distinct visual styles for different UGAL variants
        # Using different colors, line styles, and widths for clear distinction
        ugal_styles = [
            {'color': '#ff7f0e', 'linestyle': '-',      'linewidth': 1.5, 'label': 'UGAL-1'},  # Solid orange
            {'color': '#d62728', 'linestyle': '--',     'linewidth': 1.5, 'label': 'UGAL-2'},  # Dashed red
            {'color': '#9467bd', 'linestyle': '-.',     'linewidth': 1.5, 'label': 'UGAL-3'},  # Dash-dot purple
            {'color': '#8c564b', 'linestyle': ':',      'linewidth': 1.8, 'label': 'UGAL-4'},  # Dotted brown (thicker)
            {'color': '#e377c2', 'linestyle': (0, (3, 1, 1, 1)), 'linewidth': 1.5, 'label': 'UGAL-5'},  # Dash-dot-dot pink
        ]
        
        # Plot each UGAL variant as a horizontal line with distinct style
        for i, (nv, speedup) in enumerate(zip(num_valiant, ugal_speedups)):
            if i < len(ugal_styles):
                style = ugal_styles[i]
                ax.axhline(y=speedup, 
                          color=style['color'], 
                          linestyle=style['linestyle'], 
                          linewidth=style['linewidth'],
                          label=style['label'], 
                          zorder=2, 
                          alpha=0.85)
    
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
    
    # Set x-axis ticks to only show MD sample counts
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


def plot_all_problem_sizes(baseline_csv: Path, ugal_csv: Optional[Path], md_csv: Path, 
                           benchmark: str, network_info: str,
                           output_dir: Path):
    """
    Create separate plots for each problem size in the dataset.
    
    Args:
        baseline_csv: Path to baseline methods CSV
        ugal_csv: Path to UGAL sweep CSV (optional)
        md_csv: Path to MD sample sweep CSV
        benchmark: Benchmark name
        network_info: Network configuration string
        output_dir: Directory to save plots
    """
    baseline_df = pd.read_csv(baseline_csv)
    ugal_df = pd.read_csv(ugal_csv) if ugal_csv else None
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
        ugal_filtered = ugal_df[ugal_df[param_name] == size] if ugal_df is not None else None
        md_filtered = md_df[md_df[param_name] == size]
        
        output_file = output_dir / f"{network_info}_{benchmark}_{param_name}_{size}_sample_sweep.png"
        
        plot_sample_sweep(baseline_filtered, ugal_filtered, md_filtered, benchmark, size, 
                         param_name, network_info, output_file)
    
    print(f"\nAll plots saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Plot sample sweep experiment results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plot all result directories in current folder (default):
  python3 plot_sweep_results.py
  
  # Plot specific results directory:
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep
  
  # Plot all sizes for specific benchmark:
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce
  
  # Plot specific benchmark and size:
  python3 plot_sweep_results.py --results-dir RRG_V36_D5_CPE4_sample_sweep --benchmark Allreduce --size 256
        """
    )
    
    parser.add_argument('--results-dir', type=str, default=None,
                       help='Directory containing experiment results (default: discover all *_sample_sweep directories)')
    parser.add_argument('--benchmark', type=str, default=None,
                       choices=['Allreduce', 'Alltoall', 'FFT3D'],
                       help='Benchmark to plot (default: plot all available)')
    parser.add_argument('--size', type=int, default=None,
                       help='Problem size to plot (default: plot all sizes)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path (only used when plotting single benchmark+size)')
    
    args = parser.parse_args()
    
    # Determine which result directories to process
    if args.results_dir:
        # Single directory specified
        results_dir = Path(args.results_dir)
        if not results_dir.is_absolute():
            results_dir = Path(__file__).parent / results_dir
        
        if not results_dir.exists():
            print(f"ERROR: Results directory not found: {results_dir}")
            return 1
        
        result_dirs = [results_dir]
    else:
        # Discover all result directories in current folder
        script_dir = Path(__file__).parent
        result_dirs = discover_all_result_directories(script_dir)
        
        if not result_dirs:
            print(f"\nERROR: No *_sample_sweep result directories found in {script_dir}")
            print("Please run experiments first or specify --results-dir")
            return 1
        
        print(f"\n{'='*80}")
        print(f"DISCOVERED {len(result_dirs)} RESULT DIRECTOR{'Y' if len(result_dirs) == 1 else 'IES'}")
        print(f"{'='*80}")
        for d in result_dirs:
            print(f"  - {d.name}")
        print(f"{'='*80}\n")
    
    # Process each result directory
    total_plots = 0
    summary = []
    
    for results_dir in result_dirs:
        network_info = results_dir.name.split('_sample_sweep')[0]
        
        # Create plots subdirectory
        plots_dir = results_dir / 'plots'
        plots_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*80}")
        print(f"PROCESSING: {results_dir.name}")
        print(f"{'='*80}")
        
        try:
            # Discover all available benchmarks if not specified
            if args.benchmark is None:
                benchmarks = discover_all_benchmarks(results_dir)
                if not benchmarks:
                    print(f"  ⚠ No benchmark results found in {results_dir.name}")
                    summary.append({'dir': results_dir.name, 'status': 'No benchmarks found', 'plots': 0})
                    continue
                print(f"  Discovered benchmarks: {', '.join(benchmarks)}")
            else:
                benchmarks = [args.benchmark]
            
            dir_plot_count = 0
            
            # Process each benchmark
            for benchmark in benchmarks:
                print(f"\n  {'-'*76}")
                print(f"  Processing {benchmark}...")
                print(f"  {'-'*76}")
                
                # Find CSV files
                baseline_csv, ugal_csv, md_csv = find_csv_files(results_dir, benchmark)
                
                if not baseline_csv or not md_csv:
                    print(f"    ⚠ Skipping {benchmark}: CSV files not found")
                    continue
                
                print(f"    ✓ Found baseline CSV: {baseline_csv.name}")
                if ugal_csv:
                    print(f"    ✓ Found UGAL sweep CSV: {ugal_csv.name}")
                else:
                    print(f"    ⚠ No UGAL sweep CSV found (will plot without UGAL data)")
                print(f"    ✓ Found MD sweep CSV: {md_csv.name}")
                
                # Plot all sizes or specific size
                if args.size is None:
                    # Plot all problem sizes for this benchmark
                    plot_all_problem_sizes(baseline_csv, ugal_csv, md_csv, benchmark, 
                                           network_info, plots_dir)
                    # Count plots generated
                    baseline_df_temp = pd.read_csv(baseline_csv)
                    param_cols = [col for col in baseline_df_temp.columns if col in ['count', 'bytes', 'nx']]
                    if param_cols:
                        num_plots = len(baseline_df_temp[param_cols[0]].unique())
                        dir_plot_count += num_plots
                        total_plots += num_plots
                else:
                    # Plot specific size
                    baseline_df, ugal_df, md_df = load_and_filter_data(baseline_csv, ugal_csv, md_csv, args.size)
                    
                    # Determine parameter name
                    param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
                    param_name = param_cols[0]
                    problem_size = baseline_df[param_name].iloc[0]
                    
                    # Determine output file
                    if args.output:
                        output_file = Path(args.output)
                    else:
                        output_file = plots_dir / f"{network_info}_{benchmark}_{param_name}_{problem_size}_sample_sweep.png"
                    
                    plot_sample_sweep(baseline_df, ugal_df, md_df, benchmark, problem_size,
                                    param_name, network_info, output_file)
                    dir_plot_count += 1
                    total_plots += 1
            
            summary.append({
                'dir': results_dir.name,
                'status': 'Success',
                'plots': dir_plot_count,
                'plots_dir': str(plots_dir.relative_to(Path(__file__).parent))
            })
            
            print(f"\n  ✓ Generated {dir_plot_count} plot(s) for {results_dir.name}")
            print(f"  ✓ Plots saved to: {plots_dir}")
            
        except Exception as e:
            print(f"\n  ✗ ERROR processing {results_dir.name}: {e}")
            import traceback
            traceback.print_exc()
            summary.append({'dir': results_dir.name, 'status': f'Error: {e}', 'plots': 0})
            continue
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total result directories processed: {len(result_dirs)}")
    print(f"Total plots generated: {total_plots}")
    print(f"\nDetails:")
    for item in summary:
        status_icon = '✓' if item['status'] == 'Success' else '✗'
        print(f"  {status_icon} {item['dir']}: {item['plots']} plot(s) - {item['status']}")
        if 'plots_dir' in item:
            print(f"      → {item['plots_dir']}")
    print(f"{'='*80}")
    
    return 0 if total_plots > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
