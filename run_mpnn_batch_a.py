#!/usr/bin/env python3
"""
ProteinMPNN on RFdiffusion Batch A backbones.

Reads:   /home/on/rfdiff_outputs_v2/         (100 PDBs from Batch A)
Writes:  /home/on/mpnn_on_rfdiff_v2/         (MPNN outputs)
         rbx1_rfdiff_mpnn_v2.csv             (all raw sequences)
         rbx1_rfdiff_mpnn_v2_filtered.csv    (biophysically passing)

Does NOT merge with old submission or any previous CSV.
Chain convention: A = binder (design), B = RBX1 (fixed).
Temperatures: 0.1, 0.2, 0.3 x N_PER_TEMP seqs = 15 per backbone.
Resume-safe: skips temperatures whose output is already complete.
"""

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
PYTHON      = '/home/on/miniforge3/envs/protein-design/bin/python'
RFDIFF_OUT  = Path('/home/on/rfdiff_outputs_v2')
MPNN_DIR    = Path('/home/on/ProteinMPNN')
MPNN_SCRIPT = MPNN_DIR / 'protein_mpnn_run.py'
MPNN_HELPER = MPNN_DIR / 'helper_scripts'
MPNN_OUT    = Path('/home/on/mpnn_on_rfdiff_v2')
PROJECT     = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026')
RAW_CSV     = PROJECT / 'rbx1_rfdiff_mpnn_v2.csv'
FILT_CSV    = PROJECT / 'rbx1_rfdiff_mpnn_v2_filtered.csv'

TEMPS       = [0.1, 0.2, 0.3]
N_PER_TEMP  = 5       # sequences per backbone per temperature
N_BACKBONES = 100     # expected number of backbone PDBs

def flush(msg): print(msg, flush=True)


# ── biophysical filter ────────────────────────────────────────────────────────
def is_sane(seq: str) -> tuple[bool, list[str]]:
    """Return (passes, reason_list). Reasons include numeric context."""
    n = len(seq)
    reasons = []
    if n < 50 or n > 80:
        reasons.append(f'length={n}')
    if n > 0:
        max_single = max(seq.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY') / n
        if max_single > 0.20:
            reasons.append(f'single_aa_dominance={max_single:.2f}')
        pos_frac = (seq.count('R') + seq.count('K')) / n
        if pos_frac > 0.25:
            reasons.append(f'pos_charge={pos_frac:.2f}')
        aro_frac = (seq.count('F') + seq.count('W') + seq.count('Y')) / n
        if aro_frac > 0.25:
            reasons.append(f'aromatic={aro_frac:.2f}')
        pro_frac = seq.count('P') / n
        if pro_frac > 0.12:
            reasons.append(f'pro_frac={pro_frac:.2f}')
    net = (seq.count('K') + seq.count('R')) - (seq.count('D') + seq.count('E'))
    if abs(net) > 8:
        reasons.append(f'net_charge={net}')
    return len(reasons) == 0, reasons


# ── helpers ───────────────────────────────────────────────────────────────────
def count_backbone_pdbs() -> int:
    return len(list(RFDIFF_OUT.glob('rbx1_binder_*.pdb')))

def jsonl_is_fresh(jsonl_path: Path, expected_n: int) -> bool:
    """True if JSONL exists and contains exactly expected_n entries."""
    if not jsonl_path.exists():
        return False
    try:
        count = sum(1 for line in jsonl_path.open() if line.strip())
        return count == expected_n
    except OSError:
        return False

def temperature_is_complete(seqs_dir: Path, expected_fastas: int,
                             expected_seqs_per_fasta: int) -> bool:
    """True if seqs_dir has the right number of FASTAs and each has
    at least expected_seqs_per_fasta sequences (headers)."""
    if not seqs_dir.exists():
        return False
    fas = list(seqs_dir.glob('*.fa'))
    if len(fas) < expected_fastas:
        return False
    # Spot-check: count '>' lines in the first and last FASTA
    for fa in [fas[0], fas[-1]]:
        headers = sum(1 for l in fa.open() if l.startswith('>'))
        # MPNN writes 1 reference + N_PER_TEMP designed; total >= N_PER_TEMP + 1
        if headers < expected_seqs_per_fasta + 1:
            return False
    return True

def parse_fasta_file(fa: Path, backbone_id: str, tag: str) -> list[dict]:
    """Parse one ProteinMPNN FASTA; return list of binder sequence records.
    Skips the first (all-G reference) sequence.
    """
    records = []
    header, seq_parts = '', []

    def flush_record():
        if not header or not seq_parts:
            return
        raw    = ''.join(seq_parts)
        binder = raw.split('/')[0]
        score, global_score, snum = 0.0, 0.0, 0
        for tok in header.split(','):
            tok = tok.strip()
            if tok.startswith('score='):
                try: score = float(tok.split('=')[1])
                except ValueError: pass
            if tok.startswith('global_score='):
                try: global_score = float(tok.split('=')[1])
                except ValueError: pass
            if tok.startswith('sample='):
                try: snum = int(tok.split('=')[1])
                except ValueError: pass
        # Skip the all-G reference sequence (sample 0 / reference)
        if snum == 0 and set(binder.replace('/', '')) <= {'G', '/'}:
            return
        records.append({
            'backbone_id':           backbone_id,
            'temperature':           tag,
            'binder_chain_sequence': binder,
            'binder_length':         len(binder),
            'mpnn_score':            round(score, 4),
            'global_score':          round(global_score, 4),
            'sample_number':         snum,
        })

    for line in fa.read_text().splitlines():
        if line.startswith('>'):
            flush_record()
            header    = line[1:]
            seq_parts = []
        else:
            seq_parts.append(line.strip())
    flush_record()
    return records


# ── find PDBs ─────────────────────────────────────────────────────────────────
n_pdbs = count_backbone_pdbs()
flush(f"Found {n_pdbs} Batch A backbone PDBs in {RFDIFF_OUT}")
if n_pdbs == 0:
    sys.exit("ERROR: No PDBs found.")
if n_pdbs != N_BACKBONES:
    flush(f"WARNING: expected {N_BACKBONES} PDBs, found {n_pdbs}. "
          f"Proceeding with {n_pdbs}.")
    actual_backbones = n_pdbs
else:
    actual_backbones = N_BACKBONES

MPNN_OUT.mkdir(parents=True, exist_ok=True)

# ── step 1+2: parse PDBs to JSONL (skip only if fresh) ───────────────────────
parsed_jsonl = MPNN_OUT / 'parsed_pdbs.jsonl'
chain_jsonl  = MPNN_OUT / 'chain_fix.jsonl'

if jsonl_is_fresh(parsed_jsonl, actual_backbones) and chain_jsonl.exists():
    flush(f"Step 1+2: JSONL files present and match {actual_backbones} backbones — skipping.")
else:
    flush("Step 1: Parsing PDBs to JSONL...")
    r = subprocess.run([
        PYTHON, str(MPNN_HELPER / 'parse_multiple_chains.py'),
        '--input_path',  str(RFDIFF_OUT),
        '--output_path', str(parsed_jsonl),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"parse_multiple_chains failed:\n{r.stderr[-500:]}")
    flush(f"  -> {parsed_jsonl}")

    flush("Step 2: Assigning fixed chains (B = RBX1)...")
    r = subprocess.run([
        PYTHON, str(MPNN_HELPER / 'assign_fixed_chains.py'),
        '--input_path',  str(parsed_jsonl),
        '--output_path', str(chain_jsonl),
        '--chain_list',  'B',
    ], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"assign_fixed_chains failed:\n{r.stderr[-500:]}")
    flush(f"  -> {chain_jsonl}")

# ── step 3: run ProteinMPNN per temperature (skip if complete) ────────────────
flush("\nStep 3: Running ProteinMPNN...")
for T in TEMPS:
    tag      = f'T{str(T).replace(".", "")}'
    out_dir  = MPNN_OUT / tag
    out_dir.mkdir(exist_ok=True)
    seqs_dir = out_dir / 'seqs'

    if temperature_is_complete(seqs_dir, actual_backbones, N_PER_TEMP):
        n_fa = len(list(seqs_dir.glob('*.fa')))
        flush(f"  T={T} ({tag}): complete ({n_fa} FASTAs verified) — skipping.")
        continue

    flush(f"  T={T} ({tag}): running ProteinMPNN on {actual_backbones} backbones...")
    r = subprocess.run([
        PYTHON, str(MPNN_SCRIPT),
        '--jsonl_path',         str(parsed_jsonl),
        '--chain_id_jsonl',     str(chain_jsonl),
        '--out_folder',         str(out_dir),
        '--num_seq_per_target', str(N_PER_TEMP),
        '--sampling_temp',      str(T),
        '--batch_size',         '1',
        '--model_name',         'v_48_020',
    ], capture_output=True, text=True)
    if r.returncode != 0:
        flush(f"  T={T} ERROR:\n{r.stderr[-400:]}")
        continue
    n_fa = len(list(seqs_dir.glob('*.fa'))) if seqs_dir.exists() else 0
    flush(f"  T={T} ({tag}): done — {n_fa} FASTA files written.")

# ── step 4: parse all FASTA outputs ──────────────────────────────────────────
flush("\nStep 4: Parsing FASTA outputs...")
all_seqs: list[dict] = []

for T in TEMPS:
    tag      = f'T{str(T).replace(".", "")}'
    seqs_dir = MPNN_OUT / tag / 'seqs'
    if not seqs_dir.exists():
        flush(f"  {tag}: seqs/ not found — skipping.")
        continue

    fas = sorted(seqs_dir.glob('*.fa'))
    t_seqs = []
    for fa in fas:
        t_seqs.extend(parse_fasta_file(fa, fa.stem, tag))
    all_seqs.extend(t_seqs)

    expected = actual_backbones * N_PER_TEMP
    flush(f"  {tag}: {len(t_seqs)} sequences parsed "
          f"(expected ~{expected}, got {len(t_seqs)})")

flush(f"\nTotal raw sequences: {len(all_seqs)}")

if not all_seqs:
    sys.exit("ERROR: No sequences parsed. Check MPNN outputs.")

# ── write raw CSV ─────────────────────────────────────────────────────────────
raw_fields = ['backbone_id', 'temperature', 'binder_length', 'mpnn_score',
              'global_score', 'sample_number', 'binder_chain_sequence']
with RAW_CSV.open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=raw_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(all_seqs)
flush(f"Raw CSV -> {RAW_CSV}  ({len(all_seqs)} sequences)")

# ── step 5: biophysical filter ────────────────────────────────────────────────
flush("\nStep 5: Biophysical filter...")
passed: list[dict] = []
failed: list[dict] = []

for s in all_seqs:
    ok, reasons = is_sane(s['binder_chain_sequence'])
    entry = {**s, 'filter_reasons': 'PASS' if ok else '|'.join(reasons)}
    (passed if ok else failed).append(entry)

total = len(all_seqs)
pass_rate = len(passed) / total * 100 if total > 0 else 0.0
flush(f"  Pass: {len(passed)}  Fail: {len(failed)}  ({pass_rate:.1f}% pass rate)")

tc = Counter(s['temperature'] for s in passed)
flush(f"  Passing by temperature: {dict(sorted(tc.items()))}")

lens = [s['binder_length'] for s in passed]
if lens:
    flush(f"  Length: min={min(lens)}  max={max(lens)}  "
          f"mean={sum(lens)/len(lens):.1f} aa")

bc = Counter(s['backbone_id'] for s in passed)
flush(f"  Distinct backbones with >=1 passing sequence: {len(bc)}")

# ── write filtered CSV ────────────────────────────────────────────────────────
filt_fields = ['sequence_id', 'backbone_id', 'temperature', 'binder_length',
               'mpnn_score', 'global_score', 'sample_number', 'filter_reasons',
               'binder_chain_sequence']
with FILT_CSV.open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=filt_fields, extrasaction='ignore')
    w.writeheader()
    for s in passed:
        row = dict(s)
        row['sequence_id'] = (f"{s['backbone_id']}_{s['temperature']}"
                              f"_s{s['sample_number']}")
        w.writerow(row)

flush(f"Filtered CSV -> {FILT_CSV}  ({len(passed)} sequences)")
flush("\nDone. Next step: run ESMFold screen on rbx1_rfdiff_mpnn_v2_filtered.csv")
