#!/usr/bin/env bash
# =============================================================================
# run_rfdiffusion_batch_a.sh
# RFdiffusion Batch A — primary expansion run
#
# Hotspot set:   B30,B33,B36,B60,B64,B68,B72,B85,B103 (proven, unchanged)
# Contig:        B19-106/0 55-75  (full RBX1, binder 55-75 aa)
# Trajectories:  100
# Output:        /home/on/rfdiff_outputs_v2/
#
# Downstream: feed PDBs to mpnn_on_rfdiff.py (point RFDIFF_OUT at v2 dir)
# =============================================================================

set -euo pipefail

PYTHON="/home/on/miniforge3/envs/protein-design/bin/python"
SCRIPT="/home/on/RFdiffusion/scripts/run_inference.py"
TARGET="/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/targets/rbx1_1LDJ.pdb"
OUT_PREFIX="/home/on/rfdiff_outputs_v2/rbx1_binder"
MODEL_DIR="/home/on/RFdiffusion/models"

mkdir -p /home/on/rfdiff_outputs_v2

echo "============================================================"
echo " RFdiffusion Batch A"
echo " Target:      $TARGET"
echo " Output dir:  /home/on/rfdiff_outputs_v2/"
echo " Designs:     100"
echo " Contigs:     B19-106/0 55-75"
echo " Hotspots:    B30,B33,B36,B60,B64,B68,B72,B85,B103"
echo "============================================================"
echo ""

"$PYTHON" "$SCRIPT" \
    inference.input_pdb="$TARGET" \
    inference.output_prefix="$OUT_PREFIX" \
    inference.num_designs=100 \
    inference.model_directory_path="$MODEL_DIR" \
    "contigmap.contigs=[B19-106/0 55-75]" \
    "ppi.hotspot_res=[B30,B33,B36,B60,B64,B68,B72,B85,B103]" \
    denoiser.noise_scale_ca=1 \
    denoiser.noise_scale_frame=1

echo ""
echo "============================================================"
echo " Batch A complete."
echo " PDBs written to: /home/on/rfdiff_outputs_v2/"
echo " Next step: run mpnn_on_rfdiff.py with RFDIFF_OUT pointed"
echo "            at /home/on/rfdiff_outputs_v2/"
echo "============================================================"
