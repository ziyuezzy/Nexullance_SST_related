#!/usr/bin/env python3
"""
Plot EFM scaling experiment results.

Produces three plots per CSV file:
  1. Application simulation time vs network size (per routing method)
  2. Speedup vs network size (UGAL and Nexullance relative to shortest path)
  3. Wall-clock simulation runtime vs network size (log scale)

Combines all three into a single 2×2 figure as well.

Usage:
  # Plot a specific results CSV:
  python3 plot_scaling_results.py scaling_Slimfly_Allreduce_20260318_120000.csv

  # Plot all CSVs in this directory:
  python3 plot_scaling_results.py
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
import re

SCRIPT_DIR = Path(__file__).resolve().parent

# ── Styling constants ───────────────────────────────────────────────────────
MARKERS = {'shortest_path': 'o', 'ugal': 's', 'nexullance': '^'}
COLORS  = {'shortest_path': '#1f77b4', 'ugal': '#ff7f0e', 'nexullance': '#2ca02c'}
LABELS  = {'shortest_path': 'Shortest Path', 'ugal': 'UGAL', 'nexullance': 'Nexullance'}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_scaling_results(results_file: str):
    """Load a scaling CSV and detect routing methods from column names."""
    df = pd.read_csv(results_file)
    print(f"\nLoaded {len(df)} configurations from {results_file}")

    routing_methods = []
    for col in df.columns:
        if col.endswith('_sim_time_ms'):
            method = col.replace('_sim_time_ms', '')
            routing_methods.append(method)

    print(f"Routing methods: {', '.join(routing_methods)}")
    return df, routing_methods


def _extract_meta(results_path: Path, df: pd.DataFrame):
    """Try to extract topo_name and benchmark from the filename or metadata JSON."""
    stem = results_path.stem  # e.g. scaling_Slimfly_Allreduce_20260318_120000
    parts = stem.split('_')
    topo_name = parts[1] if len(parts) > 1 else 'Unknown'
    benchmark = parts[2] if len(parts) > 2 else ''

    # Attempt to load metadata JSON for richer info
    meta_pattern = f"scaling_{topo_name}_{benchmark}_*_metadata.json"
    meta_files = sorted(results_path.parent.glob(meta_pattern), reverse=True)
    metadata = {}
    if meta_files:
        import json
        with open(meta_files[0]) as f:
            metadata = json.load(f)
        topo_name = metadata.get('topo_name', topo_name)
        benchmark = metadata.get('benchmark', benchmark)

    return topo_name, benchmark, metadata


def filter_complete_configs(df: pd.DataFrame, routing_methods: list) -> pd.DataFrame:
    """Keep only network sizes that have complete data for all routing methods."""
    if 'V' not in df.columns:
        return df.copy()

    complete_vs = set()
    for v in sorted(df['V'].unique()):
        sub = df[df['V'] == v]
        ok = True
        for method in routing_methods:
            t_col = f'{method}_sim_time_ms'
            s_col = f'{method}_success'
            r_col = f'{method}_runtime'
            if any(c not in sub.columns for c in (t_col, s_col, r_col)):
                ok = False
                break
            for _, row in sub.iterrows():
                if pd.isna(row[t_col]) or pd.isna(row[r_col]) or row[s_col] is not True:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            complete_vs.add(v)

    return df[df['V'].isin(complete_vs)].copy()


# ---------------------------------------------------------------------------
# Individual plots
# ---------------------------------------------------------------------------

def plot_simtime_scaling(df: pd.DataFrame, routing_methods: list, topo_name: str,
                         benchmark: str, output_dir: Path):
    """Plot application simulation time vs network size."""
    fig, ax = plt.subplots(figsize=(12, 7))

    for method in routing_methods:
        t_col = f'{method}_sim_time_ms'
        s_col = f'{method}_success'
        if t_col in df.columns:
            mdf = df[df[s_col] == True].copy() if s_col in df.columns else df.copy()
            if len(mdf) > 0:
                ax.plot(mdf['V'], mdf[t_col],
                        marker=MARKERS.get(method, 'o'),
                        color=COLORS.get(method, 'gray'),
                        label=LABELS.get(method, method),
                        linewidth=2, markersize=8, alpha=0.8)

    ax.set_xlabel('Number of Routers (V)', fontsize=12)
    ax.set_ylabel('Application Simulation Time (ms)', fontsize=12)
    ax.set_title(f'{topo_name} – {benchmark}: Simulation Time vs Network Size',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = output_dir / f'scaling_simtime_{topo_name}_{benchmark}.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"✓ Saved sim-time plot: {out}")
    plt.close()


def plot_speedup_scaling(df: pd.DataFrame, routing_methods: list, topo_name: str,
                         benchmark: str, output_dir: Path):
    """Plot speedup (vs shortest path) vs network size."""
    fig, ax = plt.subplots(figsize=(12, 7))

    has_data = False
    for method in routing_methods:
        if method == 'shortest_path':
            continue
        sp_col = f'{method}_speedup'
        if sp_col in df.columns:
            mdf = df[df[sp_col].notna()].copy()
            if len(mdf) > 0:
                has_data = True
                ax.plot(mdf['V'], mdf[sp_col],
                        marker=MARKERS.get(method, 'o'),
                        color=COLORS.get(method, 'gray'),
                        label=LABELS.get(method, method),
                        linewidth=2, markersize=8, alpha=0.8)

    if has_data:
        ax.axhline(y=1.0, color='#1f77b4', linestyle='--', linewidth=1.5,
                   label='Shortest Path (baseline)', alpha=0.7)
        ax.set_xlabel('Number of Routers (V)', fontsize=12)
        ax.set_ylabel('Speedup vs Shortest Path', fontsize=12)
        ax.set_title(f'{topo_name} – {benchmark}: Application Speedup vs Network Size',
                     fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        out = output_dir / f'scaling_speedup_{topo_name}_{benchmark}.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        print(f"✓ Saved speedup plot: {out}")
    else:
        print("⚠ No speedup data available to plot")
    plt.close()


def plot_runtime_scaling(df: pd.DataFrame, routing_methods: list, topo_name: str,
                         benchmark: str, output_dir: Path):
    """Plot wall-clock simulation runtime vs network size (log scale)."""
    fig, ax = plt.subplots(figsize=(12, 7))

    for method in routing_methods:
        r_col = f'{method}_runtime'
        if r_col in df.columns:
            mdf = df[df[r_col].notna()].copy()
            if len(mdf) > 0:
                ax.plot(mdf['V'], mdf[r_col],
                        marker=MARKERS.get(method, 'o'),
                        color=COLORS.get(method, 'gray'),
                        label=LABELS.get(method, method),
                        linewidth=2, markersize=8, alpha=0.8)

    ax.set_xlabel('Number of Routers (V)', fontsize=12)
    ax.set_ylabel('Wall-Clock Runtime (seconds)', fontsize=12)
    ax.set_title(f'{topo_name} – {benchmark}: Simulation Runtime vs Network Size',
                 fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = output_dir / f'scaling_runtime_{topo_name}_{benchmark}.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"✓ Saved runtime plot: {out}")
    plt.close()


# ---------------------------------------------------------------------------
# Combined 2×2 plot
# ---------------------------------------------------------------------------

def plot_combined(df: pd.DataFrame, routing_methods: list, topo_name: str,
                  benchmark: str, output_dir: Path):
    """2×2 figure: sim time, speedup, runtime, runtime-per-endpoint."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    (ax1, ax2), (ax3, ax4) = axes

    # ── (a) Simulation time ──
    for method in routing_methods:
        t_col = f'{method}_sim_time_ms'
        s_col = f'{method}_success'
        if t_col in df.columns:
            mdf = df[df[s_col] == True].copy() if s_col in df.columns else df
            if len(mdf):
                ax1.plot(mdf['V'], mdf[t_col],
                         marker=MARKERS.get(method, 'o'), color=COLORS.get(method, 'gray'),
                         label=LABELS.get(method, method), linewidth=2, markersize=7)
    ax1.set_xlabel('Number of Routers (V)', fontsize=11)
    ax1.set_ylabel('App Simulation Time (ms)', fontsize=11)
    ax1.set_title('(a) Application Simulation Time', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── (b) Speedup ──
    has_speedup = False
    for method in routing_methods:
        if method == 'shortest_path':
            continue
        sp_col = f'{method}_speedup'
        if sp_col in df.columns:
            mdf = df[df[sp_col].notna()].copy()
            if len(mdf):
                has_speedup = True
                ax2.plot(mdf['V'], mdf[sp_col],
                         marker=MARKERS.get(method, 'o'), color=COLORS.get(method, 'gray'),
                         label=LABELS.get(method, method), linewidth=2, markersize=7)
    if has_speedup:
        ax2.axhline(y=1.0, color='#1f77b4', linestyle='--', linewidth=1.5,
                    label='Shortest Path (baseline)', alpha=0.7)
    ax2.set_xlabel('Number of Routers (V)', fontsize=11)
    ax2.set_ylabel('Speedup vs Shortest Path', fontsize=11)
    ax2.set_title('(b) Application Speedup', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ── (c) Wall-clock runtime ──
    for method in routing_methods:
        r_col = f'{method}_runtime'
        if r_col in df.columns:
            mdf = df[df[r_col].notna()].copy()
            if len(mdf):
                ax3.plot(mdf['V'], mdf[r_col],
                         marker=MARKERS.get(method, 'o'), color=COLORS.get(method, 'gray'),
                         label=LABELS.get(method, method), linewidth=2, markersize=7)
    ax3.set_xlabel('Number of Routers (V)', fontsize=11)
    ax3.set_ylabel('Wall-Clock Runtime (seconds)', fontsize=11)
    ax3.set_title('(c) Simulation Runtime', fontsize=12, fontweight='bold')
    ax3.set_yscale('log')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)

    # ── (d) Runtime per endpoint ──
    if 'num_endpoints' in df.columns:
        for method in routing_methods:
            r_col = f'{method}_runtime'
            if r_col in df.columns:
                mdf = df[df[r_col].notna()].copy()
                if len(mdf):
                    per_ep = mdf[r_col] / mdf['num_endpoints']
                    ax4.plot(mdf['V'], per_ep,
                             marker=MARKERS.get(method, 'o'), color=COLORS.get(method, 'gray'),
                             label=LABELS.get(method, method), linewidth=2, markersize=7)
    ax4.set_xlabel('Number of Routers (V)', fontsize=11)
    ax4.set_ylabel('Runtime per Endpoint (s)', fontsize=11)
    ax4.set_title('(d) Normalised Runtime per Endpoint', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)

    plt.suptitle(f'{topo_name} – {benchmark}: EFM Scaling Analysis',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    out = output_dir / f'scaling_combined_{topo_name}_{benchmark}.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"✓ Saved combined plot: {out}")
    plt.close()


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def process_results_file(results_path: Path, output_dir: Path):
    """Load one CSV and produce all plots."""
    print(f"\n{'='*80}")
    print(f"Processing: {results_path.name}")
    print('='*80)

    df, routing_methods = load_scaling_results(str(results_path))
    if df.empty:
        print("⚠ Empty DataFrame, skipping.")
        return

    topo_name, benchmark, _ = _extract_meta(results_path, df)

    output_dir.mkdir(parents=True, exist_ok=True)

    plot_simtime_scaling(df, routing_methods, topo_name, benchmark, output_dir)
    plot_speedup_scaling(df, routing_methods, topo_name, benchmark, output_dir)
    plot_runtime_scaling(df, routing_methods, topo_name, benchmark, output_dir)
    plot_combined(df, routing_methods, topo_name, benchmark, output_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Plot EFM scaling experiment results'
    )
    parser.add_argument('results_files', nargs='*', type=str,
                        help='Path(s) to scaling results CSV file(s). '
                             'Omit to process all CSVs in this directory.')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory for plots (default: same as results file)')

    args = parser.parse_args()

    if args.results_files:
        input_paths = [Path(p) for p in args.results_files]
    else:
        input_paths = sorted(SCRIPT_DIR.glob('scaling_*.csv'))
        # Exclude intermediate files
        input_paths = [p for p in input_paths if 'intermediate' not in p.name]

    if not input_paths:
        print(f"ERROR: No scaling CSV files found in {SCRIPT_DIR}")
        return 1

    exit_code = 0
    for results_path in input_paths:
        if not results_path.exists():
            print(f"WARNING: File not found, skipping: {results_path}")
            exit_code = 1
            continue

        out_dir = Path(args.output_dir) if args.output_dir else results_path.parent
        try:
            process_results_file(results_path, out_dir)
        except Exception as e:
            print(f"ERROR processing {results_path.name}: {e}")
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
