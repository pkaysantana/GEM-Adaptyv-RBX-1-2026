# Binder Design Tips

Practical guidance for RFdiffusion-based binder design campaigns.

## Hotspot Residue Selection

- Require at least ~3 hydrophobic residues at the binding site for viable binding
- Charged polar sites are difficult to bind -- deprioritize epitopes dominated by charged residues (ARG, LYS, ASP, GLU)
- Sites with nearby glycans are difficult -- glycans order upon binding, creating an energetic penalty
- Aromatic residues (PHE, TRP, TYR) make excellent hotspots due to their contribution to binding energy
- Recommend **3--6 hotspot residues** per design run
- The RFdiffusion model internally masks 80--100% of provided hotspots and expects more contacts than specified -- providing hotspots guides but does not strictly constrain the interface
- Run pilot runs (5--10 backbones) before committing to large-scale generation to verify hotspot quality

## Target Truncation for Large Proteins

RFdiffusion and downstream tools (including structure prediction) scale as O(N^2) with total residue count. Truncate large targets to reduce cost.

### Truncation Guidelines

- Preserve secondary structure -- do not cut in the middle of helices or sheets
- Minimize chain breaks
- Leave ~10 A of target protein on each side of the intended binding site
- Natural truncation points: flexible linkers between domains (e.g., multidomain extracellular proteins)
- Use structural visualization to identify suitable cut points
- Truncated targets are fully supported by RFdiffusion and Boltz-2

### When to Truncate

- Targets >500 residues: consider truncation for faster iteration
- Targets >1000 residues: strongly recommend truncation
- Targets >2000 residues: truncation is effectively required

## Design Scale Recommendations

### Standard Protocol

- Generate ~100 RFdiffusion backbones per target as a starting point
- 10 sequences per backbone per round (ProteinMPNN)
- Multiple temperature rounds per backbone (up to 10)
- Goal: accumulate enough valid designs passing all validation thresholds

### Large-Scale Protocol (literature reference)

- ~10,000 RFdiffusion backbones per target
- 2 sequences per backbone
- ~20,000 total designs screened
- Used when high experimental success rates are critical

### Scaling Heuristics

- For well-defined epitopes with good hydrophobic character: ~100 backbones may suffice
- For challenging targets (polar surfaces, flexible regions): increase to 500--1000 backbones
- Monitor the valid design rate after each round to decide whether to continue or adjust parameters

## Common Failure Modes

### No valid designs after multiple rounds

**Possible causes**:
- Poor epitope selection (too polar, glycosylated, disordered)
- Binder length mismatch with epitope span
- Hotspot residues too spread out or in unfavorable geometry

**Actions**:
- Re-examine epitope clusters -- try a different cluster
- Adjust binder length range (try longer binders for spread-out epitopes)
- Reduce hotspot count to give RFdiffusion more freedom
- Check if target needs truncation (large targets reduce prediction quality)

### Designs pass structure metrics but fail DockQ

**Possible causes**:
- Binder folds correctly but docks in wrong orientation
- Interface contacts differ from RFdiffusion design

**Actions**:
- Generate more backbones to increase interface diversity
- Lower temperature earlier (advance to round 2--3 faster)
- Verify hotspot residues are at the actual intended interface

### High duplicate rate in sequence generation

**Possible causes**:
- Temperature too low (sampling collapsed)
- Backbone geometry is highly constrained

**Actions**:
- This is expected at low temperatures (rounds 3+) -- normal convergence behavior
- If happening at round 1 (temperature 1.0): the backbone may have very few viable sequences. Try other backbones.

### Solubility filter rejects most designs

**Possible causes**:
- Backbone geometry produces hydrophobic-core-exposed sequences
- Binder is too small to bury its hydrophobic core

**Actions**:
- Increase binder length to allow proper hydrophobic core formation
- Try different backbones -- some geometries inherently produce more soluble designs
