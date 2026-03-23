#!/usr/bin/env python3
"""
Plot EFM Sample Sweep Results by Topology.

Creates one figure per topology with three subplots showing different benchmarks:
- Allreduce, Alltoall, FFT3D
- X-axis: Number of samples for MD_Nexullance_IT
- Horizontal lines: UGAL variants and Shortest Path baseline
- Shared legend outside the plot boxes
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Dict, List

# Set style for academic paper publication-quality plots
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'serif']
plt.rcParams['font.size'] = 13
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 15
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['legend.fontsize'] = 12
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.edgecolor'] = 'black'
plt.rcParams['legend.fancybox'] = False
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['xtick.major.width'] = 1.0
plt.rcParams['ytick.major.width'] = 1.0
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def discover_all_topologies(search_dir: Path) -> List[str]:
    """
    Discover all topology result directories in the specified directory.
    
    Args:
        search_dir: Directory to search in
    
    Returns:
        List of topology names (e.g., ['DDF', 'RRG', 'Slimfly'])
    """
    result_dirs = [d for d in search_dir.glob('*_sample_sweep') if d.is_dir()]
    
    topologies = set()
    for d in result_dirs:
        # Extract topology from directory name pattern: {Topo}_V{V}_D{D}_CPE{cores}_sample_sweep
        name_parts = d.name.split('_')
        if name_parts:
            topo = name_parts[0]
            # Verify this is a valid topology by checking for CSV files
            if list(d.glob('*_baseline_methods_*.csv')):
                topologies.add(topo)
    
    return sorted(list(topologies))


def find_topology_data(search_dir: Path, topo_name: str) -> Optional[Path]:
    """
    Find the result directory for a specific topology.
    
    Args:
        search_dir: Directory to search in
        topo_name: Topology name (e.g., 'RRG', 'DDF', 'Slimfly')
    
    Returns:
        Path to topology result directory or None
    """
    pattern = f"{topo_name}_*_sample_sweep"
    matches = list(search_dir.glob(pattern))
    return matches[0] if matches else None


def load_benchmark_data(results_dir: Path, benchmark: str, problem_size: Optional[int] = None):
    """
    Load data for a specific benchmark from the results directory.
    
    Args:
        results_dir: Directory containing results
        benchmark: Benchmark name (Allreduce, Alltoall, FFT3D)
        problem_size: Optional problem size to filter
    
    Returns:
        Tuple of (baseline_df, ugal_df, md_df) or None if files not found
    """
    # Find CSV files
    baseline_pattern = f"*_{benchmark}_*_baseline_methods_*.csv"
    ugal_pattern = f"*_{benchmark}_*_ugal_sweep_*.csv"
    md_pattern = f"*_{benchmark}_*_nexullance_MD_sample_sweep_*.csv"
    
    baseline_files = list(results_dir.glob(baseline_pattern))
    ugal_files = list(results_dir.glob(ugal_pattern))
    md_files = list(results_dir.glob(md_pattern))
    
    if not baseline_files or not md_files:
        return None
    
    # Load data
    baseline_df = pd.read_csv(baseline_files[0])
    ugal_df = pd.read_csv(ugal_files[0]) if ugal_files else None
    md_df = pd.read_csv(md_files[0])
    
    # Determine parameter name
    param_cols = [col for col in baseline_df.columns if col in ['count', 'bytes', 'nx']]
    if not param_cols:
        return None
    param_name = param_cols[0]
    
    # Filter by problem size or use first available
    if problem_size is None:
        problem_size = baseline_df[param_name].iloc[0]
    
    baseline_df = baseline_df[baseline_df[param_name] == problem_size]
    if ugal_df is not None:
        ugal_df = ugal_df[ugal_df[param_name] == problem_size]
    md_df = md_df[md_df[param_name] == problem_size]
    
    if baseline_df.empty or md_df.empty:
        return None
    
    return baseline_df, ugal_df, md_df, param_name, problem_size


def plot_topology_comparison(topo_name: str, results_dir: Path, output_dir: Path):
    """
    Create a figure with three subplots showing different benchmarks for one topology.
    
    Args:
        topo_name: Topology name (e.g., 'RRG', 'DDF', 'Slimfly')
        results_dir: Directory containing results for this topology
        output_dir: Directory to save plot
    """
    # Benchmarks to plot
    benchmarks = ['Allreduce', 'Alltoall', 'FFT3D']
    benchmark_titles = {
        'Allreduce': 'Allreduce',
        'Alltoall': 'Alltoall',
        'FFT3D': 'FFT3D'
    }
    
    # Create figure with 3 subplots in a row
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # UGAL styles (matching previous scripts)
    ugal_styles = [
        {'color': '#ff7f0e', 'linestyle': '-',      'linewidth': 1.5, 'label': 'UGAL-1'},
        {'color': '#d62728', 'linestyle': '--',     'linewidth': 1.5, 'label': 'UGAL-2'},
        {'color': '#9467bd', 'linestyle': '-.',     'linewidth': 1.5, 'label': 'UGAL-3'},
        {'color': '#8c564b', 'linestyle': ':',      'linewidth': 1.8, 'label': 'UGAL-4'},
        {'color': '#e377c2', 'linestyle': (0, (3, 1, 1, 1)), 'linewidth': 1.5, 'label': 'UGAL-5'},
    ]
    
    for idx, benchmark in enumerate(benchmarks):
        ax = axes[idx]
        
        # Load data for this benchmark
        data = load_benchmark_data(results_dir, benchmark)
        
        if data is None:
            print(f"  ⚠ No data for {benchmark}")
            ax.text(0.5, 0.5, f'No data for {benchmark}', 
                   ha='center', va='center', fontsize=14)
            ax.set_title(benchmark_titles[benchmark], fontsize=15, fontweight='bold', pad=10)
            continue
        
        baseline_df, ugal_df, md_df, param_name, problem_size = data
        
        # Sort MD data by num_samples
        md_df_sorted = md_df.sort_values('num_samples')
        num_samples = md_df_sorted['num_samples'].values
        md_speedups = md_df_sorted['speedup'].values
        
        # Plot MD Nexullance speedup vs num_samples (green line with circles)
        ax.plot(num_samples, md_speedups, 'o-', linewidth=1.8, markersize=7, 
                label='MD_Nexullance_IT', color='#2ca02c', markerfacecolor='white', 
                markeredgewidth=1.5, zorder=3)
        
        # Plot UGAL sweep as horizontal lines
        if ugal_df is not None and not ugal_df.empty:
            ugal_df_sorted = ugal_df.sort_values('num_valiant')
            num_valiant = ugal_df_sorted['num_valiant'].values
            ugal_speedups = ugal_df_sorted['speedup'].values
            
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
        ax.set_xlabel('Number of Samples', fontsize=14, fontweight='bold')
        if idx == 0:
            ax.set_ylabel('Speedup over Shortest Path', fontsize=14, fontweight='bold')
        
        # Use log scale for x-axis
        ax.set_xscale('log', base=2)
        ax.set_xticks(num_samples)
        ax.set_xticklabels([str(int(n)) for n in num_samples], rotation=45, ha='right')
        
        # Dynamic y-axis limits
        max_speedup = max(md_speedups.max(), 
                         ugal_df_sorted['speedup'].max() if ugal_df is not None else 1.0)
        y_max = max(2.0, max_speedup * 1.1)
        ax.set_ylim((0.8, y_max))
        
        # Title with parameter info
        param_display = f"{param_name}={problem_size}"
        ax.set_title(f'{benchmark_titles[benchmark]}\n({param_display})', 
                    fontsize=15, fontweight='bold', pad=10)
        
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)
    
    # Extract network info from directory name
    network_info = results_dir.name.split('_sample_sweep')[0]
    
    # Add main title
    fig.suptitle(f'{topo_name} Topology - Sample Sweep Comparison ({network_info})', 
                fontsize=17, fontweight='bold', y=0.98)
    
    # Add shared legend outside to the right
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center left', bbox_to_anchor=(0.97, 0.5),
              fontsize=11, framealpha=0.98, shadow=False, edgecolor='black',
              fancybox=False, markerscale=0.9)
    
    plt.tight_layout(rect=[0, 0, 0.87, 0.96])
    
    # Save figure
    output_file = output_dir / f"topology_comparison_{topo_name}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Plot saved: {output_file.name}")
    
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Plot EFM sample sweep results by topology',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input-dir', type=str, default=None,
                       help='Directory containing result directories (default: EFM_experiments/)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Directory to save plots (default: EFM_experiments/plots/)')
    
    args = parser.parse_args()
    
    # Set default directories
    if args.input_dir is None:
        input_dir = Path(__file__).resolve().parent
    else:
        input_dir = Path(args.input_dir)
    
    if args.output_dir is None:
        output_dir = input_dir / "plots"
    else:
        output_dir = Path(args.output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("EFM SAMPLE SWEEP - TOPOLOGY COMPARISON")
    print("="*80)
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print("="*80 + "\n")
    
    # Discover all topologies
    topologies = discover_all_topologies(input_dir)
    
    if not topologies:
        print("ERROR: No topology result directories found!")
        print(f"Searched in: {input_dir}")
        return 1
    
    print(f"Found {len(topologies)} topolog{'y' if len(topologies) == 1 else 'ies'}:")
    for topo in topologies:
        topo_dir = find_topology_data(input_dir, topo)
        if topo_dir:
            print(f"  - {topo}: {topo_dir.name}")
    print()
    
    # Create plots for each topology
    for topo_name in topologies:
        topo_dir = find_topology_data(input_dir, topo_name)
        if not topo_dir:
            print(f"  ⚠ Could not find directory for {topo_name}")
            continue
        
        print(f"Processing {topo_name}...")
        plot_topology_comparison(topo_name, topo_dir, output_dir)
    
    print("\n" + "="*80)
    print("PLOTTING COMPLETE")
    print("="*80)
    print(f"Plots saved to: {output_dir}")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
