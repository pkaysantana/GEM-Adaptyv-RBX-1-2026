"""
Build final submission CSVs from validated and reserve sets.

Format: Name,Sequence  (competition requirement)

Primary:  rbx1_final_primary_submission.csv   (25 validated)
Reserve:  rbx1_final_reserve_submission.csv   (5 reserve)

Ranking priority within primary:
  1. pair_iptm_AB (primary interface quality)
  2. iptm (secondary)
  3. complex_plddt (tertiary — structural quality in complex)
"""

import csv
from pathlib import Path

ROOT = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026")

VALIDATED_CSV = ROOT / "rbx1_rfdiff_validated.csv"
RESERVE_CSV   = ROOT / "rbx1_rfdiff_reserve.csv"
PRIMARY_OUT   = ROOT / "rbx1_final_primary_submission.csv"
RESERVE_OUT   = ROOT / "rbx1_final_reserve_submission.csv"

MAX_LEN = 250


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


# ── Load ──────────────────────────────────────────────────────────────────────
validated = load_csv(VALIDATED_CSV)
reserve   = load_csv(RESERVE_CSV)

# ── Validation checks ─────────────────────────────────────────────────────────
print("=" * 65)
print("VALIDATION CHECKS — primary (25 candidates)")
print("=" * 65)

errors = []

sequences  = [r["binder_chain_sequence"] for r in validated]
seq_ids    = [r["sequence_id"] for r in validated]

# Length check
for r in validated:
    seq = r["binder_chain_sequence"]
    if len(seq) > MAX_LEN:
        errors.append("LENGTH FAIL: %s  len=%d > %d" % (r["sequence_id"], len(seq), MAX_LEN))
    if len(seq) == 0:
        errors.append("EMPTY SEQ: %s" % r["sequence_id"])

# Duplicate sequence check
seen_seqs = {}
for r in validated:
    seq = r["binder_chain_sequence"]
    if seq in seen_seqs:
        errors.append("DUPLICATE SEQ: %s == %s" % (r["sequence_id"], seen_seqs[seq]))
    else:
        seen_seqs[seq] = r["sequence_id"]

# Duplicate ID check
seen_ids = {}
for r in validated:
    sid = r["sequence_id"]
    if sid in seen_ids:
        errors.append("DUPLICATE ID: %s" % sid)
    else:
        seen_ids[sid] = True

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print("  " + e)
    raise SystemExit("Fix errors before writing submission.")
else:
    print("  Total sequences : %d" % len(validated))
    print("  Length check    : ALL PASS (max=%d, limit=%d)" % (
        max(len(r["binder_chain_sequence"]) for r in validated), MAX_LEN))
    print("  Duplicate seqs  : NONE")
    print("  Duplicate IDs   : NONE")
    lens = sorted(len(r["binder_chain_sequence"]) for r in validated)
    print("  Length range    : %d – %d aa" % (lens[0], lens[-1]))
    print("  Length median   : %d aa" % lens[len(lens)//2])

# ── Sort by confidence priority ───────────────────────────────────────────────
def sort_key(r):
    pab  = float(r.get("pair_iptm_AB") or 0)
    iptm = float(r.get("iptm") or 0)
    cpld = float(r.get("complex_plddt") or 0)
    return (-pab, -iptm, -cpld)

ranked = sorted(validated, key=sort_key)

# ── Write primary submission ──────────────────────────────────────────────────
with open(PRIMARY_OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Name", "Sequence"])
    for r in ranked:
        w.writerow([r["sequence_id"], r["binder_chain_sequence"]])

print()
print("Primary submission written -> %s" % PRIMARY_OUT)

# ── Write reserve submission ──────────────────────────────────────────────────
# Sort reserve by pair_iptm_AB desc
reserve_sorted = sorted(reserve, key=lambda r: -float(r.get("pair_iptm_AB") or 0))

with open(RESERVE_OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Name", "Sequence"])
    for r in reserve_sorted:
        name = r["sequence_id"] + "_RESERVE"
        w.writerow([name, r["binder_chain_sequence"]])

print("Reserve submission written -> %s" % RESERVE_OUT)

# ── Full ranked list ──────────────────────────────────────────────────────────
print()
print("=" * 65)
print("PRIMARY SUBMISSION — full ranked list (25 sequences)")
print("=" * 65)
print("%-3s  %-34s  %7s  %6s  %7s  %4s  %s" % (
    "#", "Name", "pairAB", "iPTM", "cPLDDT", "len", "backbone"))
print("-" * 85)
for i, r in enumerate(ranked, 1):
    seq = r["binder_chain_sequence"]
    pab  = float(r.get("pair_iptm_AB") or 0)
    iptm = float(r.get("iptm") or 0)
    cpld = float(r.get("complex_plddt") or 0)
    print("%-3d  %-34s  %7.3f  %6.3f  %7.1f  %4d  %s" % (
        i, r["sequence_id"], pab, iptm, cpld,
        len(seq), r["backbone_id"]))

# ── Reserve list ──────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("RESERVE SUBMISSION — 5 sequences (NOT primary)")
print("=" * 65)
print("%-3s  %-34s  %7s  %6s  %s" % ("#","sequence_id","pairAB","iPTM","failure_reason"))
print("-" * 90)
for i, r in enumerate(reserve_sorted, 1):
    pab  = float(r.get("pair_iptm_AB") or 0)
    iptm = float(r.get("iptm") or 0)
    print("%-3d  %-34s  %7.3f  %6.3f  %s" % (
        i, r["sequence_id"], pab, iptm,
        r.get("failure_reason","")[:55]))

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("SUBMISSION SUMMARY")
print("=" * 65)
print("  Primary   : %d sequences  (ready to submit)" % len(ranked))
print("  Reserve   : %d sequences  (borderline — do not submit unless primary fails)" % len(reserve_sorted))
print("  Total     : %d" % (len(ranked) + len(reserve_sorted)))
print()
print("  Competition cap    : 100")
print("  Primary uses       : %d / 100 slots" % len(ranked))
print("  Slots remaining    : %d (intentionally left empty — quality over filler)" % (100 - len(ranked)))
print()
tiers = [(0.8,"excellent"),(0.7,"strong"),(0.6,"good")]
vals = [float(r.get("pair_iptm_AB") or 0) for r in ranked]
for t, label in tiers:
    print("  pairAB >= %.1f (%s): %d/%d" % (t, label, sum(1 for v in vals if v >= t), len(vals)))
