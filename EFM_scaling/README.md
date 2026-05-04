# EFM Scaling Experiments

This directory contains scripts for running EFM (Ember + Firefly + Merlin) scaling
experiments that measure how **application performance** and **simulation runtime**
scale with network size.

Metrics recorded for each network size (V):
1. **Application simulation time (ms)** — how long the MPI benchmark takes inside the simulated network
2. **Speedup** — `baseline_sim_time / method_sim_time` (higher = faster application)
3. **Wall-clock runtime (s)** — how long the SST simulation itself takes to run

## Files

| File | Purpose |
|---|---|
| `run_scaling_experiments.py` | Main script: sweep network sizes and collect results |
| `plot_scaling_results.py` | Plot final results (sim time, speedup, runtime, combined) |
| `plot_intermediate_results.py` | Quick plot of in-progress intermediate CSV files |
| `run.sh` | Convenience shell script to run all topology/benchmark combinations |
| `README.md` | This file |

## Usage

### Running Scaling Experiments

```bash
# Sweep Slimfly network sizes with Allreduce (default problem size 256)
python3 run_scaling_experiments.py --topo-name Slimfly --benchmark Allreduce

# DDF with Alltoall, limit to 500 routers
python3 run_scaling_experiments.py --topo-name DDF --benchmark Alltoall --problem-size 64 --max-routers 500

# Polarfly with custom nexullance sample count
python3 run_scaling_experiments.py --topo-name Polarfly --num-samples 64

# Compare only shortest_path and ugal (skip nexullance)
python3 run_scaling_experiments.py --topo-name DDF --routing-methods shortest_path ugal

# Show all options
python3 run_scaling_experiments.py --help
```

### Command-line Arguments

**Topology Parameters:**
- `--topo-name`, `-t` *(required)*: Topology name — `Slimfly`/`SF`, `DDF`, `Polarfly`/`PF`
- `--max-routers`: Maximum number of routers to include (default: 1000)

**Benchmark Parameters:**
- `--benchmark`, `-b`: Ember benchmark — `Allreduce`, `Alltoall`, `FFT3D` (default: `Allreduce`)
- `--problem-size`: Problem size for the benchmark (default: benchmark-specific)
- `--cores-per-ep`: Cores per endpoint (default: 4)
- `--link-bw`: Link bandwidth in Gbps (default: 16)

**Routing Methods:**
- `--routing-methods`: Space-separated list (default: `shortest_path ugal nexullance`)
- `--num-samples`: MD sample count for nexullance (default: 32)

**System Parameters:**
- `--num-threads`: Number of SST threads (default: 8)

### Topology Configurations

Configurations come from `topoResearch/global_helpers.py`:

| Topology | Configs | V range |
|---|---|---|
| Slimfly (`sf_configs_t1k`) | 12 | 18 – 1058 |
| DDF (`ddf_configs_t1k`) | 6 | 36 – 1386 |
| Polarfly (`pf_regular_configs_t1k`) | subset | 13 – 1057 |

### Benchmark Defaults

| Benchmark | `bench_args` template | Default size |
|---|---|---|
| Allreduce | `iterations=10 count={size}` | 256 |
| Alltoall  | `bytes={size}` | 64 |
| FFT3D     | `nx={size} ny={size} nz={size} npRow=12` | 256 |

### Plotting Results

```bash
# Plot a specific final results CSV
python3 plot_scaling_results.py scaling_Slimfly_Allreduce_20260318_120000.csv

# Plot all final CSVs in this directory
python3 plot_scaling_results.py

# Quick look at intermediate results during a long run
python3 plot_intermediate_results.py
```

## Output Files

Each experiment run produces:
- `scaling_{topo}_{benchmark}_{timestamp}.csv` — final results table
- `scaling_{topo}_{benchmark}_{timestamp}_metadata.json` — run parameters
- `scaling_{topo}_{benchmark}_intermediate_{timestamp}.csv` — saved after each network size

Plots saved alongside the CSVs:
- `scaling_simtime_{topo}_{benchmark}.png`
- `scaling_speedup_{topo}_{benchmark}.png`
- `scaling_runtime_{topo}_{benchmark}.png`
- `scaling_combined_{topo}_{benchmark}.png`

## CSV Schema

| Column | Description |
|---|---|
| `V`, `D`, `EPR` | Router count, degree, endpoints-per-router |
| `num_endpoints`, `total_cores` | Network scale |
| `{method}_sim_time_ms` | MPI benchmark simulation time (lower = faster app) |
| `{method}_runtime` | SST wall-clock runtime (seconds) |
| `{method}_success` | Whether the run succeeded |
| `{method}_speedup` | `baseline_ms / method_ms` (vs shortest path) |

Routing methods: `shortest_path`, `ugal`, `nexullance`
