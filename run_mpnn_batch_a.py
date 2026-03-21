#!/usr/bin/env python3
"""
ProteinMPNN on RFdiffusion Batch A backbones.

Reads:   /home/on/rfdiff_outputs_v2/  (100 PDBs from Batch A)
Writes:  /home/on/mpnn_on_rfdiff_v2/  (MPNN outputs)
         rbx1_rfdiff_mpnn_v2.csv      (all raw sequences)
         rbx1_rfdiff_mpnn_v2_filtered.csv  (biophysically passing)

Does NOT merge with old submission or any previous CSV.
Chain convention: A = binder (design), B = RBX1 (fixed).
Temperatures: 0.1, 0.2, 0.3 × 5 seqs = 15 per backbone → 1500 raw sequences.
"""

import csv, subprocess, sys
from pathlib import Path
from collections import Counter

# ── paths ─────────────────────────────────────────────────────────────────────
RFDIFF_OUT  = Path('/home/on/rfdiff_outputs_v2')
MPNN_DIR    = Path('/home/on/ProteinMPNN')
MPNN_SCRIPT = MPNN_DIR / 'protein_mpnn_run.py'
MPNN_HELPER = MPNN_DIR / 'helper_scripts'
MPNN_OUT    = Path('/home/on/mpnn_on_rfdiff_v2')

PROJECT     = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026')
RAW_CSV     = PROJECT / 'rbx1_rfdiff_mpnn_v2.csv'
FILT_CSV    = PROJECT / 'rbx1_rfdiff_mpnn_v2_filtered.csv'

TEMPS       = [0.1, 0.2, 0.3]
N_PER_TEMP  = 5
PYTHON      = '/home/on/miniforge3/envs/protein-design/bin/python'

def flush(msg): print(msg, flush=True)

# ── biophysical filter ────────────────────────────────────────────────────────
def is_sane(seq: str) -> tuple[bool, list[str]]:
    n = len(seq)
    reasons = []
    if n < 50 or n > 80:
        reasons.append(f'length={n}')
    if max(seq.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY') / n > 0.20:
        reasons.append('single_aa_dominance>20%')
    charged_pos = (seq.count('R') + seq.count('K')) / n
    if charged_pos > 0.25:
        reasons.append(f'pos_charge={charged_pos:.2f}')
    aromatic = (seq.count('F') + seq.count('W') + seq.count('Y')) / n
    if aromatic > 0.25:
        reasons.append(f'aromatic={aromatic:.2f}')
    net = (seq.count('K') + seq.count('R')) - (seq.count('D') + seq.count('E'))
    if abs(net) > 8:
        reasons.append(f'net_charge={net}')
    if seq.count('P') / n > 0.12:
        reasons.append(f'pro_frac={seq.count("P")/n:.2f}')
    return (len(reasons) == 0), reasons

# ── find PDBs ─────────────────────────────────────────────────────────────────
pdb_files = sorted(RFDIFF_OUT.glob('rbx1_binder_*.pdb'),
                   key=lambda p: int(p.stem.split('_')[-1]))
flush(f"Found {len(pdb_files)} Batch A backbone PDBs in {RFDIFF_OUT}")
if not pdb_files:
    sys.exit("ERROR: No PDBs found.")

MPNN_OUT.mkdir(parents=True, exist_ok=True)

# ── step 1: parse PDBs to JSONL ───────────────────────────────────────────────
parsed_jsonl = MPNN_OUT / 'parsed_pdbs.jsonl'
flush("\nStep 1: Parsing PDBs to JSONL...")
r = subprocess.run([
    'python', str(MPNN_HELPER / 'parse_multiple_chains.py'),
    '--input_path',  str(RFDIFF_OUT),
    '--output_path', str(parsed_jsonl),
], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"parse_multiple_chains failed:\n{r.stderr[-500:]}")
flush(f"  -> {parsed_jsonl}")

# ── step 2: assign fixed chains (fix B = RBX1) ────────────────────────────────
chain_jsonl = MPNN_OUT / 'chain_fix.jsonl'
flush("Step 2: Assigning fixed chains (B = RBX1)...")
r = subprocess.run([
    'python', str(MPNN_HELPER / 'assign_fixed_chains.py'),
    '--input_path',  str(parsed_jsonl),
    '--output_path', str(chain_jsonl),
    '--chain_list',  'B',
], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"assign_fixed_chains failed:\n{r.stderr[-500:]}")
flush(f"  -> {chain_jsonl}")

# ── step 3: run ProteinMPNN at each temperature ───────────────────────────────
flush("\nStep 3: Running ProteinMPNN...")
all_seqs = []

for T in TEMPS:
    tag = f'T{str(T).replace(".", "")}'
    out_dir = MPNN_OUT / tag
    out_dir.mkdir(exist_ok=True)

    r = subprocess.run([
        'python', str(MPNN_SCRIPT),
        '--jsonl_path',         str(parsed_jsonl),
        '--chain_id_jsonl',     str(chain_jsonl),
        '--out_folder',         str(out_dir),
        '--num_seq_per_target', str(N_PER_TEMP),
        '--sampling_temp',      str(T),
        '--batch_size',         '1',
        '--model_name',         'v_48_020',
    ], capture_output=True, text=True)
    if r.returncode != 0:
        flush(f"  T={T} ERROR: {r.stderr[-300:]}")
        continue

    # Parse FASTA outputs — chain A (binder) is first slash-delimited segment
    n_parsed = 0
    for fa in sorted((out_dir / 'seqs').glob('*.fa')):
        backbone_id = fa.stem  # e.g. rbx1_binder_42
        current_header = ''
        seq_parts = []
        for line in fa.read_text().splitlines():
            if line.startswith('>'):
                if seq_parts and current_header:
                    _emit(current_header, seq_parts, backbone_id, T, all_seqs)
                    n_parsed += 1
                current_header = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.strip())
        if seq_parts and current_header:
            _emit(current_header, seq_parts, backbone_id, T, all_seqs)
            n_parsed += 1

    flush(f"  T={T}: parsed {n_parsed} sequences")

flush(f"\nTotal raw sequences: {len(all_seqs)}")


def _emit(header, seq_parts, backbone_id, T, bucket):
    """Parse header for score and push binder sequence to bucket."""
    raw = ''.join(seq_parts)
    binder = raw.split('/')[0]
    score = 0.0
    try:
        score_part = [p for p in header.split(',') if 'score=' in p]
        if score_part:
            score = float(score_part[0].split('=')[1])
    except Exception:
        pass
    # sample number: last token in header after last comma before \n, or count
    sample = None
    try:
        for tok in header.split(','):
            if tok.strip().startswith('sample='):
                sample = int(tok.strip().split('=')[1])
    except Exception:
        pass
    bucket.append({
        'backbone_id':           backbone_id,
        'temperature':           f'T{str(T).replace(".", "")}',
        'binder_chain_sequence': binder,
        'binder_length':         len(binder),
        'mpnn_score':            round(score, 4),
        'sample_number':         sample or len(bucket) % N_PER_TEMP + 1,
    })


# Rebuild: the function was defined after use — re-parse properly
all_seqs = []
for T in TEMPS:
    tag = f'T{str(T).replace(".", "")}'
    out_dir = MPNN_OUT / tag
    if not (out_dir / 'seqs').exists():
        continue
    for fa in sorted((out_dir / 'seqs').glob('*.fa')):
        backbone_id = fa.stem
        current_header = ''
        seq_parts = []
        lines = fa.read_text().splitlines()
        for line in lines:
            if line.startswith('>'):
                if seq_parts and current_header:
                    raw = ''.join(seq_parts)
                    binder = raw.split('/')[0]
                    score = 0.0
                    try:
                        sp = [p for p in current_header.split(',') if 'score=' in p]
                        if sp: score = float(sp[0].split('=')[1])
                    except Exception: pass
                    snum = 0
                    try:
                        for tok in current_header.split(','):
                            if 'sample=' in tok:
                                snum = int(tok.strip().split('=')[1])
                    except Exception: pass
                    all_seqs.append({
                        'backbone_id':           backbone_id,
                        'temperature':           f'T{str(T).replace(".", "")}',
                        'binder_chain_sequence': binder,
                        'binder_length':         len(binder),
                        'mpnn_score':            round(score, 4),
                        'sample_number':         snum,
                    })
                current_header = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.strip())
        # last record
        if seq_parts and current_header:
            raw = ''.join(seq_parts)
            binder = raw.split('/')[0]
            score = 0.0
            try:
                sp = [p for p in current_header.split(',') if 'score=' in p]
                if sp: score = float(sp[0].split('=')[1])
            except Exception: pass
            snum = 0
            try:
                for tok in current_header.split(','):
                    if 'sample=' in tok:
                        snum = int(tok.strip().split('=')[1])
            except Exception: pass
            all_seqs.append({
                'backbone_id':           backbone_id,
                'temperature':           f'T{str(T).replace(".", "")}',
                'binder_chain_sequence': binder,
                'binder_length':         len(binder),
                'mpnn_score':            round(score, 4),
                'sample_number':         snum,
            })

flush(f"Re-parsed total sequences: {len(all_seqs)}")

# ── write raw CSV ─────────────────────────────────────────────────────────────
fields = ['backbone_id', 'temperature', 'binder_length', 'mpnn_score',
          'sample_number', 'binder_chain_sequence']
with RAW_CSV.open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(all_seqs)
flush(f"\nRaw CSV written -> {RAW_CSV}  ({len(all_seqs)} sequences)")

# ── filter ────────────────────────────────────────────────────────────────────
flush("\nStep 4: Biophysical filter...")
passed, failed = [], []
for s in all_seqs:
    seq = s['binder_chain_sequence']
    ok, reasons = is_sane(seq)
    rec = {**s, 'filter_reasons': 'PASS' if ok else '|'.join(reasons)}
    (passed if ok else failed).append(rec)

flush(f"  Pass: {len(passed)}  Fail: {len(failed)}  "
      f"({len(passed)/len(all_seqs)*100:.1f}% pass rate)")

# Temperature breakdown
tc = Counter(s['temperature'] for s in passed)
flush(f"  Passing by temperature: {dict(sorted(tc.items()))}")

# Length distribution of passing
lens = [s['binder_length'] for s in passed]
if lens:
    flush(f"  Length range: {min(lens)}-{max(lens)} aa  mean={sum(lens)/len(lens):.1f}")

# Write filtered CSV (add sequence_id column)
filt_fields = ['sequence_id', 'backbone_id', 'temperature', 'binder_length',
               'mpnn_score', 'sample_number', 'filter_reasons',
               'binder_chain_sequence']
with FILT_CSV.open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=filt_fields, extrasaction='ignore')
    w.writeheader()
    for s in passed:
        row = dict(s)
        row['sequence_id'] = (f"{s['backbone_id']}_{s['temperature']}"
                              f"_s{s['sample_number']}")
        w.writerow(row)
flush(f"Filtered CSV written -> {FILT_CSV}  ({len(passed)} sequences)")

flush("\n== Done. Next step: run_esmfold_screen.py pointed at rbx1_rfdiff_mpnn_v2_filtered.csv ==")
