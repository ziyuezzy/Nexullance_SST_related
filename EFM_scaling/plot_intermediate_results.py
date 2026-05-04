#!/usr/bin/env python3
"""
Quick plotting script for intermediate EFM scaling results.
Produces side-by-side plots of application simulation time and wall-clock
runtime vs network size from any intermediate CSV produced during a run.

Usage:
  python3 plot_intermediate_results.py scaling_Slimfly_Allreduce_intermediate_20260318_120000.csv

  # Plot all intermediate CSVs in this directory:
  python3 plot_intermediate_results.py
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import argparse

SCRIPT_DIR = Path(__file__).resolve().parent

MARKERS = {'shortest_path': 'o', 'ugal': 's', 'nexullance': '^'}
COLORS  = {'shortest_path': '#1f77b4', 'ugal': '#ff7f0e', 'nexullance': '#2ca02c'}
LABELS  = {'shortest_path': 'Shortest Path', 'ugal': 'UGAL', 'nexullance': 'Nexullance'}


def extract_topology_name(filename: str) -> str:
    """Extract topology name from intermediate CSV filename."""
    filename_lower = filename.lower()
    for topo in ['slimfly', 'ddf', 'polarfly']:
        if topo in filename_lower:
            return 'DDF' if topo == 'ddf' else topo.capitalize()
    return 'Unknown'


def extract_benchmark_name(filename: str) -> str:
    """Extract benchmark name from filename."""
    for bench in ['allreduce', 'alltoall', 'fft3d']:
        if bench in filename.lower():
            return bench.capitalize() if bench != 'fft3d' else 'FFT3D'
    return ''


def load_results(csv_file: Path):
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} configurations from {csv_file.name}")
    print(f"Network sizes (V): {sorted(df['V'].unique())}")
    return df


def plot_simtime_and_runtime(df: pd.DataFrame, output_prefix: str,
                              topo_name: str, benchmark: str):
    """Create side-by-side plots of simulation time and wall-clock runtime."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    routing_methods = ['shortest_path', 'ugal', 'nexullance']

    # ── Left: Application sim time ──
    for method in routing_methods:
        t_col = f'{method}_sim_time_ms'
        s_col = f'{method}_success'
        if t_col in df.columns:
            mdf = df[df[s_col] == True].copy() if s_col in df.columns else df
            if len(mdf):
                ax1.plot(mdf['V'], mdf[t_col],
                         marker=MARKERS[method], color=COLORS[method],
                         label=LABELS[method],
                         linewidth=2.5, markersize=10, alpha=0.85,
                         markeredgewidth=1.5, markeredgecolor='white')

    ax1.set_xlabel('Number of Routers (V)', fontsize=16, fontweight='bold')
    ax1.set_ylabel('App Simulation Time (ms)', fontsize=16, fontweight='bold')
    title1 = f'{topo_name} – {benchmark}: Sim Time vs Network Size' if benchmark else \
             f'{topo_name} App Simulation Time vs Network Size'
    ax1.set_title(title1, fontsize=18, fontweight='bold', pad=15)
    ax1.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.tick_params(labelsize=14)

    # ── Right: Wall-clock runtime (log scale) ──
    for method in routing_methods:
        r_col = f'{method}_runtime'
        s_col = f'{method}_success'
        if r_col in df.columns:
            mdf = df[df[s_col] == True].copy() if s_col in df.columns else df
            if len(mdf):
                ax2.plot(mdf['V'], mdf[r_col],
                         marker=MARKERS[method], color=COLORS[method],
                         label=LABELS[method],
                         linewidth=2.5, markersize=10, alpha=0.85,
                         markeredgewidth=1.5, markeredgecolor='white')

    ax2.set_xlabel('Number of Routers (V)', fontsize=16, fontweight='bold')
    ax2.set_ylabel('Wall-Clock Runtime (seconds)', fontsize=16, fontweight='bold')
    title2 = f'{topo_name} – {benchmark}: Runtime vs Network Size' if benchmark else \
             f'{topo_name} Simulation Runtime vs Network Size'
    ax2.set_title(title2, fontsize=18, fontweight='bold', pad=15)
    ax2.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_yscale('log')
    ax2.tick_params(labelsize=14)

    plt.tight_layout()
    output_file = f"{output_prefix}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Quick plot of intermediate EFM scaling results'
    )
    parser.add_argument('csv_files', nargs='*', type=str,
                        help='Intermediate CSV file(s) to plot. '
                             'Omit to process all intermediates in this directory.')
    args = parser.parse_args()

    if args.csv_files:
        input_paths = [Path(p) for p in args.csv_files]
    else:
        input_paths = sorted(SCRIPT_DIR.glob('scaling_*_intermediate_*.csv'))

    if not input_paths:
        print(f"No intermediate CSV files found in {SCRIPT_DIR}")
        return 1

    for csv_path in input_paths:
        if not csv_path.exists():
            print(f"WARNING: File not found, skipping: {csv_path}")
            continue

        topo_name = extract_topology_name(csv_path.name)
        benchmark = extract_benchmark_name(csv_path.name)
        output_prefix = str(csv_path.parent / csv_path.stem)

        df = load_results(csv_path)
        plot_simtime_and_runtime(df, output_prefix, topo_name, benchmark)

    return 0


if __name__ == "__main__":
    sys.exit(main())
