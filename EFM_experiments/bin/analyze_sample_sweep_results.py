#!/usr/bin/env python3
"""
Analyze and plot results from sample sweep experiments.
Compares performance of shortest_path, ugal, nexullance_SD, and nexullance_MD
with varying number of samples for MD optimization.
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


def load_results(result_dir: Path):
    """Load all result CSV files from a directory."""
    results = {}
    
    # Find all CSV files
    csv_files = list(result_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        # Determine routing method and benchmark from filename
        filename = csv_file.stem
        
        if "shortest_path" in filename:
            method = "shortest_path"
        elif "ugal" in filename:
            method = "ugal"
        elif "nexullance_SD" in filename:
            method = "nexullance_SD"
        elif "nexullance_MD" in filename:
            method = "nexullance_MD"
        else:
            continue
        
        # Determine benchmark
        if "Allreduce" in filename:
            benchmark = "Allreduce"
        elif "Alltoall" in filename:
            benchmark = "Alltoall"
        elif "FFT3D" in filename:
            benchmark = "FFT3D"
        else:
            continue
        
        # Load data
        try:
            df = pd.read_csv(csv_file)
            key = f"{benchmark}_{method}"
            results[key] = df
            print(f"Loaded: {key} ({len(df)} rows)")
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    return results


def plot_sample_sweep_comparison(results: dict, benchmark: str, output_dir: Path):
    """
    Create comparison plots showing how MD performance varies with number of samples.
    
    Args:
        results: Dictionary of dataframes with results
        benchmark: Benchmark name (Allreduce, Alltoall, FFT3D)
        output_dir: Directory to save plots
    """
    # Get data
    shortest_path_df = results.get(f"{benchmark}_shortest_path")
    ugal_df = results.get(f"{benchmark}_ugal")
    sd_df = results.get(f"{benchmark}_nexullance_SD")
    md_df = results.get(f"{benchmark}_nexullance_MD")
    
    if not all([shortest_path_df is not None, md_df is not None]):
        print(f"Missing data for {benchmark}")
        return
    
    # Determine parameter name
    if benchmark == "Allreduce":
        param_col = "count"
        param_label = "Message Count"
    elif benchmark == "Alltoall":
        param_col = "bytes"
        param_label = "Message Size (bytes)"
    else:  # FFT3D
        param_col = "nx"
        param_label = "Grid Size (nx=ny=nz)"
    
    # Get unique problem sizes
    problem_sizes = shortest_path_df[param_col].unique()
    
    # Create figure with subplots for each problem size
    n_sizes = len(problem_sizes)
    fig, axes = plt.subplots(1, n_sizes, figsize=(6*n_sizes, 5))
    if n_sizes == 1:
        axes = [axes]
    
    for idx, size in enumerate(problem_sizes):
        ax = axes[idx]
        
        # Get baseline time
        baseline_time = shortest_path_df[shortest_path_df[param_col] == size]['sim_time_ms'].values[0]
        
        # Plot horizontal lines for non-MD methods
        ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=2, label='Shortest-Path (baseline)', alpha=0.7)
        
        if ugal_df is not None:
            ugal_speedup = ugal_df[ugal_df[param_col] == size]['speedup'].values
            if len(ugal_speedup) > 0:
                ax.axhline(y=ugal_speedup[0], color='orange', linestyle='--', linewidth=2, label='UGAL', alpha=0.7)
        
        if sd_df is not None:
            sd_speedup = sd_df[sd_df[param_col] == size]['speedup'].values
            if len(sd_speedup) > 0:
                ax.axhline(y=sd_speedup[0], color='green', linestyle='--', linewidth=2, label='Nexullance SD', alpha=0.7)
        
        # Plot MD speedup vs. number of samples
        md_data = md_df[md_df[param_col] == size]
        if len(md_data) > 0:
            ax.plot(md_data['num_samples'], md_data['speedup'], 
                   marker='o', linewidth=2, markersize=8, color='red', label='Nexullance MD')
            ax.fill_between(md_data['num_samples'], 1.0, md_data['speedup'], alpha=0.2, color='red')
        
        ax.set_xlabel('Number of Demand Samples', fontsize=11)
        ax.set_ylabel('Speedup vs. Baseline', fontsize=11)
        ax.set_title(f'{param_label}={size}', fontsize=12, fontweight='bold')
        ax.set_xscale('log', base=2)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        
        # Set x-axis ticks
        ax.set_xticks([1, 2, 4, 8, 16, 32, 64, 128])
        ax.set_xticklabels(['1', '2', '4', '8', '16', '32', '64', '128'])
    
    fig.suptitle(f'{benchmark} - Sample Sweep Analysis', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    # Save plot
    output_file = output_dir / f"{benchmark}_sample_sweep_speedup.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def plot_optimal_samples_comparison(results: dict, output_dir: Path):
    """
    Create a comparison plot showing optimal number of samples for each benchmark.
    """
    benchmarks = ["Allreduce", "Alltoall", "FFT3D"]
    param_cols = {"Allreduce": "count", "Alltoall": "bytes", "FFT3D": "nx"}
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, benchmark in enumerate(benchmarks):
        ax = axes[idx]
        md_df = results.get(f"{benchmark}_nexullance_MD")
        
        if md_df is None:
            continue
        
        param_col = param_cols[benchmark]
        problem_sizes = md_df[param_col].unique()
        
        # For each problem size, find optimal number of samples
        optimal_samples = []
        optimal_speedups = []
        
        for size in problem_sizes:
            size_data = md_df[md_df[param_col] == size]
            max_speedup_idx = size_data['speedup'].idxmax()
            optimal_samples.append(size_data.loc[max_speedup_idx, 'num_samples'])
            optimal_speedups.append(size_data.loc[max_speedup_idx, 'speedup'])
        
        # Plot
        ax.scatter(problem_sizes, optimal_samples, s=200, c=optimal_speedups, 
                  cmap='viridis', edgecolors='black', linewidth=1.5)
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap='viridis', 
                                   norm=plt.Normalize(vmin=min(optimal_speedups), 
                                                     vmax=max(optimal_speedups)))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label('Best Speedup', fontsize=10)
        
        ax.set_xlabel('Problem Size', fontsize=11)
        ax.set_ylabel('Optimal Sample Count', fontsize=11)
        ax.set_title(f'{benchmark}', fontsize=12, fontweight='bold')
        ax.set_yscale('log', base=2)
        ax.grid(True, alpha=0.3)
        ax.set_yticks([1, 2, 4, 8, 16, 32, 64, 128])
        ax.set_yticklabels(['1', '2', '4', '8', '16', '32', '64', '128'])
    
    fig.suptitle('Optimal Sample Count for Multi-Demand Nexullance', 
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    output_file = output_dir / "optimal_samples_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_summary_table(results: dict, output_dir: Path):
    """Create a summary table comparing all methods."""
    benchmarks = ["Allreduce", "Alltoall", "FFT3D"]
    param_cols = {"Allreduce": "count", "Alltoall": "bytes", "FFT3D": "nx"}
    
    summary_rows = []
    
    for benchmark in benchmarks:
        param_col = param_cols[benchmark]
        
        # Get data
        shortest_path_df = results.get(f"{benchmark}_shortest_path")
        ugal_df = results.get(f"{benchmark}_ugal")
        sd_df = results.get(f"{benchmark}_nexullance_SD")
        md_df = results.get(f"{benchmark}_nexullance_MD")
        
        if shortest_path_df is None:
            continue
        
        problem_sizes = shortest_path_df[param_col].unique()
        
        for size in problem_sizes:
            row = {
                'Benchmark': benchmark,
                'Problem Size': size,
                'Shortest-Path Time (ms)': None,
                'UGAL Speedup': None,
                'SD Speedup': None,
                'MD Best Speedup': None,
                'MD Optimal Samples': None
            }
            
            # Shortest-path baseline
            baseline_time = shortest_path_df[shortest_path_df[param_col] == size]['sim_time_ms'].values[0]
            row['Shortest-Path Time (ms)'] = f"{baseline_time:.2f}"
            
            # UGAL
            if ugal_df is not None:
                ugal_speedup = ugal_df[ugal_df[param_col] == size]['speedup'].values
                if len(ugal_speedup) > 0:
                    row['UGAL Speedup'] = f"{ugal_speedup[0]:.4f}"
            
            # SD
            if sd_df is not None:
                sd_speedup = sd_df[sd_df[param_col] == size]['speedup'].values
                if len(sd_speedup) > 0:
                    row['SD Speedup'] = f"{sd_speedup[0]:.4f}"
            
            # MD - find best
            if md_df is not None:
                size_data = md_df[md_df[param_col] == size]
                if len(size_data) > 0:
                    max_idx = size_data['speedup'].idxmax()
                    row['MD Best Speedup'] = f"{size_data.loc[max_idx, 'speedup']:.4f}"
                    row['MD Optimal Samples'] = int(size_data.loc[max_idx, 'num_samples'])
            
            summary_rows.append(row)
    
    # Create DataFrame
    summary_df = pd.DataFrame(summary_rows)
    
    # Save to CSV
    output_file = output_dir / "summary_comparison.csv"
    summary_df.to_csv(output_file, index=False)
    print(f"\nSummary table saved to: {output_file}")
    
    # Print to console
    print("\nSummary Comparison:")
    print("="*100)
    print(summary_df.to_string(index=False))
    print("="*100)
    
    return summary_df


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="Analyze sample sweep experiment results")
    parser.add_argument("result_dir", nargs='?', 
                       help="Directory containing result CSV files")
    args = parser.parse_args()
    
    # Find result directory
    if args.result_dir:
        result_dir = Path(args.result_dir)
    else:
        # Find most recent sample_sweep directory
        sweep_dirs = list(SCRIPT_DIR.glob("*_sample_sweep"))
        if not sweep_dirs:
            print("ERROR: No sample_sweep result directories found")
            print(f"Searched in: {SCRIPT_DIR}")
            return 1
        
        result_dir = max(sweep_dirs, key=lambda p: p.stat().st_mtime)
        print(f"Using most recent result directory: {result_dir.name}")
    
    if not result_dir.exists():
        print(f"ERROR: Directory not found: {result_dir}")
        return 1
    
    print(f"\nAnalyzing results from: {result_dir}")
    print("="*80)
    
    # Load results
    results = load_results(result_dir)
    
    if not results:
        print("ERROR: No result files found")
        return 1
    
    # Create plots directory
    plots_dir = result_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    print(f"\nCreating plots...")
    print("="*80)
    
    # Create sample sweep plots for each benchmark
    for benchmark in ["Allreduce", "Alltoall", "FFT3D"]:
        if f"{benchmark}_nexullance_MD" in results:
            plot_sample_sweep_comparison(results, benchmark, plots_dir)
    
    # Create optimal samples comparison
    plot_optimal_samples_comparison(results, plots_dir)
    
    # Create summary table
    create_summary_table(results, result_dir)
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE!")
    print(f"{'='*80}")
    print(f"Results saved to: {result_dir}")
    print(f"Plots saved to: {plots_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
