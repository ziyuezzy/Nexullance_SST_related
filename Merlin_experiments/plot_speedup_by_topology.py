#!/usr/bin/env python3
"""
Plot speedup comparisons by topology.

Creates one figure per topology with three subplots showing speedup 
for different traffic patterns (uniform, shift_1, shift_half).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse

# Add project root to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set matplotlib style for publication-quality plots
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


# Define distinct styles for each routing method (matching analyze_results.py)
ROUTING_STYLES = {
    'shortest_path': {
        'marker': 'o', 
        'linestyle': '-', 
        'linewidth': 2.5, 
        'markersize': 8, 
        'alpha': 0.95, 
        'color': '#2F4F4F',  # Dark slate gray
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'nexullance': {
        'marker': 's', 
        'linestyle': '--', 
        'linewidth': 2.5, 
        'markersize': 8, 
        'alpha': 0.95, 
        'color': '#2ca02c',  # Green
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'md_nexullance': {
        'marker': 'D', 
        'linestyle': '--', 
        'linewidth': 2.5, 
        'markersize': 7, 
        'alpha': 0.95, 
        'color': '#1f7a1f',  # Dark green
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_1': {
        'marker': '^', 
        'linestyle': '-', 
        'linewidth': 2.2, 
        'markersize': 8, 
        'alpha': 0.90, 
        'color': '#ff7f0e',  # Orange
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_2': {
        'marker': 'v', 
        'linestyle': '--', 
        'linewidth': 2.2, 
        'markersize': 8, 
        'alpha': 0.90, 
        'color': '#d62728',  # Red
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_3': {
        'marker': '<', 
        'linestyle': '-.', 
        'linewidth': 2.2, 
        'markersize': 8, 
        'alpha': 0.90, 
        'color': '#9467bd',  # Purple
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_4': {
        'marker': '>', 
        'linestyle': ':', 
        'linewidth': 2.5, 
        'markersize': 8, 
        'alpha': 0.90, 
        'color': '#8c564b',  # Brown
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_5': {
        'marker': 'p', 
        'linestyle': (0, (3, 1, 1, 1)), 
        'linewidth': 2.2, 
        'markersize': 9, 
        'alpha': 0.90, 
        'color': '#e377c2',  # Pink
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'ugal_threshold': {
        'marker': '*', 
        'linestyle': (0, (5, 2)), 
        'linewidth': 2.5, 
        'markersize': 11, 
        'alpha': 0.95, 
        'color': '#17becf',  # Cyan
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    },
    'default': {
        'marker': 'x', 
        'linestyle': '-', 
        'linewidth': 2.5, 
        'markersize': 8, 
        'alpha': 0.9, 
        'color': '#7f7f7f',  # Gray
        'markeredgecolor': 'white',
        'markeredgewidth': 1.5
    }
}


def format_method_label(method):
    """Format routing method name for display."""
    if method.startswith('ugal_'):
        return f"UGAL-{method.split('_')[1]}"
    elif method == 'md_nexullance':
        return "MD_Nexullance_IT"
    elif method == 'nexullance':
        return "SD_Nexullance_IT"
    elif method == 'shortest_path':
        return "Shortest Path"
    else:
        return method.replace('_', ' ').title()


def load_results_by_topology(input_dir):
    """
    Load all result files and organize by topology and traffic pattern.
    
    Args:
        input_dir: Directory containing result CSV files
        
    Returns:
        Dictionary: {topology: {traffic_pattern: DataFrame}}
    """
    result_files = list(input_dir.glob("routing_comparison_*.csv"))
    
    if not result_files:
        return {}
    
    results = {}
    
    for result_file in result_files:
        # Parse filename: routing_comparison_{topo}_{traffic}_{timestamp}.csv
        filename = result_file.stem
        
        # Extract topology
        topo_name = None
        for topo in ['RRG', 'Slimfly', 'DDF']:
            if topo in filename:
                topo_name = topo
                break
        
        # Extract traffic pattern
        if 'uniform' in filename:
            traffic = 'uniform'
        elif 'shift_half' in filename:
            traffic = 'shift_half'
        elif 'shift_1' in filename:
            traffic = 'shift_1'
        else:
            traffic = None
        
        if topo_name and traffic:
            # Load data
            df = pd.read_csv(result_file)
            
            # Initialize nested dict if needed
            if topo_name not in results:
                results[topo_name] = {}
            
            results[topo_name][traffic] = df
    
    return results


def plot_topology_speedup(topo_name, traffic_data, output_dir):
    """
    Create a figure with three subplots showing speedup for different traffic patterns.
    
    Args:
        topo_name: Topology name (RRG, Slimfly, DDF)
        traffic_data: Dictionary {traffic_pattern: DataFrame}
        output_dir: Directory to save plot
    """
    # Traffic patterns in order
    traffic_patterns = ['uniform', 'shift_1', 'shift_half']
    traffic_labels = {
        'uniform': 'Uniform Traffic',
        'shift_1': 'Shift-1 Traffic',
        'shift_half': 'Shift-Half Traffic'
    }
    
    # Create figure with 3 subplots in a row
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, traffic in enumerate(traffic_patterns):
        if traffic not in traffic_data:
            print(f"  Warning: No data for {topo_name} {traffic}")
            continue
        
        ax = axes[idx]
        df = traffic_data[traffic]
        
        # Get shortest path baseline
        baseline_data = df[df['routing_method'] == 'shortest_path'].sort_values('load')
        
        # Get all routing methods except shortest_path and md_nexullance
        routing_methods = [m for m in df['routing_method'].unique() 
                          if m not in ['shortest_path', 'md_nexullance']]
        
        # Track max speedup for dynamic y-axis scaling
        max_speedup = 1.0
        
        # Plot each routing method
        for method in routing_methods:
            method_data = df[df['routing_method'] == method].sort_values('load')
            
            # Merge with baseline on load
            merged = pd.merge(method_data, baseline_data[['load', 'throughput_gbps']], 
                             on='load', suffixes=('', '_baseline'))
            
            # Calculate speedup
            merged['speedup'] = merged['throughput_gbps'] / merged['throughput_gbps_baseline']
            
            # Track maximum speedup for y-axis scaling
            max_speedup = max(max_speedup, merged['speedup'].max())
            
            # Get style for this method
            style = ROUTING_STYLES.get(method, ROUTING_STYLES['default'])
            
            # Format label
            label = format_method_label(method)
            
            # Plot
            ax.plot(merged['load'], merged['speedup'], 
                   marker=style['marker'],
                   linestyle=style['linestyle'],
                   linewidth=style['linewidth'],
                   markersize=style['markersize'],
                   alpha=style['alpha'],
                   color=style['color'],
                   markeredgewidth=style['markeredgewidth'],
                   markeredgecolor=style['markeredgecolor'],
                   label=label)
        
        # Add baseline reference line
        ax.axhline(y=1.0, color='#7f7f7f', linestyle=':', linewidth=1.5, 
                  label='Shortest Path Baseline', alpha=0.8, zorder=1)
        
        # Formatting
        ax.set_xlabel('Offered Load', fontsize=14, fontweight='bold')
        if idx == 0:
            ax.set_ylabel('Speedup vs Shortest Path', fontsize=14, fontweight='bold')
        
        # Set dynamic y-axis limits based on data
        # Use 0.8 as minimum, and add 10% padding above max speedup
        y_max = max(2.0, max_speedup * 1.1)  # At least 2.0, or 110% of max speedup
        ax.set_ylim((0.8, y_max))
        
        ax.set_title(traffic_labels[traffic], fontsize=15, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Add main title
    fig.suptitle(f'{topo_name} Topology - Speedup Comparison', 
                fontsize=17, fontweight='bold', y=0.98)
    
    # Add legend outside to the right of the rightmost subplot
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center left', bbox_to_anchor=(0.97, 0.5),
              fontsize=11, framealpha=0.98, shadow=False, edgecolor='black',
              fancybox=False, markerscale=0.9)
    
    plt.tight_layout(rect=[0, 0, 0.87, 0.96])
    
    # Save figure
    output_file = output_dir / f"speedup_comparison_{topo_name}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Plot saved: {output_file.name}")
    
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Plot speedup comparisons by topology',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input-dir', type=str, default=None,
                       help='Directory containing result CSV files (default: Merlin_experiments/)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Directory to save plots (default: Merlin_experiments/plots/)')
    
    args = parser.parse_args()
    
    # Set default directories
    if args.input_dir is None:
        input_dir = SCRIPT_DIR
    else:
        input_dir = Path(args.input_dir)
    
    if args.output_dir is None:
        output_dir = SCRIPT_DIR / "plots"
    else:
        output_dir = Path(args.output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("SPEEDUP COMPARISON BY TOPOLOGY")
    print("="*80)
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print("="*80 + "\n")
    
    # Load results organized by topology and traffic pattern
    results = load_results_by_topology(input_dir)
    
    if not results:
        print("ERROR: No result files found!")
        print(f"Searched in: {input_dir}")
        return 1
    
    print(f"Found data for {len(results)} topolog{'y' if len(results) == 1 else 'ies'}:")
    for topo in results.keys():
        traffic_patterns = list(results[topo].keys())
        print(f"  - {topo}: {', '.join(traffic_patterns)}")
    print()
    
    # Create plots for each topology
    for topo_name, traffic_data in sorted(results.items()):
        print(f"Processing {topo_name}...")
        plot_topology_speedup(topo_name, traffic_data, output_dir)
    
    print("\n" + "="*80)
    print("PLOTTING COMPLETE")
    print("="*80)
    print(f"Plots saved to: {output_dir}")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
