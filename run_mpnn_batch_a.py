#!/usr/bin/env python3
"""
ProteinMPNN on RFdiffusion Batch A backbones.

Reads:   /home/on/rfdiff_outputs_v2/         (100 PDBs from Batch A)
Writes:  /home/on/mpnn_on_rfdiff_v2/         (MPNN outputs)
         rbx1_rfdiff_mpnn_v2.csv             (all raw sequences)
         rbx1_rfdiff_mpnn_v2_filtered.csv    (biophysically passing)

Does NOT merge with old submission or any previous CSV.
Chain convention: A = binder (design), B = RBX1 (fixed).
Temperatures: 0.1, 0.2, 0.3 x 5 seqs = 15 per backbone -> 1500 raw.
Skips any temperature whose seqs/ directory already has one FASTA per backbone.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────
PYTHON      = "/home/on/miniforge3/envs/protein-design/bin/python"
RFDIFF_OUT  = Path("/home/on/rfdiff_outputs_v2")
MPNN_DIR    = Path("/home/on/ProteinMPNN")
MPNN_SCRIPT = MPNN_DIR / "protein_mpnn_run.py"
MPNN_HELPER = MPNN_DIR / "helper_scripts"
MPNN_OUT    = Path("/home/on/mpnn_on_rfdiff_v2")

PROJECT     = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026")
RAW_CSV     = PROJECT / "rbx1_rfdiff_mpnn_v2.csv"
FILT_CSV    = PROJECT / "rbx1_rfdiff_mpnn_v2_filtered.csv"

TEMPS            = [0.1, 0.2, 0.3]
N_PER_TEMP       = 5
EXPECTED_BACKBONES = 100


def flush(msg: str) -> None:
    print(msg, flush=True)


# ── biophysical filter ────────────────────────────────────────────────────────
def is_sane(seq: str) -> tuple[bool, list[str]]:
    n = len(seq)
    reasons: list[str] = []

    if n < 50 or n > 80:
        reasons.append(f"length={n}")

    if n > 0 and max(seq.count(aa) for aa in "ACDEFGHIKLMNPQRSTVWY") / n > 0.20:
        reasons.append("single_aa_dominance>20%")

    charged_pos = ((seq.count("R") + seq.count("K")) / n) if n > 0 else 0.0
    if charged_pos > 0.25:
        reasons.append(f"pos_charge={charged_pos:.2f}")

    aromatic = ((seq.count("F") + seq.count("W") + seq.count("Y")) / n) if n > 0 else 0.0
    if aromatic > 0.25:
        reasons.append(f"aromatic={aromatic:.2f}")

    net = (seq.count("K") + seq.count("R")) - (seq.count("D") + seq.count("E"))
    if abs(net) > 8:
        reasons.append(f"net_charge={net}")

    pro_frac = (seq.count("P") / n) if n > 0 else 0.0
    if pro_frac > 0.12:
        reasons.append(f"pro_frac={pro_frac:.2f}")

    return (len(reasons) == 0), reasons


# ── helpers ───────────────────────────────────────────────────────────────────
def find_backbone_pdbs() -> list[Path]:
    pdb_files = sorted(
        RFDIFF_OUT.glob("rbx1_binder_*.pdb"),
        key=lambda p: int(p.stem.split("_")[-1]),
    )
    flush(f"Found {len(pdb_files)} Batch A backbone PDBs in {RFDIFF_OUT}")

    if not pdb_files:
        sys.exit("ERROR: No PDBs found.")

    if len(pdb_files) != EXPECTED_BACKBONES:
        flush(
            f"WARNING: expected {EXPECTED_BACKBONES} backbones, found {len(pdb_files)}. "
            "Using discovered count."
        )

    return pdb_files


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        sys.exit(f"{label} failed:\n{stderr[-500:]}")


def ensure_jsonl_files() -> tuple[Path, Path]:
    parsed_jsonl = MPNN_OUT / "parsed_pdbs.jsonl"
    chain_jsonl  = MPNN_OUT / "chain_fix.jsonl"

    if parsed_jsonl.exists() and chain_jsonl.exists():
        flush("\nStep 1+2: JSONL files already exist — skipping rebuild.")
        flush(f"  -> {parsed_jsonl}")
        flush(f"  -> {chain_jsonl}")
        return parsed_jsonl, chain_jsonl

    flush("\nStep 1: Parsing PDBs to JSONL...")
    run_checked(
        [
            PYTHON,
            str(MPNN_HELPER / "parse_multiple_chains.py"),
            "--input_path",  str(RFDIFF_OUT),
            "--output_path", str(parsed_jsonl),
        ],
        "parse_multiple_chains",
    )
    flush(f"  -> {parsed_jsonl}")

    flush("Step 2: Assigning fixed chains (B = RBX1)...")
    run_checked(
        [
            PYTHON,
            str(MPNN_HELPER / "assign_fixed_chains.py"),
            "--input_path",  str(parsed_jsonl),
            "--output_path", str(chain_jsonl),
            "--chain_list",  "A",
        ],
        "assign_fixed_chains",
    )
    flush(f"  -> {chain_jsonl}")

    return parsed_jsonl, chain_jsonl


def temp_tag(temp: float) -> str:
    return f"T{str(temp).replace('.', '')}"


def run_mpnn_temperature(
    temp: float,
    parsed_jsonl: Path,
    chain_jsonl: Path,
    expected_fastas: int,
) -> None:
    tag      = temp_tag(temp)
    out_dir  = MPNN_OUT / tag
    seqs_dir = out_dir / "seqs"
    out_dir.mkdir(parents=True, exist_ok=True)

    existing_fastas = sorted(seqs_dir.glob("*.fa")) if seqs_dir.exists() else []
    if len(existing_fastas) >= expected_fastas:
        flush(f"  T={temp} ({tag}): already complete ({len(existing_fastas)} FASTAs) — skipping.")
        return

    flush(f"  T={temp} ({tag}): running MPNN...")
    result = subprocess.run(
        [
            PYTHON,
            str(MPNN_SCRIPT),
            "--jsonl_path",         str(parsed_jsonl),
            "--chain_id_jsonl",     str(chain_jsonl),
            "--out_folder",         str(out_dir),
            "--num_seq_per_target", str(N_PER_TEMP),
            "--sampling_temp",      str(temp),
            "--batch_size",         "1",
            "--model_name",         "v_48_020",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        flush(f"  T={temp} ({tag}) ERROR: {stderr[-400:]}")
        return

    done_fastas = len(list(seqs_dir.glob("*.fa"))) if seqs_dir.exists() else 0
    flush(f"  T={temp} ({tag}): done — {done_fastas} FASTA files written.")


def extract_score(header: str) -> float:
    for tok in header.split(","):
        tok = tok.strip()
        if tok.startswith("score="):
            try:
                return float(tok.split("=", 1)[1])
            except ValueError:
                return 0.0
    return 0.0


def extract_sample_number(header: str) -> int:
    for tok in header.split(","):
        tok = tok.strip()
        if tok.startswith("sample="):
            try:
                return int(tok.split("=", 1)[1])
            except ValueError:
                return 0
    return 0


def emit_record(
    bucket: list[dict],
    backbone_id: str,
    tag: str,
    header: str,
    seq_parts: list[str],
) -> None:
    if not header or not seq_parts:
        return
    raw    = "".join(seq_parts)
    binder = raw.split("/")[0]  # chain A is first slash-delimited segment
    bucket.append(
        {
            "backbone_id":           backbone_id,
            "temperature":           tag,
            "binder_chain_sequence": binder,
            "binder_length":         len(binder),
            "mpnn_score":            round(extract_score(header), 4),
            "sample_number":         extract_sample_number(header),
        }
    )


def parse_temperature_fastas(temp: float) -> list[dict]:
    tag      = temp_tag(temp)
    seqs_dir = MPNN_OUT / tag / "seqs"

    if not seqs_dir.exists():
        flush(f"  {tag}: seqs/ not found — skipping.")
        return []

    records: list[dict] = []
    fasta_files = sorted(seqs_dir.glob("*.fa"))

    for fa in fasta_files:
        backbone_id = fa.stem
        header      = ""
        seq_parts: list[str] = []

        for line in fa.read_text().splitlines():
            if line.startswith(">"):
                emit_record(records, backbone_id, tag, header, seq_parts)
                header    = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.strip())

        emit_record(records, backbone_id, tag, header, seq_parts)  # flush last record

    flush(f"  {tag}: parsed {len(records)} sequences from {len(fasta_files)} FASTA files")
    return records


def write_raw_csv(rows: list[dict]) -> None:
    fields = [
        "backbone_id",
        "temperature",
        "binder_length",
        "mpnn_score",
        "sample_number",
        "binder_chain_sequence",
    ]
    with RAW_CSV.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    flush(f"Raw CSV -> {RAW_CSV}  ({len(rows)} sequences)")


def write_filtered_csv(rows: list[dict]) -> None:
    filt_fields = [
        "sequence_id",
        "backbone_id",
        "temperature",
        "binder_length",
        "mpnn_score",
        "sample_number",
        "filter_reasons",
        "binder_chain_sequence",
    ]
    with FILT_CSV.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=filt_fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["sequence_id"] = (
                f"{row['backbone_id']}_{row['temperature']}_s{row['sample_number']}"
            )
            writer.writerow(out)
    flush(f"Filtered CSV -> {FILT_CSV}  ({len(rows)} sequences)")


def main() -> None:
    pdb_files      = find_backbone_pdbs()
    expected_fastas = len(pdb_files)

    MPNN_OUT.mkdir(parents=True, exist_ok=True)

    parsed_jsonl, chain_jsonl = ensure_jsonl_files()

    flush("\nStep 3: Running ProteinMPNN...")
    for temp in TEMPS:
        run_mpnn_temperature(temp, parsed_jsonl, chain_jsonl, expected_fastas)

    flush("\nStep 4: Parsing FASTA outputs...")
    all_seqs: list[dict] = []
    for temp in TEMPS:
        all_seqs.extend(parse_temperature_fastas(temp))

    flush(f"\nTotal raw sequences collected: {len(all_seqs)}")
    write_raw_csv(all_seqs)

    flush("\nStep 5: Biophysical filter...")
    passed: list[dict] = []
    failed: list[dict] = []

    for seq_row in all_seqs:
        ok, reasons = is_sane(str(seq_row["binder_chain_sequence"]))
        row = {
            **seq_row,
            "filter_reasons": "PASS" if ok else "|".join(reasons),
        }
        (passed if ok else failed).append(row)

    total     = len(all_seqs)
    pass_rate = (len(passed) / total * 100.0) if total else 0.0
    flush(f"  Pass: {len(passed)}  Fail: {len(failed)}  ({pass_rate:.1f}% pass rate)")

    by_temp = Counter(str(s["temperature"]) for s in passed)
    flush(f"  By temperature: {dict(sorted(by_temp.items()))}")

    lens = [int(s["binder_length"]) for s in passed]
    if lens:
        flush(f"  Length: min={min(lens)}  max={max(lens)}  mean={sum(lens)/len(lens):.1f}")

    by_backbone = Counter(str(s["backbone_id"]) for s in passed)
    flush(f"  Distinct backbones with >=1 passing sequence: {len(by_backbone)}")

    write_filtered_csv(passed)
    flush("\nDone. Next: run_esmfold_screen.py pointed at rbx1_rfdiff_mpnn_v2_filtered.csv")


if __name__ == "__main__":
    main()
