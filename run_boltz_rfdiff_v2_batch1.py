#!/usr/bin/env python3
"""
Boltz-2 complex screening — RFdiffusion v2 batch 1.

18 candidates selected from rbx1_rfdiff_esmfold_v2_scores.csv.
Selection criteria:
  - Highest mean pLDDT
  - Backbone diversity (≤2 per backbone; exceptions noted)
  - All candidates pass: mean_pLDDT ≥ 70, min_pLDDT ≥ 55

Pass criteria (post-Boltz):
  pair_iptm_AB ≥ 0.50
  iptm         ≥ 0.60
  Δ pLDDT      ≥ -20.0

Output directories (separate from v1 run):
  boltz_rfdiff_v2_inputs/
  boltz_rfdiff_v2_outputs/
  rbx1_boltz_rfdiff_v2_batch1_scores.csv

NOTE: mean_plddt in v2 ESMFold CSV is already on 0-100 scale.
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── RBX1 target sequence (chain B from PDB 1LDJ, 87 aa) ─────────────────────
RBX1_SEQ = (
    "KKRFEVKKWNAVALWAWDIVVDNCAICRNHIMDLCIECQANQASATSEECTVAWGVCNHAFHFHCISRWLK"
    "TRQVCPLDNREWEFQKY"
)

# ── Batch 1 candidates (18 sequences, 15 unique backbones) ───────────────────
# Format: (sequence_id, backbone_id, mean_plddt, min_plddt, rationale)
BATCH1_CANDIDATES = [
    ("rbx1_binder_44_T01_s3", "rbx1_binder_44", 93.65, 83.0,
     "#1 overall; min=83 — exceptionally tight floor"),
    ("rbx1_binder_87_T01_s3", "rbx1_binder_87", 93.17, 73.0,
     "#2 overall; only passing sequence from bb87"),
    ("rbx1_binder_55_T01_s4", "rbx1_binder_55", 92.26, 77.0,
     "Top of bb55 — strongest multi-hit backbone (4 seqs ≥90, taking top 2)"),
    ("rbx1_binder_23_T01_s1", "rbx1_binder_23", 91.89, 78.0,
     "Top of bb23; s1 and s5 diverge at interface positions — both worth testing"),
    ("rbx1_binder_16_T01_s5", "rbx1_binder_16", 91.69, 83.0,
     "Sole bb16 representative; min=83 — excellent pLDDT floor"),
    ("rbx1_binder_55_T01_s2", "rbx1_binder_55", 91.66, 78.0,
     "2nd from bb55 — justified by cluster strength; adds sequence diversity within backbone"),
    ("rbx1_binder_15_T02_s3", "rbx1_binder_15", 91.54, 75.0,
     "T02 compact binder (57 aa); only T02 representative from bb15"),
    ("rbx1_binder_0_T02_s5",  "rbx1_binder_0",  91.38, 79.0,
     "T02 short binder (60 aa); adds temperature and length diversity"),
    ("rbx1_binder_63_T01_s1", "rbx1_binder_63", 91.35, 82.0,
     "bb63 — very short (55 aa), min=82; both bb63 seqs have high min, worth 2 slots"),
    ("rbx1_binder_28_T01_s5", "rbx1_binder_28", 91.32, 73.0,
     "Top of bb28 (57 aa); only representative in batch"),
    ("rbx1_binder_64_T01_s4", "rbx1_binder_64", 90.65, 82.0,
     "bb64 sole rep; min=82 — one of best floors in entire set"),
    ("rbx1_binder_11_T02_s2", "rbx1_binder_11", 90.36, 83.0,
     "T02; min=83 — highest min pLDDT in entire 55-sequence pool"),
    ("rbx1_binder_1_T02_s3",  "rbx1_binder_1",  90.35, 81.0,
     "T02 medium binder (72 aa); sole bb1 representative in batch"),
    ("rbx1_binder_23_T01_s5", "rbx1_binder_23", 90.51, 80.0,
     "2nd from bb23; sequence diverges from s1 in key N-terminal region"),
    ("rbx1_binder_63_T01_s2", "rbx1_binder_63", 89.67, 82.0,
     "2nd from bb63; min=82 matches s1 — both worth testing as shortest binders"),
    ("rbx1_binder_77_T01_s3", "rbx1_binder_77", 89.57, 83.0,
     "bb77 sole rep (56 aa); min=83 — tightest pLDDT distribution in batch"),
    ("rbx1_binder_61_T01_s4", "rbx1_binder_61", 89.27, 74.0,
     "bb61 sole rep (56 aa); second short-binder backbone in batch"),
    ("rbx1_binder_45_T01_s1", "rbx1_binder_45", 87.39, 80.0,
     "bb45 — adds backbone diversity; min=80, longest tail in pLDDT range"),
]

CANDIDATE_IDS = [c[0] for c in BATCH1_CANDIDATES]

# Thresholds
PASS_PAIR_IPTM = 0.50
PASS_IPTM      = 0.60
PASS_DELTA     = -20.0

# Source CSV (v2 — mean_plddt already on 0-100 scale)
ESMFOLD_V2_CSV = Path(
    "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/"
    "GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_esmfold_v2_scores.csv"
)


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    repo_root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=str(repo_root))
    p.add_argument("--recycling-steps",   type=int, default=3)
    p.add_argument("--diffusion-samples", type=int, default=1)
    p.add_argument("--sampling-steps",    type=int, default=200)
    p.add_argument("--override", action="store_true", default=True)
    return p.parse_args()


# ── helpers ───────────────────────────────────────────────────────────────────
def find_boltz() -> str:
    for p in ["/home/on/miniforge3/envs/protein-design/bin/boltz", shutil.which("boltz")]:
        if p and Path(p).is_file() and os.access(p, os.X_OK):
            return p
    sys.exit("ERROR: boltz binary not found.")


def load_sequences(csv_path: Path, wanted_ids: list) -> dict:
    found = {}
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            if row["sequence_id"] in wanted_ids:
                found[row["sequence_id"]] = row
    missing = set(wanted_ids) - set(found)
    if missing:
        sys.exit(f"ERROR: IDs not in {csv_path.name}:\n  {sorted(missing)}")
    return found


def safe_load_confidence(path: Path):
    try:
        with path.open() as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: could not parse {path}: {e}")
        return None


def extract_pair_iptm(conf: dict):
    pci = conf.get("pair_chains_iptm", {})
    try:
        return round(pci["0"]["1"], 4)
    except (KeyError, TypeError):
        return None


def find_confidence_json(out_root: Path, run_name: str, seq_id: str):
    expected = out_root / run_name / "predictions" / seq_id / f"confidence_{seq_id}_model_0.json"
    if expected.exists():
        return expected
    matches = list(out_root.rglob(f"confidence_{seq_id}_model_0.json"))
    if matches:
        if len(matches) > 1:
            print(f"  WARNING: multiple hits for {seq_id}, using first")
        return matches[0]
    return None


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    args     = parse_args()
    out_root = Path(args.out_dir)
    input_dir   = out_root / "boltz_rfdiff_v2_inputs"
    output_dir  = out_root / "boltz_rfdiff_v2_outputs"
    score_csv   = out_root / "rbx1_boltz_rfdiff_v2_batch1_scores.csv"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    boltz_bin = find_boltz()

    # ── STEP 1: print batch manifest ─────────────────────────────────────────
    print("=" * 70)
    print("BATCH 1 — RFdiffusion v2 Boltz complex screen")
    print(f"  {len(CANDIDATE_IDS)} candidates  |  15 unique backbones")
    print(f"  Pass: pair_iptm_AB ≥ {PASS_PAIR_IPTM}  |  iPTM ≥ {PASS_IPTM}  |  Δ pLDDT ≥ {PASS_DELTA}")
    print("=" * 70)
    print(f"\n{'#':<3} {'sequence_id':<34} {'bb':<18} {'mean':>6} {'min':>6} {'len':>4}  rationale")
    print("-" * 120)
    for i, (sid, bb, mean_p, min_p, rationale) in enumerate(BATCH1_CANDIDATES, 1):
        print(f"{i:<3} {sid:<34} {bb:<18} {mean_p:>6.1f} {min_p:>6.1f} "
              f"{'?':>4}  {rationale}")

    # ── STEP 2: load sequences ────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2 — Loading sequences from ESMFold v2 CSV")
    print(f"{'='*70}")
    seqs = load_sequences(ESMFOLD_V2_CSV, CANDIDATE_IDS)
    print(f"  Loaded {len(seqs)} sequences from {ESMFOLD_V2_CSV.name}")

    # ── STEP 3: write FASTAs ──────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — Writing Boltz input FASTAs")
    print(f"{'='*70}")
    for seq_id in CANDIDATE_IDS:
        row = seqs[seq_id]
        binder_seq = row["binder_chain_sequence"]
        fasta_path = input_dir / f"{seq_id}.fasta"
        fasta_path.write_text(
            f">A|protein\n{RBX1_SEQ}\n"
            f">B|protein\n{binder_seq}\n"
        )
        print(f"  {fasta_path.name}  (RBX1={len(RBX1_SEQ)} aa, binder={len(binder_seq)} aa)")
    print(f"\n  {len(CANDIDATE_IDS)} FASTAs written → {input_dir}")

    # ── STEP 4: run Boltz ─────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — Running Boltz-2 complex prediction")
    print(f"{'='*70}")
    cmd = [
        boltz_bin, "predict",
        str(input_dir),
        "--out_dir",           str(output_dir),
        "--accelerator",       "gpu",
        "--model",             "boltz2",
        "--recycling_steps",   str(args.recycling_steps),
        "--sampling_steps",    str(args.sampling_steps),
        "--diffusion_samples", str(args.diffusion_samples),
        "--output_format",     "pdb",
        "--use_msa_server",
        "--no_kernels",
    ]
    if args.override:
        cmd.append("--override")

    print("CMD:", " ".join(cmd))
    print()
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"\nWARNING: Boltz exited {result.returncode} — attempting partial parse")

    # ── STEP 5: parse confidence JSONs ────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — Parsing confidence scores")
    print(f"{'='*70}")

    run_name = f"boltz_results_{input_dir.name}"
    rows = []

    for seq_id in CANDIDATE_IDS:
        row = seqs[seq_id]
        binder_seq = row["binder_chain_sequence"]
        # v2 CSV: mean_plddt already 0-100
        mono_plddt = float(row.get("mean_plddt", 0) or 0)

        conf_path = find_confidence_json(output_dir, run_name, seq_id)

        if conf_path is None:
            print(f"  MISSING: {seq_id}")
            rows.append({
                "sequence_id":    seq_id,
                "backbone_id":    row.get("backbone_id", ""),
                "temperature":    row.get("temperature", ""),
                "binder_length":  len(binder_seq),
                "monomer_plddt":  round(mono_plddt, 1),
                "iptm":           None, "protein_iptm": None,
                "pair_iptm_AB":   None, "ptm": None,
                "complex_plddt":  None, "plddt_delta": None,
                "status":         "missing",
                "binder_chain_sequence": binder_seq,
            })
            continue

        conf = safe_load_confidence(conf_path)
        if conf is None:
            rows.append({
                "sequence_id": seq_id, "backbone_id": row.get("backbone_id", ""),
                "temperature": row.get("temperature", ""), "binder_length": len(binder_seq),
                "monomer_plddt": round(mono_plddt, 1),
                "iptm": None, "protein_iptm": None, "pair_iptm_AB": None,
                "ptm": None, "complex_plddt": None, "plddt_delta": None,
                "status": "parse_error", "binder_chain_sequence": binder_seq,
            })
            continue

        iptm          = round(conf.get("iptm",         0) or 0, 4)
        protein_iptm  = round(conf.get("protein_iptm", 0) or 0, 4)
        ptm           = round(conf.get("ptm",          0) or 0, 4)
        # complex_plddt from Boltz is 0-1
        complex_plddt = round((conf.get("complex_plddt", 0) or 0) * 100, 2)
        pair_AB       = extract_pair_iptm(conf)
        plddt_delta   = round(complex_plddt - mono_plddt, 1) if mono_plddt else None

        print(f"  {seq_id}")
        print(f"    pair_iptm_AB={pair_AB}  iptm={iptm:.3f}  protein_iptm={protein_iptm:.3f}")
        print(f"    ptm={ptm:.3f}  complex_pLDDT={complex_plddt:.1f}  "
              f"monomer_pLDDT={mono_plddt:.1f}  Δ={plddt_delta:+.1f}")

        rows.append({
            "sequence_id":    seq_id,
            "backbone_id":    row.get("backbone_id", ""),
            "temperature":    row.get("temperature", ""),
            "binder_length":  len(binder_seq),
            "monomer_plddt":  round(mono_plddt, 1),
            "iptm":           iptm, "protein_iptm": protein_iptm,
            "pair_iptm_AB":   pair_AB, "ptm": ptm,
            "complex_plddt":  complex_plddt, "plddt_delta": plddt_delta,
            "status":         "ok",
            "binder_chain_sequence": binder_seq,
        })

    # ── write CSV ─────────────────────────────────────────────────────────────
    fields = ["sequence_id", "backbone_id", "temperature", "binder_length",
              "monomer_plddt", "iptm", "protein_iptm", "pair_iptm_AB",
              "ptm", "complex_plddt", "plddt_delta", "status",
              "binder_chain_sequence"]
    with score_csv.open("w", newline="") as fh:
        csv.DictWriter(fh, fieldnames=fields).writeheader()
        csv.DictWriter(fh, fieldnames=fields).writerows(rows)
    print(f"\n  Score CSV → {score_csv}")

    # ── STEP 6: results table ─────────────────────────────────────────────────
    ok = [r for r in rows if r["status"] == "ok" and r["pair_iptm_AB"] is not None]
    if not ok:
        print("\nNo successful predictions to summarise.")
        return

    ranked = sorted(ok, key=lambda r: (-(r["pair_iptm_AB"] or 0), -(r["iptm"] or 0)))

    print(f"\n{'='*70}")
    print("RESULTS — ranked by pair_iptm_AB")
    print(f"{'='*70}")
    hdr = (f"  {'sequence_id':<34} {'len':>4}  "
           f"{'pairAB':>7}  {'iPTM':>6}  {'prot_iPTM':>9}  "
           f"{'cPLDDT':>7}  {'mPLDDT':>7}  {'Δ':>6}  temp")
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))
    for r in ranked:
        d = f"{r['plddt_delta']:+.1f}" if r["plddt_delta"] is not None else "  N/A"
        print(f"  {r['sequence_id']:<34} {r['binder_length']:>4}  "
              f"{r['pair_iptm_AB']:>7.3f}  {r['iptm']:>6.3f}  {r['protein_iptm']:>9.3f}  "
              f"{r['complex_plddt']:>7.1f}  {r['monomer_plddt']:>7.1f}  "
              f"{d:>6}  {r['temperature']}")

    print()
    print("Interface tier distribution (pair_iptm_AB):")
    for t, label in [(0.8, "excellent"), (0.6, "good"), (0.5, "pass"), (0.4, "marginal")]:
        n = sum(1 for r in ok if (r["pair_iptm_AB"] or 0) >= t)
        print(f"  >= {t:.1f} ({label:9s}): {n}/{len(ok)}")

    print()
    print(f"Selection gate: pair_iptm_AB ≥ {PASS_PAIR_IPTM}  |  "
          f"iPTM ≥ {PASS_IPTM}  |  Δ pLDDT ≥ {PASS_DELTA}")
    print()
    passed, dropped = [], []
    for r in ranked:
        p_ab  = r["pair_iptm_AB"] or 0
        it    = r["iptm"] or 0
        delta = r["plddt_delta"] if r["plddt_delta"] is not None else -999
        if p_ab >= PASS_PAIR_IPTM and it >= PASS_IPTM and delta >= PASS_DELTA:
            passed.append(r)
            print(f"  PASS  {r['sequence_id']}  "
                  f"pairAB={p_ab:.3f}  iPTM={it:.3f}  Δ={delta:+.1f}")
        else:
            reasons = []
            if p_ab  < PASS_PAIR_IPTM: reasons.append(f"pairAB={p_ab:.3f}<{PASS_PAIR_IPTM}")
            if it    < PASS_IPTM:      reasons.append(f"iPTM={it:.3f}<{PASS_IPTM}")
            if delta < PASS_DELTA:     reasons.append(f"Δ={delta:+.1f}<{PASS_DELTA}")
            dropped.append(r)
            print(f"  DROP  {r['sequence_id']}  ({', '.join(reasons)})")

    print()
    print(f"  {len(passed)} PASS  /  {len(dropped)} DROP  /  "
          f"{len(rows)-len(ok)} missing  (from {len(rows)} candidates)")

    if passed:
        print("\nCandidates ready for review (do NOT add to submission yet):")
        for r in passed:
            print(f"  {r['sequence_id']}  "
                  f"pairAB={r['pair_iptm_AB']:.3f}  iPTM={r['iptm']:.3f}  "
                  f"cPLDDT={r['complex_plddt']:.1f}  len={r['binder_length']}")


if __name__ == "__main__":
    main()
