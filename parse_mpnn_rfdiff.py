#!/usr/bin/env python3
"""
Parse ProteinMPNN FASTA outputs from RFdiffusion backbones.
Builds a flat CSV, deduplicates, applies biophysical filters.

FASTA FORMAT (verified on 6 representative files):
  - Record 0: reference backbone, all-G sequence, header contains
              designed_chains=['A'] fixed_chains=['B'] -> ALWAYS SKIP
  - Records 1-5: designed binder (chain A ONLY, no '/' separator,
                 no RBX-1 chain in output), variable length 66-79 AA
  - 5 samples per backbone per temperature, consistent
"""
import os
import re
import csv
import sys
from collections import defaultdict

# -- paths ---------------------------------------------------------------------
DIRS = {
    "T01": "/home/on/mpnn_on_rfdiff/rfdiff_T01/seqs",
    "T02": "/home/on/mpnn_on_rfdiff/rfdiff_T02/seqs",
    "T03": "/home/on/mpnn_on_rfdiff/rfdiff_T03/seqs",
}
OUT_CSV  = "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_mpnn.csv"
FILT_CSV = "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_mpnn_filtered.csv"

# -- charge table (physiological pH, standard assignment) ---------------------
# Verified pairings:
#   A  C  D   E   F  G  H  I  K   L  M  N  P  Q  R   S  T  V  W  Y
#   0  0  -1  -1  0  0  0  0  +1  0  0  0  0  0  +1  0  0  0  0  0
CHARGE = dict(zip(
    list("ACDEFGHIKLMNPQRSTVWY"),
    [  0, 0,-1,-1, 0, 0, 0, 0,+1, 0, 0, 0, 0, 0,+1, 0, 0, 0, 0, 0]
))

# -- preflight summary ---------------------------------------------------------
print("-- FASTA FORMAT PREFLIGHT ----------------------------------------------")
print("  Directories scanned:")
for label, d in DIRS.items():
    n = len([f for f in os.listdir(d) if f.endswith(".fa")]) if os.path.isdir(d) else 0
    print(f"    {label}: {d}  ({n} .fa files)")
print("  Format observed (verified on 6 representative files):")
print("    Record 0  = all-G reference backbone  -> skipped")
print("    Records 1-5 = designed binder (chain A only, no '/' multi-chain)")
print("    Binder lengths vary per backbone (66-79 AA observed)")
print("    5 samples per backbone per temperature")
print("  Binder extraction: take sequence as-is from records[1:] -- chain A only")
print("------------------------------------------------------------------------\n")

# -- biophysical filter -------------------------------------------------------
def filter_reasons(seq):
    reasons = []
    n = len(seq)
    if n == 0:
        return ["empty_sequence"]
    # max single amino acid fraction > 20%
    for aa in set(seq):
        frac = seq.count(aa) / n
        if frac > 0.20:
            reasons.append(f"single_aa_{aa}={frac*100:.1f}%")
    # R+K > 25%
    rk = (seq.count("R") + seq.count("K")) / n
    if rk > 0.25:
        reasons.append(f"R+K={rk*100:.1f}%")
    # F+W+Y > 25%
    fwy = (seq.count("F") + seq.count("W") + seq.count("Y")) / n
    if fwy > 0.25:
        reasons.append(f"F+W+Y={fwy*100:.1f}%")
    # |net charge| > 8
    net = sum(CHARGE.get(aa, 0) for aa in seq)
    if abs(net) > 8:
        reasons.append(f"|charge|={net}")
    # proline > 12%
    pro = seq.count("P") / n
    if pro > 0.12:
        reasons.append(f"P={pro*100:.1f}%")
    return reasons

# -- parse all FASTA files ----------------------------------------------------
rows = []
malformed = []

for temp_label, seq_dir in sorted(DIRS.items()):
    if not os.path.isdir(seq_dir):
        print(f"ERROR: directory not found: {seq_dir}", file=sys.stderr)
        continue
    fa_files = sorted(f for f in os.listdir(seq_dir) if f.endswith(".fa"))
    if not fa_files:
        print(f"WARNING: no .fa files in {seq_dir}", file=sys.stderr)
        continue

    for fa_file in fa_files:
        backbone_id = fa_file.replace(".fa", "")
        path = os.path.join(seq_dir, fa_file)

        # parse FASTA into (header, sequence) records
        records = []
        current_header = None
        current_seq_parts = []
        with open(path) as fh:
            for line in fh:
                line = line.rstrip()
                if line.startswith(">"):
                    if current_header is not None:
                        records.append((current_header, "".join(current_seq_parts).upper()))
                    current_header = line[1:]
                    current_seq_parts = []
                elif line:
                    current_seq_parts.append(line)
            if current_header is not None:
                records.append((current_header, "".join(current_seq_parts).upper()))

        # validate: need at least 1 reference + 1 sample
        if len(records) < 2:
            malformed.append((temp_label, fa_file, f"only {len(records)} record(s), expected >=2"))
            continue

        # record[0] = reference (all-G) -- verify and skip
        ref_header, ref_seq = records[0]
        if set(ref_seq) - {"G"}:
            malformed.append((temp_label, fa_file,
                f"record[0] not all-G (chars: {''.join(sorted(set(ref_seq)-{'G'}))}) -- skipping file"))
            continue

        # records[1:] = designed samples (binder chain A only)
        for header, seq in records[1:]:
            # score= appears twice in header: first = per-sample, second = global
            scores = re.findall(r"score=([-\d.]+)", header)
            per_sample_score = float(scores[0]) if len(scores) >= 1 else None
            global_score_val = float(scores[1]) if len(scores) >= 2 else None

            m_sample = re.search(r"sample=(\d+)", header)
            sample_n = int(m_sample.group(1)) if m_sample else -1

            seq_id = f"{backbone_id}_{temp_label}_s{sample_n}"

            if not seq:
                malformed.append((temp_label, fa_file, f"sample {sample_n}: empty sequence"))
                continue
            if set(seq) <= {"G"}:
                malformed.append((temp_label, fa_file, f"sample {sample_n}: all-G (undesigned?)"))
                continue
            invalid_aa = set(seq) - set("ACDEFGHIKLMNPQRSTVWY")
            if invalid_aa:
                malformed.append((temp_label, fa_file,
                    f"sample {sample_n}: non-standard AA {''.join(sorted(invalid_aa))}"))
                continue

            rows.append({
                "backbone_id":           backbone_id,
                "temperature":           temp_label,
                "fasta_file":            fa_file,
                "sequence_id":           seq_id,
                "binder_chain_sequence": seq,
                "binder_length":         len(seq),
                "mpnn_score":            per_sample_score,
                "global_score":          global_score_val,
                "sample_number":         sample_n,
            })

total_raw = len(rows)
print(f"Raw sequences parsed:   {total_raw}")

# -- deduplication (keep first occurrence) ------------------------------------
seen_seqs = {}
unique_rows = []
dup_count = 0
for r in rows:
    s = r["binder_chain_sequence"]
    if s not in seen_seqs:
        seen_seqs[s] = r["sequence_id"]
        unique_rows.append(r)
    else:
        dup_count += 1

print(f"Duplicate sequences:    {dup_count}")
print(f"Unique sequences:       {len(unique_rows)}")

by_temp_raw  = defaultdict(int)
by_temp_uniq = defaultdict(int)
for r in rows:
    by_temp_raw[r["temperature"]] += 1
for r in unique_rows:
    by_temp_uniq[r["temperature"]] += 1

print("\nRaw / unique by temperature:")
for t in sorted(by_temp_raw):
    print(f"  {t}: {by_temp_raw[t]} raw  ->  {by_temp_uniq[t]} unique")

# -- write full deduplicated CSV ----------------------------------------------
fieldnames = ["backbone_id","temperature","fasta_file","sequence_id",
              "binder_chain_sequence","binder_length","mpnn_score",
              "global_score","sample_number"]
with open(OUT_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(unique_rows)
print(f"\nFull CSV written -> {OUT_CSV}")

# -- biophysical filtering ----------------------------------------------------
fail_bucket = defaultdict(int)
passing = []
failing = []
for r in unique_rows:
    reasons = filter_reasons(r["binder_chain_sequence"])
    r["filter_reasons"] = ";".join(reasons) if reasons else "PASS"
    if not reasons:
        passing.append(r)
    else:
        failing.append(r)
        seen_rules = set()
        for reason in reasons:
            if "single_aa" in reason:
                rule = "single_aa>20%"
            elif reason.startswith("R+K"):
                rule = "R+K>25%"
            elif reason.startswith("F+W+Y"):
                rule = "F+W+Y>25%"
            elif "|charge|" in reason:
                rule = "|charge|>8"
            elif reason.startswith("P="):
                rule = "proline>12%"
            else:
                rule = reason
            if rule not in seen_rules:
                fail_bucket[rule] += 1
                seen_rules.add(rule)

by_temp_pass = defaultdict(int)
for r in passing:
    by_temp_pass[r["temperature"]] += 1

print("\n-- Biophysical Filter Summary ------------------------------------------")
print(f"  Unique input:         {len(unique_rows)}")
print(f"  Passing all filters:  {len(passing)}")
print(f"  Failing:              {len(failing)}")
print(f"\n  Top failure reasons (sequences failing each rule):")
for rule, cnt in sorted(fail_bucket.items(), key=lambda x: -x[1]):
    print(f"    {rule}: {cnt}")
print(f"\n  Passing by temperature:")
for t in sorted(by_temp_pass):
    print(f"    {t}: {by_temp_pass[t]}")

# -- write filtered CSV -------------------------------------------------------
filt_fields = fieldnames + ["filter_reasons"]
with open(FILT_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=filt_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(passing)
print(f"\nFiltered CSV written -> {FILT_CSV}")

# -- malformed report ---------------------------------------------------------
if malformed:
    print(f"\n-- Malformed / Skipped ({len(malformed)}) ----------------------------")
    for temp, fname, reason in malformed:
        print(f"  [{temp}] {fname}: {reason}")
else:
    print("\nNo malformed FASTA files.")
