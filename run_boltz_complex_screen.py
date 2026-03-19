#!/usr/bin/env python3
"""
Boltz-2 complex validation for top RFdiffusion→ProteinMPNN binder candidates.

Chains:  A = RBX1 (target, 90 aa, chain B from PDB 1LDJ)
         B = binder (designed sequence)

Usage:
    python run_boltz_complex_screen.py                     # defaults
    python run_boltz_complex_screen.py --candidates a,b,c  # specific IDs
    python run_boltz_complex_screen.py --out-dir /tmp/out  # custom output root

Outputs (all relative to --out-dir, default = repo root):
    boltz_rfdiff_inputs/          one FASTA per candidate
    boltz_rfdiff_outputs/         Boltz predictions
    rbx1_boltz_complex_scores.csv ranked confidence summary

Key metrics:
    pair_iptm_AB   chain-A↔B iPTM  (primary interface metric, 0-1)
    iptm           overall interface TM-score
    protein_iptm   protein-only iPTM
    ptm            global TM-score
    complex_plddt  mean pLDDT over full complex
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────────────
RBX1_SEQ = (
    "KKRFEVKKWNAVALWAWDIVVDNCAICRNHIMDLCIECQANQASATSEECTVAWGVCNHAFHFHCISRWLK"
    "TRQVCPLDNREWEFQKY"
)

# Default candidates: top 5 from ESMFold monomer screen
DEFAULT_CANDIDATES = [
    # Tier-2 screen — backbone diversity across binder_31, binder_44, binder_15
    "rbx1_binder_31_T01_s2",   # best monomer pLDDT from binder_31 (89.0×)
    "rbx1_binder_31_T02_s2",   # cleanest min pLDDT in binder_31 (min=70), different temp
    "rbx1_binder_44_T02_s4",   # best of binder_44 backbone (distinct structure)
    "rbx1_binder_44_T03_s5",   # second binder_44 — covers backbone with two variants
    "rbx1_binder_15_T03_s1",   # unique binder_15 backbone, only representative
]

# Source of truth: the filtered ESMFold-scored CSV
ESMFOLD_CSV = Path(
    "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/"
    "GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_esmfold_scores.csv"
)

# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    repo_root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Boltz-2 complex screen for RBX1 binders")
    p.add_argument("--candidates", default=",".join(DEFAULT_CANDIDATES),
                   help="Comma-separated sequence IDs to validate")
    p.add_argument("--esmfold-csv", default=str(ESMFOLD_CSV),
                   help="CSV with binder sequences (rbx1_rfdiff_esmfold_scores.csv)")
    p.add_argument("--out-dir", default=str(repo_root),
                   help="Root directory for inputs/, outputs/, score CSV")
    p.add_argument("--recycling-steps", type=int, default=3)
    p.add_argument("--diffusion-samples", type=int, default=1)
    p.add_argument("--sampling-steps", type=int, default=200)
    p.add_argument("--override", action="store_true", default=True,
                   help="Re-run even if outputs exist")
    return p.parse_args()

# ── helpers ───────────────────────────────────────────────────────────────────
def find_boltz() -> str:
    """Resolve boltz binary: prefer protein-design env, fall back to PATH."""
    candidates = [
        "/home/on/miniforge3/envs/protein-design/bin/boltz",
        shutil.which("boltz"),
    ]
    for p in candidates:
        if p and Path(p).is_file() and os.access(p, os.X_OK):
            return p
    sys.exit("ERROR: boltz binary not found. Activate protein-design env or add to PATH.")

def load_sequences(csv_path: Path, wanted_ids: list[str]) -> dict[str, dict]:
    """Return {sequence_id: row_dict} for all wanted IDs."""
    found = {}
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            sid = row["sequence_id"]
            if sid in wanted_ids:
                found[sid] = row
    missing = set(wanted_ids) - set(found)
    if missing:
        sys.exit(f"ERROR: sequence IDs not found in {csv_path}:\n  {sorted(missing)}")
    return found

def safe_load_confidence(path: Path) -> dict | None:
    """Load confidence JSON; return None and warn on any parse error."""
    try:
        with path.open() as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print(f"  WARNING: unexpected JSON type in {path.name}")
            return None
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: could not parse {path}: {e}")
        return None

def extract_pair_iptm(conf: dict) -> float | None:
    """Extract chain-0 ↔ chain-1 iPTM from pair_chains_iptm."""
    pci = conf.get("pair_chains_iptm", {})
    try:
        return round(pci["0"]["1"], 4)
    except (KeyError, TypeError):
        return None

def find_confidence_json(out_root: Path, run_name: str, seq_id: str) -> Path | None:
    """Locate the confidence JSON with explicit path first, then fallback search."""
    expected = out_root / run_name / "predictions" / seq_id / f"confidence_{seq_id}_model_0.json"
    if expected.exists():
        return expected
    # Fallback: broader search
    matches = list(out_root.rglob(f"confidence_{seq_id}_model_0.json"))
    if len(matches) == 1:
        print(f"  NOTE: found {seq_id} via fallback search at {matches[0]}")
        return matches[0]
    if len(matches) > 1:
        print(f"  WARNING: multiple confidence files for {seq_id}; using first: {matches[0]}")
        return matches[0]
    return None

# ── main ──────────────────────────────────────────────────────────────────────
import os  # needed for os.access

def main():
    args = parse_args()
    candidate_ids = [c.strip() for c in args.candidates.split(",") if c.strip()]
    out_root      = Path(args.out_dir)
    input_dir     = out_root / "boltz_rfdiff_inputs"
    output_dir    = out_root / "boltz_rfdiff_outputs"
    score_csv     = out_root / "rbx1_boltz_complex_scores.csv"
    esmfold_csv   = Path(args.esmfold_csv)

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    boltz_bin = find_boltz()

    # ── step 1: load sequences from ESMFold CSV ───────────────────────────────
    print("=" * 60)
    print("STEP 1 — Loading sequences from ESMFold CSV")
    print("=" * 60)
    seqs = load_sequences(esmfold_csv, candidate_ids)
    print(f"  Loaded {len(seqs)} sequences from {esmfold_csv.name}")

    # ── step 2: write input FASTAs ────────────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 2 — Writing Boltz input FASTAs")
    print("=" * 60)
    for seq_id in candidate_ids:
        row = seqs[seq_id]
        binder_seq = row["binder_chain_sequence"]
        fasta_path = input_dir / f"{seq_id}.fasta"
        fasta_path.write_text(
            f">A|protein\n{RBX1_SEQ}\n"
            f">B|protein\n{binder_seq}\n"
        )
        print(f"  {fasta_path.name}  (RBX1={len(RBX1_SEQ)} aa, binder={len(binder_seq)} aa)")
    print(f"\n  {len(candidate_ids)} FASTAs written to {input_dir}")

    # ── step 3: run Boltz ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 3 — Running Boltz-2 complex prediction")
    print("=" * 60)
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
        print(f"\nWARNING: Boltz exited with code {result.returncode} — attempting to parse partial outputs")

    # ── step 4: parse confidence JSONs ────────────────────────────────────────
    print()
    print("=" * 60)
    print("STEP 4 — Parsing confidence scores")
    print("=" * 60)

    run_name = f"boltz_results_{input_dir.name}"
    rows = []

    for seq_id in candidate_ids:
        row = seqs[seq_id]
        binder_seq = row["binder_chain_sequence"]
        mono_plddt = float(row.get("mean_plddt", 0) or 0) * 100  # stored 0-1, convert

        conf_path = find_confidence_json(output_dir, run_name, seq_id)

        if conf_path is None:
            print(f"  MISSING output: {seq_id}")
            rows.append({
                "sequence_id":    seq_id,
                "backbone_id":    row.get("backbone_id", ""),
                "temperature":    row.get("temperature", ""),
                "binder_length":  len(binder_seq),
                "monomer_plddt":  round(mono_plddt, 1),
                "iptm":           None,
                "protein_iptm":   None,
                "pair_iptm_AB":   None,
                "ptm":            None,
                "complex_plddt":  None,
                "plddt_delta":    None,
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

        iptm          = round(conf.get("iptm",          0) or 0, 4)
        protein_iptm  = round(conf.get("protein_iptm",  0) or 0, 4)
        ptm           = round(conf.get("ptm",           0) or 0, 4)
        complex_plddt = round((conf.get("complex_plddt", 0) or 0) * 100, 2)  # 0-1 → 0-100
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
            "iptm":           iptm,
            "protein_iptm":   protein_iptm,
            "pair_iptm_AB":   pair_AB,
            "ptm":            ptm,
            "complex_plddt":  complex_plddt,
            "plddt_delta":    plddt_delta,
            "status":         "ok",
            "binder_chain_sequence": binder_seq,
        })

    # ── write CSV ─────────────────────────────────────────────────────────────
    fields = ["sequence_id", "backbone_id", "temperature", "binder_length",
              "monomer_plddt", "iptm", "protein_iptm", "pair_iptm_AB",
              "ptm", "complex_plddt", "plddt_delta", "status",
              "binder_chain_sequence"]
    with score_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n  Score CSV -> {score_csv}")

    # ── summary ───────────────────────────────────────────────────────────────
    ok = [r for r in rows if r["status"] == "ok" and r["pair_iptm_AB"] is not None]
    if not ok:
        print("\nNo successful predictions to summarise.")
        return

    print()
    print("=" * 60)
    print("RESULTS — ranked by pair_iptm_AB (chain interface quality)")
    print("=" * 60)
    hdr = (f"  {'sequence_id':<34} {'len':>4}  "
           f"{'pairAB':>7}  {'iPTM':>6}  {'prot_iPTM':>9}  "
           f"{'cPLDDT':>7}  {'mPLDDT':>7}  {'Δ':>5}  temp")
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    # Primary sort: pair_iptm_AB; secondary: iptm
    ranked = sorted(ok, key=lambda r: (-(r["pair_iptm_AB"] or 0), -(r["iptm"] or 0)))
    for r in ranked:
        pab = f"{r['pair_iptm_AB']:.3f}"
        d   = f"{r['plddt_delta']:+.1f}" if r["plddt_delta"] is not None else "  N/A"
        print(f"  {r['sequence_id']:<34} {r['binder_length']:>4}  "
              f"{pab:>7}  {r['iptm']:>6.3f}  {r['protein_iptm']:>9.3f}  "
              f"{r['complex_plddt']:>7.1f}  {r['monomer_plddt']:>7.1f}  "
              f"{d:>5}  {r['temperature']}")

    print()
    print("Interface thresholds (pair_iptm_AB):")
    for t, label in [(0.8, "excellent"), (0.6, "good"), (0.4, "marginal"), (0.2, "weak")]:
        n = sum(1 for r in ok if (r["pair_iptm_AB"] or 0) >= t)
        print(f"  >= {t:.1f} ({label:9s}): {n}/{len(ok)}")

    print()
    print("Selection decision (strict gate):")
    print("  PASS criteria: pair_iptm_AB >= 0.5, iptm >= 0.6, Δ pLDDT >= -10")
    passed, dropped = [], []
    for r in ranked:
        p_ab   = r["pair_iptm_AB"] or 0
        iptm   = r["iptm"] or 0
        delta  = r["plddt_delta"] if r["plddt_delta"] is not None else -999
        if p_ab >= 0.5 and iptm >= 0.6 and delta >= -10:
            passed.append(r)
            print(f"  PASS  {r['sequence_id']}  (pairAB={p_ab:.3f}  iPTM={iptm:.3f}  Δ={delta:+.1f})")
        else:
            reasons = []
            if p_ab < 0.5:   reasons.append(f"pairAB={p_ab:.3f}<0.5")
            if iptm < 0.6:   reasons.append(f"iPTM={iptm:.3f}<0.6")
            if delta < -10:  reasons.append(f"Δ={delta:+.1f}<-10")
            dropped.append(r)
            print(f"  DROP  {r['sequence_id']}  ({', '.join(reasons)})")

    print()
    print(f"  {len(passed)} PASS / {len(dropped)} DROP  (from {len(ok)} scored)")
    if passed:
        print("\nCandidates ready for submission merge:")
        for r in passed:
            print(f"  {r['sequence_id']}  pairAB={r['pair_iptm_AB']:.3f}  "
                  f"iPTM={r['iptm']:.3f}  cPLDDT={r['complex_plddt']:.1f}")


if __name__ == "__main__":
    main()
