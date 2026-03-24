# Method Description: De Novo Protein Binder Design for RBX-1

## Target and Structural Basis

I designed protein binders targeting RBX-1 (RING-box protein 1), a RING domain E3 ubiquitin ligase component involved in cullin-RING ligase complexes implicated in cancer biology. All backbones were generated de novo by RFdiffusion (no motif scaffolding or lead optimisation from existing binders); I have not independently verified novelty by sequence search against UniRef50, but the designs are structurally novel by construction. My designs target the CUL1-interacting surface of RBX-1, using the crystal structure of the CUL1-RBX1 complex (PDB: 1LDJ, 2.4 A) as the structural template. I selected hotspot residues on RBX-1 at the native protein-protein interface to define the binding site for scaffold generation.

## Backbone Generation with RFdiffusion

I generated novel binder backbones using RFdiffusion (Watson et al., 2023) conditioned on RBX-1 hotspot residues at the CUL1 binding interface. Approximately 90 diverse backbone scaffolds were produced, spanning 55-76 residues in length. I ran RFdiffusion with hotspot-conditioned denoising to produce compact, helical binder geometries complementary to the RBX-1 surface. Backbone diversity was encouraged through variation in diffusion parameters.

## Sequence Design with ProteinMPNN

I threaded each backbone with multiple sequences using ProteinMPNN (Dauparas et al., 2022), sampling at three temperatures (T=0.1, T=0.2, T=0.3) with 5 sequence samples per backbone per temperature. This produced approximately 1,500 candidate binder sequences across all backbones. The multi-temperature strategy balances sequence confidence (low T) with sequence diversity (high T), increasing the probability of sampling experimentally viable sequences.

## Biophysical Filtering

I filtered candidate sequences using biophysical heuristics to remove designs unlikely to express or fold in vitro:

- **Net charge**: sequences with extreme net charge were removed
- **Hydrophobic content**: sequences with excessive hydrophobic fraction were filtered
- **Repeat content**: sequences containing long amino acid repeats or low-complexity regions were excluded
- **Length**: designs outside the 50-80 AA range were removed

This stage reduced the pool from ~1,500 to 245 sequences across 62 unique backbones.

## Monomer Structure Validation with ESMFold

I evaluated the 245 filtered sequences for foldability using ESMFold (Lin et al., 2023), predicting monomer structures and computing per-residue pLDDT confidence scores. Sequences with mean pLDDT below 75 were discarded, retaining 59 candidates confidently predicted to fold into the intended backbone topology. Mean monomer pLDDT across the final 25 submissions was 87.6 (range: 75.0-93.7).

## Complex Binding Validation with Boltz-2

I assessed remaining candidates for RBX-1 binding using Boltz-2 (Wohlwend et al., 2025) complex structure prediction. Each binder-RBX1 pair was modelled as a two-chain complex, and I extracted interface-level metrics:

- **pair_iptm_AB**: interface predicted TM-score between binder (chain A) and RBX-1 (chain B)
- **complex pLDDT**: confidence of the predicted complex structure
- **pLDDT delta**: change in binder confidence from monomer to complex context

Predictions were run in three batches (initial + v2 batch 1 + v2 batch 2) totalling 37 complex predictions. I gated candidates on pair_iptm_AB > 0.65, yielding 25 designs that passed all validation stages.

## Final Ranking and Selection

I ranked the 25 validated binders by pair_iptm_AB (interface quality). The final submission includes all 25 designs spanning 18 unique backbone scaffolds. An additional 5 reserve candidates were held separately. Key statistics of the submitted designs:

| Metric | Min | Mean | Max |
|--------|-----|------|-----|
| Binder length (AA) | 55 | 66 | 76 |
| Monomer pLDDT | 75.0 | 87.6 | 93.7 |
| pair_iptm_AB | 0.65 | 0.76 | 0.85 |

## Design Philosophy

I adopted a quality-over-quantity strategy, submitting 25 high-confidence designs rather than filling the 100-sequence quota with lower-quality candidates. Every submitted sequence passed a four-stage computational validation pipeline (biophysical filter, ESMFold monomer screen, Boltz-2 complex screen, interface quality ranking). This approach maximises the expected number of experimentally validated binders given the wet-lab evaluation criteria (SPR/BLI binding, expression yield, thermal stability).

## Software and Compute

- **RFdiffusion**: backbone generation (GPU: RTX 5070 Ti, WSL2/Ubuntu 24.04)
- **ProteinMPNN**: sequence design (GPU)
- **ESMFold**: monomer structure prediction (GPU)
- **Boltz-2**: complex structure prediction (GPU)
- **Python**: biophysical filtering and analysis scripts

## References

1. Watson et al. (2023). De novo design of protein structure and function with RFdiffusion. *Nature* 620, 1089-1100.
2. Dauparas et al. (2022). Robust deep learning-based protein sequence design using ProteinMPNN. *Science* 378, 49-56.
3. Lin et al. (2023). Evolutionary-scale prediction of atomic-level protein structure with a language model. *Science* 379, 1123-1130.
4. Wohlwend et al. (2025). Boltz-2: Towards Accurate and Efficient Biomolecular Structure Prediction. *bioRxiv*.
