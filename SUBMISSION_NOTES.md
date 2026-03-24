# RBX-1 Binder Design — Submission Notes

**Date**: 2026-03-24
**Competition**: GEM x Adaptyv RBX-1 Binder Design 2026
**Deadline**: 2026-03-26

## Submission File

- **Primary**: `rbx1_final_primary_submission.csv` (25 sequences)
- **Format**: CSV — `Name,Sequence`
- **Reserve**: `rbx1_final_reserve_submission.csv` (5 sequences, not submitted)

## Sequence Summary

- **Count**: 25 validated binders
- **Length range**: 55–76 AA
- **Unique backbones**: 18 RFdiffusion-generated scaffolds
- **All sequences**: standard 20 AA, no duplicates, no overlap with reserves

## Selection Pipeline

1. **Backbone generation**: RFdiffusion conditioned on RBX-1 hotspot residues (PDB 1LDJ)
2. **Sequence design**: ProteinMPNN at multiple temperatures (T01–T03)
3. **Biophysical filtering**: charge, hydrophobicity, repeat content
4. **Monomer screening**: ESMFold pLDDT (all > 75)
5. **Complex screening**: Boltz-2 interface prediction (pair_iptm_AB > 0.65)
6. **Final ranking**: by pair_iptm_AB (interface quality)

All 25 sequences passed every validation gate (boltz_gate = PASS).

## Backups

Timestamped backups created at `rbx1_final_*_backup_20260324_173252.csv`.

## Reserve File

5 additional candidates held back in `rbx1_final_reserve_submission.csv`.
These can be swapped in if any primary sequence is found to have issues.
