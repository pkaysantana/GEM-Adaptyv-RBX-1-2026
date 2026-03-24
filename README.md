# GEM-Adaptyv RBX-1 Binder Design Competition 2026

## Competition Overview

**Target**: RBX-1 (RING-box protein 1) — E3 ubiquitin ligase, 108 AA, cancer-relevant target
**Goal**: Design up to 100 de novo protein binders; evaluated by wet-lab assays
**Prize**: $1,000 + scientific recognition + wet lab testing of top 300 designs
**Deadline**: 26 March 2026

## Current Status: Final Submission

**Primary submission**: `rbx1_final_primary_submission.csv`
- 25 validated binder sequences (55–76 AA)
- 18 unique RFdiffusion backbones
- All passed four-stage computational validation

**Reserve**: `rbx1_final_reserve_submission.csv` (5 additional candidates, not submitted)

## Design Pipeline

1. **RFdiffusion** — hotspot-conditioned backbone generation on RBX-1 (PDB 1LDJ)
2. **ProteinMPNN** — sequence design at 3 temperatures, ~1,500 candidates
3. **Biophysical filtering** — charge, hydrophobicity, repeats → 245 candidates
4. **ESMFold** — monomer pLDDT screening (>75) → 59 candidates
5. **Boltz-2** — complex interface screening (pair_iptm_AB > 0.65) → 25 candidates

Ranking: pair_iptm_AB (primary), monomer pLDDT (secondary), biophysical heuristics (tertiary). These are model-based prioritisation metrics, not experimental binding affinities.

## Repository Structure

```
Submission
  rbx1_final_primary_submission.csv     # Primary submission (25 sequences)
  rbx1_final_reserve_submission.csv     # Reserve candidates (5 sequences)
  method_description.md                 # 2-page method description
  COMPETITION_SUBMISSION_PACKAGE.md     # Package documentation
  SUBMISSION_NOTES.md                   # File map and notes

Validated Metrics
  rbx1_rfdiff_validated.csv             # Full metrics for 25 submitted designs
  rbx1_rfdiff_reserve.csv              # Reserve candidate metrics

Pipeline Intermediates
  rbx1_rfdiff_mpnn_v2.csv              # Raw MPNN output (~1,500 seqs)
  rbx1_rfdiff_mpnn_v2_filtered.csv     # Post-filter (245 seqs)
  rbx1_rfdiff_esmfold_v2_scores.csv    # ESMFold scores (59 seqs)
  rbx1_boltz_rfdiff_v2_batch1_scores.csv
  rbx1_boltz_rfdiff_v2_batch2_scores.csv

Target
  rbx1_sequence.fasta                   # RBX-1 target sequence
  target_analysis_summary.md            # Structure/function analysis
  targets/                              # PDB structures
  cleaned/                              # Processed structures

Scripts
  merge_and_select.py
  esmfold_validate.py
  extract_interface_complex.py

Legacy
  legacy_archive/                       # Obsolete files from earlier iterations
```

## Evaluation

Designs will be tested experimentally:
- SPR/BLI binding affinity
- Expression yield
- Thermal stability (Tm)

Computational scores (pLDDT, pair_iptm_AB) were used for prioritisation only.
