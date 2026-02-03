#!/bin/bash
# Run comparison experiments for all three routing methods:
# 1. Shortest-path routing
# 2. Nexullance IT optimization
# 3. UGAL adaptive routing
#
# Tests multiple topologies and traffic patterns

echo "========================================"
echo "ROUTING COMPARISON EXPERIMENTS"
echo "========================================"
echo "Testing routing methods:"
echo "  1. Shortest-path routing"
echo "  2. Nexullance IT optimization"
echo "  3. UGAL adaptive routing"
echo "========================================"
echo ""

# Configuration
PYTHON=python3.12

# Topology configurations from archive experiments
# Format: "topo_name V D"
CONFIGS=(
    # "RRG 36 5"
    # "DDF 36 5"
    "Slimfly 32 6"
)

# Traffic patterns to test
TRAFFIC_PATTERNS=(
    "uniform"
    "shift_1"
    "shift_half"
)

# Run experiments for each configuration and traffic pattern
for config in "${CONFIGS[@]}"; do
    # Parse config
    read -r topo V D <<< "$config"
    
    echo ""
    echo "========================================"
    echo "TOPOLOGY: $topo (V=$V, D=$D)"
    echo "========================================"
    
    for traffic in "${TRAFFIC_PATTERNS[@]}"; do
        echo ""
        echo "----------------------------------------"
        echo "Traffic Pattern: $traffic"
        echo "----------------------------------------"
        
        # Run comparison experiment
        $PYTHON run_experiments.py \
            --topo-name "$topo" \
            --V "$V" \
            --D "$D" \
            --traffic-pattern "$traffic" \
            --link-bw 16 \
            --load-start 0.1 \
            --load-end 1.0 \
            --load-step 0.2 \
            --num-threads 4 \
            --routing-methods shortest_path nexullance md_nexullance ugal
        
        if [ $? -ne 0 ]; then
            echo "ERROR: Experiment failed for $topo with $traffic traffic"
        else
            echo "SUCCESS: Experiment completed for $topo with $traffic traffic"
        fi
    done
done

echo ""
echo "========================================"
echo "ALL EXPERIMENTS COMPLETE"
echo "========================================"
echo "Results saved to: ../simulation_results/"
echo ""
