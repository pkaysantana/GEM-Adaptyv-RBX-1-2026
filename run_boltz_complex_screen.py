#!/usr/bin/env python3
"""
Boltz-2 complex validation for top RFdiffusion→ProteinMPNN binder candidates.

Chains:
  A = RBX1 (target, 90 aa, chain B from 1LDJ)
  B = binder (designed sequence)

Outputs:
  /home/on/boltz_rfdiff_inputs/   — one FASTA per candidate
  /home/on/boltz_rfdiff_outputs/  — Boltz predictions
  rbx1_boltz_complex_scores.csv   — parsed confidence summary

Key metrics extracted per candidate:
  iptm            — interface TM-score (complex quality, 0–1)
  protein_iptm    — protein-only iPTM
  pair_iptm_AB    — chain-A↔chain-B iPTM (direct interface metric)
  ptm             — global TM-score
  complex_plddt   — mean pLDDT over full complex
"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

# ── sequences ────────────────────────────────────────────────────────────────
RBX1_SEQ = "KKRFEVKKWNAVALWAWDIVVDNCAICRNHIMDLCIECQANQASATSEECTVAWGVCNHAFHFHCISRWLKTRQVCPLDNREWEFQKY"

CANDIDATES = [
    # (sequence_id, backbone, temperature, binder_sequence)
    ("rbx1_binder_7_T02_s4",  "rbx1_binder_7",  "T02",
     "AHPLTQLLKKAADLKAETEEFIKRNQEKLTQEEIEEIRLKTAEEVAALLAEARALLSAEIAG"),
    ("rbx1_binder_7_T02_s2",  "rbx1_binder_7",  "T02",
     "MHPADKLAKKAEELRAKTEAFIEANQDKLTPEEIQQILRKTEEEVAKLEKERDKLVKKRIAG"),
    ("rbx1_binder_7_T03_s5",  "rbx1_binder_7",  "T03",
     "PSALAQLLRKAKELEAKTQAFLAENQSKLSPEEKQKIILETLKEIAKLKAEADALLKAKIRG"),
    ("rbx1_binder_25_T03_s1", "rbx1_binder_25", "T03",
     "QTWEQLRQAALNAFEARHAAELAEMEAKAAAEKEDEAKMLEMEKERQLFRLQRQQELAQLQQKLDHARQLQLQKEA"),
    ("rbx1_binder_11_T03_s5", "rbx1_binder_11", "T03",
     "SLEELLRELREAEKRRLLAERIADVIKAIKALTPEEIAKIIAVLESLLRPIREEKFRKRMKELQ"),
]

# ── paths ─────────────────────────────────────────────────────────────────────
INPUT_DIR  = Path("/home/on/boltz_rfdiff_inputs")
OUTPUT_DIR = Path("/home/on/boltz_rfdiff_outputs")
SCORE_CSV  = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_boltz_complex_scores.csv")
BOLTZ_BIN  = "/home/on/miniforge3/envs/protein-design/bin/boltz"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── step 1: write input FASTAs ────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Writing Boltz input FASTAs")
print("=" * 60)
for seq_id, backbone, temp, binder_seq in CANDIDATES:
    fasta_path = INPUT_DIR / f"{seq_id}.fasta"
    fasta_text = (
        f">A|protein\n{RBX1_SEQ}\n"
        f">B|protein\n{binder_seq}\n"
    )
    fasta_path.write_text(fasta_text)
    print(f"  {fasta_path.name}  (RBX1={len(RBX1_SEQ)} aa, binder={len(binder_seq)} aa)")

print(f"\n  {len(CANDIDATES)} FASTA files written to {INPUT_DIR}\n")

# ── step 2: run Boltz predict ─────────────────────────────────────────────────
print("=" * 60)
print("STEP 2 — Running Boltz-2 complex prediction")
print("=" * 60)
cmd = [
    BOLTZ_BIN, "predict",
    str(INPUT_DIR),
    "--out_dir",          str(OUTPUT_DIR),
    "--accelerator",      "gpu",
    "--recycling_steps",  "3",
    "--diffusion_samples","1",
    "--output_format",    "pdb",
    "--write_full_pae",
    "--override",
]
print("CMD:", " ".join(cmd))
print()

result = subprocess.run(cmd, text=True)
if result.returncode != 0:
    print(f"\nBoltz exited with code {result.returncode}")
    print("Attempting to parse any partial outputs...")

# ── step 3: parse confidence JSONs ────────────────────────────────────────────
print()
print("=" * 60)
print("STEP 3 — Parsing confidence scores")
print("=" * 60)

# Boltz output layout (2.x):
#   {OUTPUT_DIR}/predictions/{boltz_run_name}/predictions/{seq_id}/
#       confidence_{seq_id}_model_0.json
# The run name is boltz_results_{INPUT_DIR.name}
boltz_run_name = f"boltz_results_{INPUT_DIR.name}"
pred_base = OUTPUT_DIR / boltz_run_name / "predictions"

rows = []
for seq_id, backbone, temp, binder_seq in CANDIDATES:
    conf_path = pred_base / seq_id / f"confidence_{seq_id}_model_0.json"
    if not conf_path.exists():
        # fallback: search
        found = list((OUTPUT_DIR).rglob(f"confidence_{seq_id}_model_0.json"))
        conf_path = found[0] if found else None

    if conf_path is None or not conf_path.exists():
        print(f"  MISSING: {seq_id}")
        rows.append({
            "sequence_id":    seq_id,
            "backbone_id":    backbone,
            "temperature":    temp,
            "binder_length":  len(binder_seq),
            "iptm":           None,
            "protein_iptm":   None,
            "pair_iptm_AB":   None,
            "ptm":            None,
            "complex_plddt":  None,
            "status":         "missing",
            "binder_chain_sequence": binder_seq,
        })
        continue

    with open(conf_path) as fh:
        c = json.load(fh)

    iptm           = round(c.get("iptm",          0), 4)
    protein_iptm   = round(c.get("protein_iptm",  0), 4)
    ptm            = round(c.get("ptm",            0), 4)
    complex_plddt  = round(c.get("complex_plddt", 0), 4)

    # pair_chains_iptm["0"]["1"] = RBX1↔binder interface score
    pci = c.get("pair_chains_iptm", {})
    pair_AB = None
    if "0" in pci and "1" in pci.get("0", {}):
        pair_AB = round(pci["0"]["1"], 4)

    print(f"  {seq_id}")
    print(f"    iptm={iptm:.3f}  protein_iptm={protein_iptm:.3f}  "
          f"pair_AB={pair_AB}  ptm={ptm:.3f}  complex_plddt={complex_plddt:.3f}")

    rows.append({
        "sequence_id":    seq_id,
        "backbone_id":    backbone,
        "temperature":    temp,
        "binder_length":  len(binder_seq),
        "iptm":           iptm,
        "protein_iptm":   protein_iptm,
        "pair_iptm_AB":   pair_AB,
        "ptm":            ptm,
        "complex_plddt":  complex_plddt,
        "status":         "ok",
        "binder_chain_sequence": binder_seq,
    })

# ── write CSV ─────────────────────────────────────────────────────────────────
fields = ["sequence_id", "backbone_id", "temperature", "binder_length",
          "iptm", "protein_iptm", "pair_iptm_AB", "ptm", "complex_plddt",
          "status", "binder_chain_sequence"]
with open(SCORE_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(f"\n  Score CSV -> {SCORE_CSV}")

# ── summary ───────────────────────────────────────────────────────────────────
ok = [r for r in rows if r["status"] == "ok" and r["iptm"] is not None]
if not ok:
    print("\nNo successful predictions to summarise.")
    sys.exit(0)

print()
print("=" * 60)
print("RESULTS — ranked by iPTM (interface quality)")
print("=" * 60)
header = f"  {'sequence_id':<35} {'len':>4}  {'iPTM':>6}  {'prot_iPTM':>9}  {'pairAB':>7}  {'pTM':>6}  {'cPLDDT':>7}  temp"
print(header)
print("  " + "-" * (len(header) - 2))
for r in sorted(ok, key=lambda x: -(x["iptm"] or 0)):
    pab = f"{r['pair_iptm_AB']:.3f}" if r["pair_iptm_AB"] is not None else "  N/A "
    print(f"  {r['sequence_id']:<35} {r['binder_length']:>4}  "
          f"{r['iptm']:>6.3f}  {r['protein_iptm']:>9.3f}  {pab:>7}  "
          f"{r['ptm']:>6.3f}  {r['complex_plddt']:>7.3f}  {r['temperature']}")

print()
print("Interface quality thresholds (iPTM):")
for thresh, label in [(0.8, "excellent"), (0.6, "good"), (0.4, "marginal")]:
    n = sum(1 for r in ok if r["iptm"] >= thresh)
    print(f"  >= {thresh:.1f} ({label:8s}): {n}/{len(ok)}")

print()
print("Top candidate for submission:")
best = sorted(ok, key=lambda x: -(x["iptm"] or 0))[0]
print(f"  {best['sequence_id']}  iPTM={best['iptm']:.3f}  complex_pLDDT={best['complex_plddt']:.3f}")
