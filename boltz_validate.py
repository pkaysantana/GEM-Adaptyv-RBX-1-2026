#!/usr/bin/env python3
"""
Boltz-2 complex validation for RBX-1 binders.
Creates per-binder FASTA files and runs boltz predict,
then extracts interface confidence (ipSAE / ptm) scores.
"""
import csv, json, os, subprocess, shutil, sys
from pathlib import Path

# ─── Paths ─────────────────────────────────────────────────────────────────
SUBMISSION = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')
OUT_DIR    = Path('/home/on/boltz_outputs')
FASTA_DIR  = OUT_DIR / 'inputs'
SCORES_OUT = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_boltz_scored.csv')

# RBX-1 chain B sequence (from PDB 1LDJ residues 19-106)
RBX1_SEQ = "KKRFEVKKWNAVALWAWDIVVDNCAICRNHIMDLCIECQANQASATSEECTVAWGVCNHAFHFHCISRWLKTRQVCPLDNREWEFQKY"

TOP_N = 20  # validate top N binders (increase after test)

def flush(msg):
    print(msg, flush=True)

# ─── Load sequences ─────────────────────────────────────────────────────────
seqs = list(csv.DictReader(SUBMISSION.open()))
flush(f"Loaded {len(seqs)} sequences — validating top {TOP_N}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
FASTA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Write FASTA inputs ──────────────────────────────────────────────────────
for row in seqs[:TOP_N]:
    name = row['Name'].replace('/', '_').replace(' ', '_')
    binder_seq = row['Sequence']
    fasta_path = FASTA_DIR / f"{name}.fasta"
    with fasta_path.open('w') as f:
        # Chain A = RBX-1 (target, fixed)
        f.write(f">A|protein\n{RBX1_SEQ}\n")
        # Chain B = binder
        f.write(f">B|protein\n{binder_seq}\n")

flush(f"Wrote {TOP_N} FASTA input files to {FASTA_DIR}")

# ─── Run Boltz predict ───────────────────────────────────────────────────────
boltz_out = OUT_DIR / 'predictions'
cmd = [
    'boltz', 'predict',
    str(FASTA_DIR),
    '--out_dir', str(boltz_out),
    '--accelerator', 'gpu',
    '--model', 'boltz2',
    '--recycling_steps', '3',
    '--sampling_steps', '100',    # reduced for speed (default 200)
    '--diffusion_samples', '1',
    '--no_kernels',               # skip optional CUDA kernels
]
flush(f"\nRunning: {' '.join(cmd)}\n")
result = subprocess.run(cmd, capture_output=False, text=True)
if result.returncode != 0:
    flush(f"Boltz exited with code {result.returncode}")

# ─── Parse scores ────────────────────────────────────────────────────────────
flush("\nParsing Boltz confidence scores...")
scores = []

for row in seqs[:TOP_N]:
    name = row['Name'].replace('/', '_').replace(' ', '_')
    # Boltz writes confidence JSONs to: predictions/boltz_results_<name>/
    # confidence file: predictions/boltz_results_<name>/confidence_<name>_model_0.json
    conf_pattern = boltz_out.glob(f"boltz_results_{name}/confidence_{name}_model_0.json")
    conf_files = list(conf_pattern)

    if not conf_files:
        # try alternate naming
        conf_files = list(boltz_out.glob(f"*{name}*/confidence*.json"))

    if conf_files:
        with conf_files[0].open() as f:
            conf = json.load(f)
        # Boltz confidence keys: ptm, iptm, ligand_iptm, complex_plddt, chains_ptm
        iptm      = conf.get('iptm', 0.0)
        ptm       = conf.get('ptm', 0.0)
        plddt     = conf.get('complex_plddt', 0.0)
        # interface PAE (lower = better interface)
        ipae      = conf.get('interface_pae', 99.0)
        score = (iptm * 0.8 + ptm * 0.2)  # weighted composite
        scores.append({
            'name': row['Name'],
            'sequence': row['Sequence'],
            'iptm': iptm,
            'ptm': ptm,
            'plddt': plddt,
            'ipae': ipae,
            'composite': score,
        })
        flush(f"  {row['Name']}: iptm={iptm:.3f}  ptm={ptm:.3f}  pLDDT={plddt:.1f}  iPAE={ipae:.1f}")
    else:
        flush(f"  {row['Name']}: NO OUTPUT FOUND")
        scores.append({
            'name': row['Name'],
            'sequence': row['Sequence'],
            'iptm': 0.0, 'ptm': 0.0, 'plddt': 0.0, 'ipae': 99.0, 'composite': 0.0,
        })

# ─── Sort and write ──────────────────────────────────────────────────────────
scores.sort(key=lambda x: x['composite'], reverse=True)

with SCORES_OUT.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['name', 'sequence', 'iptm', 'ptm', 'plddt', 'ipae', 'composite'])
    w.writeheader()
    for s in scores:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in s.items()})

flush(f"\nWrote scores to {SCORES_OUT}")
flush(f"\nTop 5 by composite score:")
for s in scores[:5]:
    flush(f"  {s['name']}: iptm={s['iptm']:.3f}  composite={s['composite']:.3f}")

if scores:
    valid = [s for s in scores if s['composite'] > 0]
    if valid:
        flush(f"\nMean iptm: {sum(s['iptm'] for s in valid)/len(valid):.3f}")
        flush(f"Max iptm:  {max(s['iptm'] for s in valid):.3f}")
