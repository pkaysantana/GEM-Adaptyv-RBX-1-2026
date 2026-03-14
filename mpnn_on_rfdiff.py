#!/usr/bin/env python3
"""
Run ProteinMPNN on RFdiffusion-generated backbone PDBs.
Each PDB has:
  Chain A = binder (to be sequence-designed)
  Chain B = RBX-1 (fixed — do not redesign)

Applies biophysical filters and diversity selection,
then merges with existing ProteinMPNN-only sequences.
"""
import csv, json, os, subprocess, sys, glob
from pathlib import Path

RFDIFF_OUT  = Path('/home/on/rfdiff_outputs')
MPNN_DIR    = Path('/home/on/ProteinMPNN')
MPNN_SCRIPT = MPNN_DIR / 'protein_mpnn_run.py'
MPNN_HELPER = MPNN_DIR / 'helper_scripts'
MPNN_OUT    = Path('/home/on/mpnn_on_rfdiff')

EXISTING_CSV  = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')
FINAL_CSV     = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')
RFDIFF_SCORED = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_mpnn.csv')

TEMPS       = [0.1, 0.2, 0.3]   # sample temperatures
N_PER_TEMP  = 5                  # sequences per temperature per backbone
MAX_BINDERS = 100                # total in final submission

def flush(msg):
    print(msg, flush=True)

def is_biophysically_sane(seq):
    n = len(seq)
    if n < 40 or n > 120:
        return False
    if max(seq.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY') / n > 0.20:
        return False
    if (seq.count('R') + seq.count('K')) / n > 0.25:
        return False
    if (seq.count('F') + seq.count('W') + seq.count('Y')) / n > 0.25:
        return False
    net = (seq.count('K') + seq.count('R')) - (seq.count('D') + seq.count('E'))
    if abs(net) > 8:
        return False
    if seq.count('P') / n > 0.12:
        return False
    return True

def seq_identity(a, b):
    return sum(x == y for x, y in zip(a, b)) / max(len(a), len(b))

# ─── Find RFdiffusion PDBs ───────────────────────────────────────────────────
pdb_files = sorted(RFDIFF_OUT.glob('rbx1_binder_*.pdb'))
flush(f"Found {len(pdb_files)} RFdiffusion backbone PDBs")
if not pdb_files:
    flush("ERROR: No PDB files found. Did RFdiffusion finish?")
    sys.exit(1)

MPNN_OUT.mkdir(parents=True, exist_ok=True)

# ─── Step 1: Parse PDBs to JSONL format ─────────────────────────────────────
pdb_dir    = RFDIFF_OUT  # directory containing the 50 PDBs
parsed_dir = MPNN_OUT / 'parsed_pdbs'
parsed_dir.mkdir(exist_ok=True)

flush("Parsing PDBs to JSONL...")
result = subprocess.run([
    'python', str(MPNN_HELPER / 'parse_multiple_chains.py'),
    '--input_path',  str(pdb_dir),
    '--output_path', str(parsed_dir),
], capture_output=True, text=True)
if result.returncode != 0:
    flush(f"  parse error: {result.stderr[-300:]}")
    sys.exit(1)

parsed_jsonl = parsed_dir / 'parsed_pdbs.jsonl'
flush(f"  Parsed JSONL: {parsed_jsonl}")

# ─── Step 2: Assign fixed chains (fix chain B = RBX-1) ──────────────────────
chain_jsonl = MPNN_OUT / 'chain_fix.jsonl'
result = subprocess.run([
    'python', str(MPNN_HELPER / 'assign_fixed_chains.py'),
    '--input_path',  str(parsed_jsonl),
    '--output_path', str(chain_jsonl),
    '--chain_list',  'B',   # fix chain B (RBX-1), design chain A (binder)
], capture_output=True, text=True)
if result.returncode != 0:
    flush(f"  chain assign error: {result.stderr[-300:]}")
    sys.exit(1)
flush(f"  Chain fix JSONL: {chain_jsonl}")

# ─── Step 3: Run ProteinMPNN for each temperature ────────────────────────────
all_seqs = []
for T in TEMPS:
    out_dir = MPNN_OUT / f'rfdiff_T{str(T).replace(".", "")}'
    out_dir.mkdir(exist_ok=True)

    cmd = [
        'python', str(MPNN_SCRIPT),
        '--jsonl_path',         str(parsed_jsonl),
        '--chain_id_jsonl',     str(chain_jsonl),
        '--out_folder',         str(out_dir),
        '--num_seq_per_target', str(N_PER_TEMP),
        '--sampling_temp',      str(T),
        '--batch_size',         '1',
        '--model_name',         'v_48_020',
    ]
    flush(f"\nRunning ProteinMPNN T={T}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        flush(f"  ERROR: {result.stderr[-500:]}")
        continue
    flush(f"  Done T={T}")

    # Parse FASTA outputs — chain A (binder) is first in the slash-separated sequence
    for fa in (out_dir / 'seqs').glob('*.fa'):
        header, seq_parts = '', []
        for line in fa.read_text().splitlines():
            if line.startswith('>'):
                if seq_parts and 'score=' in header:
                    try:
                        score = float([p for p in header.split(',') if 'score=' in p][0].split('=')[1])
                    except:
                        score = 0.0
                    seq = ''.join(seq_parts)
                    binder = seq.split('/')[0]  # chain A comes first
                    all_seqs.append({'sequence': binder, 'score': score,
                                     'source': f'rfdiff_{fa.stem}_T{T}'})
                header = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.strip())
        if seq_parts and 'score=' in header:
            try:
                score = float([p for p in header.split(',') if 'score=' in p][0].split('=')[1])
            except:
                score = 0.0
            seq = ''.join(seq_parts)
            binder = seq.split('/')[0]
            all_seqs.append({'sequence': binder, 'score': score,
                             'source': f'rfdiff_{fa.stem}_T{T}'})

flush(f"\nCollected {len(all_seqs)} raw RFdiffusion+MPNN sequences")

# ─── Filter ─────────────────────────────────────────────────────────────────
sane = [s for s in all_seqs if is_biophysically_sane(s['sequence'])]
flush(f"After biophysical filter: {len(sane)}")

# Sort by MPNN score (lower = better in log-prob)
sane.sort(key=lambda x: x['score'])

# ─── Diversity selection ─────────────────────────────────────────────────────
selected_rfdiff = []
for cand in sane:
    if len(selected_rfdiff) >= 60:
        break
    if not any(seq_identity(cand['sequence'], s['sequence']) > 0.65
               for s in selected_rfdiff):
        selected_rfdiff.append(cand)

flush(f"After diversity selection: {len(selected_rfdiff)} RFdiffusion+MPNN sequences")

# Write RFdiffusion+MPNN CSV
with RFDIFF_SCORED.open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Sequence', 'MPNNScore', 'Source'])
    for i, s in enumerate(selected_rfdiff, 1):
        w.writerow([f'RBX1_RFD_{i:03d}', s['sequence'],
                    f"{s['score']:.4f}", s['source']])
flush(f"Wrote {RFDIFF_SCORED}")

# ─── Merge with existing ProteinMPNN-only pool ───────────────────────────────
existing = list(csv.DictReader(EXISTING_CSV.open()))
flush(f"\nMerging with {len(existing)} existing ProteinMPNN sequences")

# Combined pool: prefer RFdiffusion sequences (better backbone quality)
combined = list(selected_rfdiff)
for row in existing:
    seq = row['Sequence']
    if not any(seq_identity(seq, s['sequence']) > 0.65 for s in combined):
        combined.append({'sequence': seq, 'score': 0.0, 'source': 'mpnn_only'})
    if len(combined) >= MAX_BINDERS:
        break

flush(f"Combined pool: {len(combined)} unique sequences")

# Write final submission
with FINAL_CSV.open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Sequence'])
    for i, s in enumerate(combined[:MAX_BINDERS], 1):
        prefix = 'RBX1_RFD' if 'rfdiff' in s.get('source', '') else 'RBX1_MPNN'
        w.writerow([f'{prefix}_{i:03d}', s['sequence']])

flush(f"\nFinal submission written to {FINAL_CSV}")
flush(f"  RFdiffusion+MPNN sequences: {sum(1 for s in combined[:MAX_BINDERS] if 'rfdiff' in s.get('source',''))}")
flush(f"  ProteinMPNN-only sequences: {sum(1 for s in combined[:MAX_BINDERS] if 'mpnn_only' in s.get('source',''))}")
flush("Done!")
