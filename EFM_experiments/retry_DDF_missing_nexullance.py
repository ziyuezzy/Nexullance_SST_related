#!/usr/bin/env python3
"""
Retry script for missing DDF nexullance MD data points.

Both Alltoall (bytes=64) and FFT3D (nx=256) nexullance MD sweeps failed entirely
for DDF_V36_D5. This script retries only those missing data points and appends
results to the existing CSV files.

Existing baseline times (from already-completed runs):
  Alltoall bytes=64: 8.52441 ms
  FFT3D    nx=256:   12.3621 ms
"""

import sys
from pathlib import Path
import csv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sst_ultility.ultility import run_ember_experiment_with_nexullance

# ── Configuration ──────────────────────────────────────────────────────────────
TOPO_NAME   = "DDF"
V           = 36
D           = 5
CORES_PER_EP = 4
LINK_BW     = 16
NUM_THREADS = 8
NETWORK_INFO = f"{TOPO_NAME}_V{V}_D{D}"

SAMPLE_COUNTS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]

OUTPUT_DIR = SCRIPT_DIR / "DDF_V36_D5_CPE4_sample_sweep"

# Existing CSV files to append to
ALLTOALL_CSV = OUTPUT_DIR / "DDF_V36_D5_Alltoall_bytes_nexullance_MD_sample_sweep_20260303_143451.csv"
FFT3D_CSV    = OUTPUT_DIR / "DDF_V36_D5_FFT3D_nx_nexullance_MD_sample_sweep_20260303_152936.csv"

# Baseline times extracted from already-completed baseline CSVs
ALLTOALL_BASELINE_MS = 8.52441
FFT3D_BASELINE_MS    = 12.3621

# ── Helpers ────────────────────────────────────────────────────────────────────

def write_csv_row(filename: Path, row: list):
    with open(filename, mode='a', newline='') as f:
        csv.writer(f).writerow(row)
        f.flush()


def run_nexullance_sweep(benchmark_name: str, bench_args: str,
                         param_name: str, param_value,
                         baseline_ms: float, csv_file: Path):
    """Run nexullance MD sample sweep and append results to an existing CSV."""

    print(f"\n{'='*70}")
    print(f"Nexullance MD sweep — {benchmark_name} ({param_name}={param_value})")
    print(f"Baseline: {baseline_ms} ms   →  appending to {csv_file.name}")
    print(f"{'='*70}")

    for num_samples in SAMPLE_COUNTS:
        print(f"  [{benchmark_name}] num_samples={num_samples} ...", end=" ", flush=True)
        try:
            results = run_ember_experiment_with_nexullance(
                topo_name=TOPO_NAME, V=V, D=D,
                benchmark=benchmark_name, bench_args=bench_args,
                cores_per_ep=CORES_PER_EP, link_bw=LINK_BW,
                num_threads=NUM_THREADS,
                traffic_collection_rate="1us",
                nexullance_method="MD",
                num_demand_samples=num_samples
            )

            if results:
                opt_ms      = results['optimized_sim_time_ms']
                speedup     = baseline_ms / opt_ms
                improvement = (baseline_ms - opt_ms) / baseline_ms * 100
                write_csv_row(csv_file,
                              [NETWORK_INFO, param_value, num_samples,
                               baseline_ms, opt_ms, speedup, improvement])
                print(f"✓  {opt_ms:.4f} ms  speedup={speedup:.4f}x")
            else:
                print("✗  run_ember_experiment_with_nexullance returned None/empty")

        except ValueError as e:
            print(f"⚠  ValueError: {e}")
            print(f"   Stopping sweep at num_samples={num_samples} (insufficient data)")
            break
        except Exception as e:
            print(f"✗  Unexpected error: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*70)
    print("DDF MISSING NEXULLANCE MD DATA — RETRY SCRIPT")
    print(f"Topology: {TOPO_NAME}  V={V}  D={D}  CPE={CORES_PER_EP}")
    print(f"Sample counts: {SAMPLE_COUNTS}")
    print("="*70)

    # 1. Alltoall (bytes=64)
    run_nexullance_sweep(
        benchmark_name="Alltoall",
        bench_args=" bytes=64",
        param_name="bytes",
        param_value=64,
        baseline_ms=ALLTOALL_BASELINE_MS,
        csv_file=ALLTOALL_CSV,
    )

    # 2. FFT3D (nx=ny=nz=256)
    run_nexullance_sweep(
        benchmark_name="FFT3D",
        bench_args=" nx=256 ny=256 nz=256 npRow=12",
        param_name="nx",
        param_value=256,
        baseline_ms=FFT3D_BASELINE_MS,
        csv_file=FFT3D_CSV,
    )

    print("\n" + "="*70)
    print("RETRY COMPLETE")
    print(f"Results appended to existing CSVs in {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    sys.exit(main())
