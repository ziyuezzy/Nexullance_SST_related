#!/usr/bin/env python3
"""
Simple plotting script for intermediate scaling results.
Plots network throughput and simulation runtime vs network size.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import argparse

SCRIPT_DIR = Path(__file__).resolve().parent


def extract_topology_name(filename: str) -> str:
    """Extract topology name from CSV filename."""
    filename_lower = filename.lower()
    for topo in ['slimfly', 'dragonfly', 'ddf', 'polarfly', 'fattree', 'torus']:
        if topo in filename_lower:
            return topo.capitalize() if topo != 'ddf' else 'DDF'
    return "Unknown"


def load_results(csv_file: Path):
    """Load scaling results from CSV file."""
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} configurations from {csv_file.name}")
    print(f"Network sizes (V): {sorted(df['V'].unique())}")
    return df


def plot_throughput_and_runtime(df: pd.DataFrame, output_prefix: str, topo_name: str):
    """Create side-by-side plots of throughput and runtime vs network size."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    
    # Styling configurations
    markers = {'shortest_path': 'o', 'ugal': 's', 'nexullance': '^'}
    colors = {'shortest_path': '#1f77b4', 'ugal': '#ff7f0e', 'nexullance': '#2ca02c'}
    labels = {'shortest_path': 'Shortest Path', 'ugal': 'UGAL', 'nexullance': 'Nexullance'}
    
    routing_methods = ['shortest_path', 'ugal', 'nexullance']
    
    # Plot 1: Network Throughput
    for method in routing_methods:
        throughput_col = f'{method}_throughput'
        success_col = f'{method}_success'
        
        if throughput_col in df.columns:
            # Filter successful experiments
            method_df = df[df[success_col] == True].copy()
            
            if len(method_df) > 0:
                ax1.plot(method_df['V'], method_df[throughput_col],
                        marker=markers[method],
                        color=colors[method],
                        label=labels[method],
                        linewidth=2.5, 
                        markersize=10, 
                        alpha=0.8,
                        markeredgewidth=1.5,
                        markeredgecolor='white')
    
    ax1.set_xlabel('Number of Routers (V)', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Network Throughput (Gbps)', fontsize=16, fontweight='bold')
    ax1.set_title(f'{topo_name} Network Throughput vs Network Size', fontsize=18, fontweight='bold', pad=15)
    ax1.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.tick_params(labelsize=14)
    
    # Plot 2: Simulation Runtime
    for method in routing_methods:
        runtime_col = f'{method}_runtime'
        success_col = f'{method}_success'
        
        if runtime_col in df.columns:
            # Filter successful experiments
            method_df = df[df[success_col] == True].copy()
            
            if len(method_df) > 0:
                ax2.plot(method_df['V'], method_df[runtime_col],
                        marker=markers[method],
                        color=colors[method],
                        label=labels[method],
                        linewidth=2.5, 
                        markersize=10, 
                        alpha=0.8,
                        markeredgewidth=1.5,
                        markeredgecolor='white')
    
    ax2.set_xlabel('Number of Routers (V)', fontsize=16, fontweight='bold')
    ax2.set_ylabel('Simulation Runtime (seconds)', fontsize=16, fontweight='bold')
    ax2.set_title(f'{topo_name} Simulation Runtime vs Network Size', fontsize=18, fontweight='bold', pad=15)
    ax2.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_yscale('log')  # Log scale for runtime
    ax2.tick_params(labelsize=14)
    
    plt.tight_layout()
    
    # Save the figure
    output_file = Path(output_prefix + '.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot: {output_file}")
    plt.close()


def plot_separate_figures(df: pd.DataFrame, output_prefix: str, topo_name: str):
    """Create separate figures for throughput and runtime."""
    
    markers = {'shortest_path': 'o', 'ugal': 's', 'nexullance': '^'}
    colors = {'shortest_path': '#1f77b4', 'ugal': '#ff7f0e', 'nexullance': '#2ca02c'}
    labels = {'shortest_path': 'Shortest Path', 'ugal': 'UGAL', 'nexullance': 'Nexullance'}
    routing_methods = ['shortest_path', 'ugal', 'nexullance']
    
    # Figure 1: Throughput
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    
    for method in routing_methods:
        throughput_col = f'{method}_throughput'
        success_col = f'{method}_success'
        
        if throughput_col in df.columns:
            method_df = df[df[success_col] == True].copy()
            if len(method_df) > 0:
                ax1.plot(method_df['V'], method_df[throughput_col],
                        marker=markers[method],
                        color=colors[method],
                        label=labels[method],
                        linewidth=2.5, 
                        markersize=10, 
                        alpha=0.8,
                        markeredgewidth=1.5,
                        markeredgecolor='white')
    
    ax1.set_xlabel('Number of Routers (V)', fontsize=18, fontweight='bold')
    ax1.set_ylabel('Network Throughput (Gbps)', fontsize=18, fontweight='bold')
    ax1.set_title(f'{topo_name} Network Throughput vs Network Size', fontsize=20, fontweight='bold', pad=20)
    ax1.legend(fontsize=16, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.tick_params(labelsize=15)
    
    plt.tight_layout()
    output_file1 = Path(output_prefix + '_throughput.png')
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"✓ Saved throughput plot: {output_file1}")
    plt.close()
    
    # Figure 2: Runtime
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    
    for method in routing_methods:
        runtime_col = f'{method}_runtime'
        success_col = f'{method}_success'
        
        if runtime_col in df.columns:
            method_df = df[df[success_col] == True].copy()
            if len(method_df) > 0:
                ax2.plot(method_df['V'], method_df[runtime_col],
                        marker=markers[method],
                        color=colors[method],
                        label=labels[method],
                        linewidth=2.5, 
                        markersize=10, 
                        alpha=0.8,
                        markeredgewidth=1.5,
                        markeredgecolor='white')
    
    ax2.set_xlabel('Number of Routers (V)', fontsize=18, fontweight='bold')
    ax2.set_ylabel('Simulation Runtime (seconds)', fontsize=18, fontweight='bold')
    ax2.set_title(f'{topo_name} Simulation Runtime vs Network Size', fontsize=20, fontweight='bold', pad=20)
    ax2.legend(fontsize=16, loc='upper left', framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_yscale('log')
    ax2.tick_params(labelsize=15)
    
    plt.tight_layout()
    output_file2 = Path(output_prefix + '_runtime.png')
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✓ Saved runtime plot: {output_file2}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plot intermediate scaling results: throughput and runtime'
    )
    
    parser.add_argument('csv_file', nargs='?', type=str,
                        help='Path to CSV file (default: newest scaling_*.csv in current directory)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file prefix (default: same as input file)')
    parser.add_argument('--separate', action='store_true',
                        help='Generate separate plots instead of combined figure')
    
    args = parser.parse_args()
    
    # Determine input file
    if args.csv_file:
        csv_path = Path(args.csv_file)
    else:
        # Find the most recent CSV file
        csv_files = sorted(SCRIPT_DIR.glob('scaling_*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csv_files:
            print("ERROR: No CSV files found in current directory")
            return 1
        csv_path = csv_files[0]
        print(f"Auto-selected most recent CSV: {csv_path.name}")
    
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return 1
    
    # Load data
    df = load_results(csv_path)
    
    # Extract topology name
    topo_name = extract_topology_name(csv_path.name)
    print(f"Detected topology: {topo_name}")
    
    # Determine output prefix
    if args.output:
        output_prefix = args.output
    else:
        output_prefix = str(csv_path.parent / f"plot_{csv_path.stem}")
    
    print(f"\nGenerating plots...")
    
    # Generate plots
    if args.separate:
        plot_separate_figures(df, output_prefix, topo_name)
    else:
        plot_throughput_and_runtime(df, output_prefix, topo_name)
    
    print("\n✓ Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
