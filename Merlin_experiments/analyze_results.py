#!/usr/bin/env python3
"""
Analyze and plot results from routing comparison experiments.

Compares performance of:
1. Shortest-path routing
2. Nexullance IT optimization
3. UGAL adaptive routing
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
from datetime import datetime

# Add project root to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from paths import SIMULATION_RESULTS_DIR


def load_and_merge_results(result_files):
    """
    Load multiple result CSV files and merge them.
    
    Args:
        result_files: List of CSV file paths
        
    Returns:
        Merged DataFrame
    """
    dfs = []
    for file in result_files:
        if Path(file).exists():
            df = pd.read_csv(file)
            dfs.append(df)
        else:
            print(f"Warning: File not found: {file}")
    
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return None


def plot_comparison(df, topo_name, traffic_pattern, output_dir):
    """
    Create comparison plots for routing methods.
    
    Args:
        df: DataFrame with results
        topo_name: Topology name
        traffic_pattern: Traffic pattern name
        output_dir: Directory to save plots
    """
    # Filter data for this topology and traffic pattern
    filtered = df.copy()
    
    # Create figure with subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Define distinct styles for each routing method to avoid overlap confusion
    styles = {
        'shortest_path': {'marker': 'o', 'linestyle': '-', 'linewidth': 2.5, 'markersize': 8, 'alpha': 0.9, 'color': 'black'},
        'nexullance': {'marker': 's', 'linestyle': '--', 'linewidth': 2.5, 'markersize': 7, 'alpha': 0.9, 'color': 'red'},
        'md_nexullance': {'marker': 'd', 'linestyle': '--', 'linewidth': 2.5, 'markersize': 7, 'alpha': 0.9, 'color': 'darkred'},
        'ugal_1': {'marker': '^', 'linestyle': '-.', 'linewidth': 2.0, 'markersize': 7, 'alpha': 0.85, 'color': 'blue'},
        'ugal_2': {'marker': 'v', 'linestyle': '-.', 'linewidth': 2.0, 'markersize': 7, 'alpha': 0.85, 'color': 'cyan'},
        'ugal_3': {'marker': '<', 'linestyle': '-.', 'linewidth': 2.0, 'markersize': 7, 'alpha': 0.85, 'color': 'green'},
        'ugal_4': {'marker': '>', 'linestyle': '-.', 'linewidth': 2.0, 'markersize': 7, 'alpha': 0.85, 'color': 'orange'},
        'ugal_5': {'marker': 'p', 'linestyle': '-.', 'linewidth': 2.0, 'markersize': 7, 'alpha': 0.85, 'color': 'purple'},
        'ugal_threshold': {'marker': '*', 'linestyle': ':', 'linewidth': 2.5, 'markersize': 9, 'alpha': 0.9, 'color': 'magenta'},
        'default': {'marker': 'x', 'linestyle': '-', 'linewidth': 2.5, 'markersize': 7, 'alpha': 0.9, 'color': 'gray'}
    }
    
    # Plot 1: Throughput vs Load
    ax1 = axes[0]
    routing_methods = filtered['routing_method'].unique()
    
    for method in routing_methods:
        method_data = filtered[filtered['routing_method'] == method]
        method_data = method_data.sort_values('load')
        
        # Get style for this method
        style = styles.get(method, styles['default'])
        
        # Format label for better readability
        if method.startswith('ugal_'):
            label = f"UGAL (valiant={method.split('_')[1]})"
        elif method == 'md_nexullance':
            label = "MD_Nexullance_IT_1_sample"
        elif method == 'nexullance':
            label = "SD_Nexullance_IT"
        else:
            label = method.replace('_', ' ').title()
        
        # Plot with distinct markers and line styles
        ax1.plot(method_data['load'], method_data['throughput_gbps'], 
                marker=style['marker'], 
                linestyle=style['linestyle'],
                linewidth=style['linewidth'], 
                markersize=style['markersize'],
                alpha=style['alpha'],
                color=style.get('color'),
                markeredgewidth=1.5,
                markeredgecolor='white',
                label=label)
    
    ax1.set_xlabel('Offered Load', fontsize=12)
    ax1.set_ylabel('Throughput (Gbps)', fontsize=12)
    ax1.set_ylim((0.0, 200))
    ax1.set_title(f'{topo_name} - {traffic_pattern.replace("_", " ").title()} Traffic\nThroughput vs Load', 
                  fontsize=13, fontweight='bold')
    ax1.legend(fontsize=11, framealpha=0.95, shadow=True, markerscale=1.2)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Plot 2: Speedup relative to shortest path
    ax2 = axes[1]
    
    # Get shortest path baseline
    baseline_data = filtered[filtered['routing_method'] == 'shortest_path'].sort_values('load')
    
    for method in routing_methods:
        if method == 'shortest_path':
            continue
        
        method_data = filtered[filtered['routing_method'] == method].sort_values('load')
        
        # Merge with baseline on load
        merged = pd.merge(method_data, baseline_data[['load', 'throughput_gbps']], 
                         on='load', suffixes=('', '_baseline'))
        
        # Calculate speedup
        merged['speedup'] = merged['throughput_gbps'] / merged['throughput_gbps_baseline']
        
        # Get style for this method
        style = styles.get(method, styles['default'])
        
        # Format label for better readability
        if method.startswith('ugal_'):
            label = f"UGAL (valiant={method.split('_')[1]})"
        elif method == 'md_nexullance':
            label = "MD_Nexullance"
        elif method == 'nexullance':
            label = "Nexullance"
        else:
            label = method.replace('_', ' ').title()
        
        ax2.plot(merged['load'], merged['speedup'], 
                marker=style['marker'],
                linestyle=style['linestyle'],
                linewidth=style['linewidth'],
                markersize=style['markersize'],
                alpha=style['alpha'],
                color=style.get('color'),
                markeredgewidth=1.5,
                markeredgecolor='white',
                label=label)
    
    # Add baseline reference line
    ax2.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, label='Shortest Path Baseline')
    
    ax2.set_xlabel('Offered Load', fontsize=12)
    ax2.set_ylabel('Speedup vs Shortest Path', fontsize=12)
    ax2.set_ylim((0.0, 2.5))
    ax2.set_title(f'{topo_name} - {traffic_pattern.replace("_", " ").title()} Traffic\nSpeedup Comparison', 
                  fontsize=13, fontweight='bold')
    ax2.legend(fontsize=11, framealpha=0.95, shadow=True, markerscale=1.2)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Save figure
    output_file = output_dir / f"comparison_{topo_name}_{traffic_pattern}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_file}")
    
    plt.close()


def generate_summary_table(df, output_dir):
    """
    Generate summary statistics table.
    
    Args:
        df: DataFrame with results
        output_dir: Directory to save summary
    """
    summary_rows = []
    
    # Group by topology, traffic pattern, and routing method
    groups = df.groupby(['routing_method'])
    
    for method, group_df in groups:
        successful = group_df[group_df['throughput_gbps'].notna()]
        
        if len(successful) > 0:
            # Format method name
            if method[0].startswith('ugal_'):
                method_name = f"UGAL (valiant={method[0].split('_')[1]})"
            elif method[0] == 'md_nexullance':
                method_name = "MD_Nexullance"
            else:
                method_name = method[0].replace('_', ' ').title()
            
            summary_rows.append({
                'Routing Method': method_name,
                'Avg Throughput (Gbps)': successful['throughput_gbps'].mean(),
                'Max Throughput (Gbps)': successful['throughput_gbps'].max(),
                'Min Throughput (Gbps)': successful['throughput_gbps'].min(),
                'Std Dev (Gbps)': successful['throughput_gbps'].std(),
                'Successful Runs': len(successful),
                'Total Runs': len(group_df)
            })
    
    summary_df = pd.DataFrame(summary_rows)
    
    # Save to CSV
    summary_file = output_dir / "summary_statistics.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary saved to: {summary_file}")
    
    # Print to console
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(summary_df.to_string(index=False))
    print("="*80)
    
    return summary_df


def main():
    """Main entry point for analysis."""
    parser = argparse.ArgumentParser(
        description='Analyze and plot routing comparison results',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input-dir', type=str, default=None,
                        help='Directory containing result CSV files (default: Merlin_experiments/)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to save plots and analysis (default: Merlin_experiments/plots/)')
    parser.add_argument('--result-files', nargs='+', default=None,
                        help='Specific result CSV files to analyze')
    
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
    print("ROUTING COMPARISON ANALYSIS")
    print("="*80)
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print("="*80 + "\n")
    
    # Load results
    if args.result_files:
        result_files = args.result_files
    else:
        # Find all routing comparison result files
        result_files = list(input_dir.glob("routing_comparison_*.csv"))
    
    if not result_files:
        print("ERROR: No result files found!")
        print(f"Searched in: {input_dir}")
        return 1
    
    print(f"Found {len(result_files)} result file(s):")
    for f in result_files:
        print(f"  - {f.name}")
    print()
    
    # Load and merge all results
    df = load_and_merge_results(result_files)
    
    if df is None or len(df) == 0:
        print("ERROR: No data loaded!")
        return 1
    
    print(f"Loaded {len(df)} result rows")
    print(f"Routing methods: {', '.join(df['routing_method'].unique())}")
    print()
    
    # Generate summary statistics
    generate_summary_table(df, output_dir)
    
    # Create comparison plots for each topology and traffic pattern
    # Extract topology and traffic pattern from result files
    for result_file in result_files:
        # Parse filename: routing_comparison_{topo}_{traffic}_{timestamp}.csv
        parts = result_file.stem.split('_')
        if len(parts) >= 4:
            # Find the topology and traffic pattern
            # Format: routing_comparison_RRG_V36_D5_uniform_20260116_123456.csv
            # We need to extract topo name and traffic pattern
            file_df = pd.read_csv(result_file)
            
            # Try to infer from filename
            filename = result_file.stem
            if 'uniform' in filename:
                traffic = 'uniform'
            elif 'shift_half' in filename:
                traffic = 'shift_half'
            elif 'shift_1' in filename:
                traffic = 'shift_1'
            else:
                traffic = 'unknown'
            
            # Extract topology
            for topo in ['RRG', 'Slimfly', 'DDF']:
                if topo in filename:
                    topo_name = topo
                    break
            else:
                topo_name = 'unknown'
            
            if topo_name != 'unknown' and traffic != 'unknown':
                plot_comparison(file_df, topo_name, traffic, output_dir)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"Plots and summaries saved to: {output_dir}")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
