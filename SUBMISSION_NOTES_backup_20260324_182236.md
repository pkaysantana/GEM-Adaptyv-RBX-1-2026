# RBX-1 Binder Design — Submission Notes

**Date**: 2026-03-24
**Competition**: GEM x Adaptyv RBX-1 Binder Design 2026
**Deadline**: 2026-03-26

## Submission Summary

- **Sequences submitted**: 25
- **Unique backbones**: 18 RFdiffusion-generated scaffolds
- **Length range**: 55–76 AA
- **All sequences**: standard 20 AA, no duplicates

## Selection Pipeline

1. RFdiffusion backbone generation conditioned on RBX-1 hotspot residues (PDB 1LDJ)
2. ProteinMPNN sequence design at 3 temperatures, 5 samples each (~1,500 candidates)
3. Biophysical filtering: charge, hydrophobicity, repeats, length (245 pass)
4. ESMFold monomer screening: pLDDT > 75 (59 pass)
5. Boltz-2 complex screening: pair_iptm_AB > 0.65 (25 pass)

## Ranking

Primary: pair_iptm_AB (Boltz-2 interface confidence). Secondary: monomer pLDDT, biophysical heuristics. These are model-based prioritisation metrics, not experimental affinities.

## File Map

| File | Role |
|------|------|
| `rbx1_final_primary_submission.csv` | **Primary submission** — 25 sequences, `Name,Sequence` |
| `rbx1_final_reserve_submission.csv` | **Reserve** — 5 additional candidates, not submitted |
| `method_description.md` | 2-page method description for competition |
| `rbx1_rfdiff_validated.csv` | Full metric table for all 25 validated designs |
| `COMPETITION_SUBMISSION_PACKAGE.md` | Submission package documentation |

## Pipeline Intermediate Files (retained for provenance)

| File | Contents |
|------|----------|
| `rbx1_rfdiff_mpnn_v2.csv` | Raw MPNN output (~1,500 sequences) |
| `rbx1_rfdiff_mpnn_v2_filtered.csv` | Post-biophysical filter (245 sequences) |
| `rbx1_rfdiff_esmfold_v2_scores.csv` | ESMFold monomer scores (59 sequences) |
| `rbx1_boltz_rfdiff_v2_batch1_scores.csv` | Boltz-2 batch 1 complex scores |
| `rbx1_boltz_rfdiff_v2_batch2_scores.csv` | Boltz-2 batch 2 complex scores |
| `rbx1_rfdiff_reserve.csv` | Reserve candidate metrics |

## Legacy Files

All obsolete files from earlier pipeline iterations (100-sequence heuristic submissions, old scoring files, outdated strategy docs) have been moved to `legacy_archive/`.

## Backups

Timestamped backups: `rbx1_final_*_backup_20260324_173252.csv`
