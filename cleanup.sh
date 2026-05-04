#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRACES_DIR="$SCRIPT_DIR/traffic_traces"
RESULTS_DIR="$SCRIPT_DIR/simulation_results"

# Verify targets are accessible (important if dirs are symlinks to mounted disk)
if [ ! -d "$TRACES_DIR" ] || [ ! -d "$RESULTS_DIR" ]; then
    echo "ERROR: One or both directories not found or not mounted."
    exit 1
fi

echo "This will delete all files in:"
echo "  $TRACES_DIR"
echo "  $RESULTS_DIR"
read -rp "Are you sure? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

rm -f "$TRACES_DIR"/*
rm -rf "$RESULTS_DIR"/*/
echo "Done."