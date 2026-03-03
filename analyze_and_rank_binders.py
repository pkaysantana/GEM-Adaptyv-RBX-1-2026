#!/usr/bin/env python3
"""
Analyze and rank RBX-1 binder sequences for optimal competition submission
"""

import csv
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import re

def load_sequences(csv_file: str) -> List[Tuple[str, str]]:
    """Load sequences from CSV file"""
    sequences = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sequences.append((row['Name'], row['Sequence']))
    return sequences

def calculate_binding_score(sequence: str) -> float:
    """Calculate predicted binding potential based on sequence features"""

    # Aromatic content (important for protein-protein interactions)
    aromatic_count = sum(sequence.count(aa) for aa in 'FWY')
    aromatic_fraction = aromatic_count / len(sequence)

    # Hydrophobic content (important for binding interfaces)
    hydrophobic_count = sum(sequence.count(aa) for aa in 'AILMFWYV')
    hydrophobic_fraction = hydrophobic_count / len(sequence)

    # Charged residues (can form salt bridges)
    positive_count = sum(sequence.count(aa) for aa in 'KR')
    negative_count = sum(sequence.count(aa) for aa in 'DE')
    charge_balance = min(positive_count, negative_count) / len(sequence)

    # Binding motifs (simple pattern matching)
    motif_score = 0
    binding_motifs = ['WGF', 'RKD', 'HSH', 'DXE', 'FWY', 'HXH']
    for motif in binding_motifs:
        if motif in sequence:
            motif_score += 1
        elif motif.replace('X', '.') and re.search(motif.replace('X', '.'), sequence):
            motif_score += 0.5

    # Combine scores
    binding_score = (
        aromatic_fraction * 2.0 +          # Weight: 2.0
        hydrophobic_fraction * 1.5 +       # Weight: 1.5
        charge_balance * 1.0 +              # Weight: 1.0
        motif_score * 0.5                   # Weight: 0.5
    )

    return binding_score

def calculate_druggability_score(sequence: str) -> float:
    """Calculate predicted druggability (solubility, aggregation resistance)"""

    length = len(sequence)

    # Length penalty (very long or very short proteins are problematic)
    if length < 50:
        length_score = 0.8
    elif length > 80:
        length_score = 0.9
    else:
        length_score = 1.0

    # Charge score (moderate positive charge is good for solubility)
    net_charge = sum(sequence.count(aa) for aa in 'KR') - sum(sequence.count(aa) for aa in 'DE')
    if -2 <= net_charge <= 4:
        charge_score = 1.0
    else:
        charge_score = 0.7

    # Aggregation resistance (avoid too many hydrophobic residues in a row)
    aggregation_score = 1.0
    hydrophobic_runs = re.findall(r'[AILMFWYV]{4,}', sequence)
    if hydrophobic_runs:
        aggregation_score = max(0.5, 1.0 - len(hydrophobic_runs) * 0.2)

    # Avoid problematic sequences
    problematic_score = 1.0
    if 'PPP' in sequence:  # Too many prolines
        problematic_score *= 0.8
    if sequence.count('C') > 4:  # Too many cysteines
        problematic_score *= 0.9
    if sequence.count('M') > 3:  # Too many methionines
        problematic_score *= 0.95

    druggability_score = length_score * charge_score * aggregation_score * problematic_score

    return druggability_score

def calculate_structural_score(sequence: str) -> float:
    """Calculate predicted structural quality"""

    length = len(sequence)

    # Secondary structure content prediction (very basic)
    helix_formers = sum(sequence.count(aa) for aa in 'AEDKRL')
    sheet_formers = sum(sequence.count(aa) for aa in 'VIFYWTM')
    loop_formers = sum(sequence.count(aa) for aa in 'GNPSTQ')

    helix_fraction = helix_formers / length
    sheet_fraction = sheet_formers / length
    loop_fraction = loop_formers / length

    # Balance of secondary structures (not too much of any one type)
    ss_balance = 1.0 - abs(max(helix_fraction, sheet_fraction, loop_fraction) - 0.5)

    # Avoid glycine-rich regions (can be too flexible)
    glycine_content = sequence.count('G') / length
    if glycine_content > 0.15:
        flexibility_penalty = 0.8
    else:
        flexibility_penalty = 1.0

    # Proline content (moderate amounts are good for structure)
    proline_content = sequence.count('P') / length
    if 0.05 <= proline_content <= 0.1:
        proline_score = 1.0
    else:
        proline_score = 0.9

    structural_score = ss_balance * flexibility_penalty * proline_score

    return structural_score

def calculate_diversity_contribution(sequence: str, existing_sequences: List[str]) -> float:
    """Calculate how much diversity this sequence adds to the selection"""

    if not existing_sequences:
        return 1.0

    # Simple diversity metric based on amino acid composition
    aa_composition = np.array([sequence.count(aa) / len(sequence) for aa in 'ACDEFGHIKLMNPQRSTVWY'])

    min_distance = float('inf')
    for existing_seq in existing_sequences:
        existing_composition = np.array([existing_seq.count(aa) / len(existing_seq) for aa in 'ACDEFGHIKLMNPQRSTVWY'])
        distance = np.linalg.norm(aa_composition - existing_composition)
        min_distance = min(min_distance, distance)

    # Normalize distance to 0-1 range
    diversity_score = min(1.0, min_distance * 5)  # Scale factor of 5

    return diversity_score

def calculate_novelty_score(sequence: str) -> float:
    """Calculate novelty score (avoiding similarity to known proteins)"""

    # This is a simplified version - in practice you'd compare against UniRef50
    # For now, we'll use some heuristics

    # Avoid common protein domains (simplified)
    common_motifs = ['DEAD', 'HERC', 'RING', 'WD40', 'EF-hand']
    novelty_penalty = 0
    for motif in common_motifs:
        if motif in sequence:
            novelty_penalty += 0.1

    # Prefer unique amino acid compositions
    aa_counts = [sequence.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY']
    aa_diversity = len([c for c in aa_counts if c > 0])  # Number of different AAs used

    diversity_bonus = min(0.3, aa_diversity / 20 * 0.3)

    novelty_score = max(0.5, 1.0 - novelty_penalty + diversity_bonus)

    return novelty_score

def rank_sequences(sequences: List[Tuple[str, str]]) -> List[Tuple[str, str, float, Dict]]:
    """Rank sequences based on composite scoring"""

    ranked_sequences = []
    selected_sequences = []  # For diversity calculation

    for name, sequence in sequences:
        # Calculate individual scores
        binding_score = calculate_binding_score(sequence)
        druggability_score = calculate_druggability_score(sequence)
        structural_score = calculate_structural_score(sequence)
        diversity_score = calculate_diversity_contribution(sequence, selected_sequences)
        novelty_score = calculate_novelty_score(sequence)

        # Composite score (weighted combination)
        weights = {
            'binding': 0.35,
            'druggability': 0.25,
            'structural': 0.20,
            'diversity': 0.15,
            'novelty': 0.05
        }

        composite_score = (
            binding_score * weights['binding'] +
            druggability_score * weights['druggability'] +
            structural_score * weights['structural'] +
            diversity_score * weights['diversity'] +
            novelty_score * weights['novelty']
        )

        scores_dict = {
            'binding': binding_score,
            'druggability': druggability_score,
            'structural': structural_score,
            'diversity': diversity_score,
            'novelty': novelty_score,
            'composite': composite_score
        }

        ranked_sequences.append((name, sequence, composite_score, scores_dict))

        # Add to selected sequences for diversity calculation
        if len(selected_sequences) < 50:  # Limit for efficiency
            selected_sequences.append(sequence)

    # Sort by composite score (descending)
    ranked_sequences.sort(key=lambda x: x[2], reverse=True)

    return ranked_sequences

def optimize_final_selection(ranked_sequences: List, target_count: int = 100) -> List:
    """Optimize final selection for diversity and quality"""

    # Start with top scoring sequences
    final_selection = []
    remaining_sequences = ranked_sequences.copy()

    # Categories for diversity
    categories = {
        'high_binding': [],      # Top binding scores
        'high_structural': [],   # Top structural scores
        'diverse_scaffolds': [], # Different scaffold types
        'balanced': []           # Well-balanced scores
    }

    # Categorize sequences
    for seq_data in ranked_sequences:
        name, sequence, composite_score, scores = seq_data

        # Categorize based on strengths
        if scores['binding'] > 0.8:
            categories['high_binding'].append(seq_data)
        elif scores['structural'] > 0.8:
            categories['high_structural'].append(seq_data)
        elif scores['diversity'] > 0.8:
            categories['diverse_scaffolds'].append(seq_data)
        else:
            categories['balanced'].append(seq_data)

    # Select from each category to ensure diversity
    selections_per_category = {
        'high_binding': 40,      # 40% high binding potential
        'high_structural': 25,   # 25% high structural quality
        'diverse_scaffolds': 20, # 20% diverse scaffolds
        'balanced': 15           # 15% balanced properties
    }

    for category, count in selections_per_category.items():
        category_sequences = categories[category]
        # Sort by composite score within category
        category_sequences.sort(key=lambda x: x[2], reverse=True)

        # Add top sequences from this category
        added = 0
        for seq_data in category_sequences:
            if len(final_selection) < target_count and added < count:
                # Check if not already added
                if seq_data not in final_selection:
                    final_selection.append(seq_data)
                    added += 1

    # Fill remaining slots with top overall scores
    if len(final_selection) < target_count:
        for seq_data in ranked_sequences:
            if len(final_selection) >= target_count:
                break
            if seq_data not in final_selection:
                final_selection.append(seq_data)

    return final_selection[:target_count]

def create_submission_files(final_sequences: List, prefix: str = "final_rbx1_submission"):
    """Create final submission files"""

    # CSV format
    csv_filename = f"{prefix}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Rank', 'Name', 'Sequence', 'Composite_Score', 'Binding_Score', 'Druggability_Score'])

        for rank, (name, sequence, composite_score, scores) in enumerate(final_sequences, 1):
            writer.writerow([
                rank, name, sequence, f"{composite_score:.3f}",
                f"{scores['binding']:.3f}", f"{scores['druggability']:.3f}"
            ])

    # FASTA format
    fasta_filename = f"{prefix}.fasta"
    with open(fasta_filename, 'w') as f:
        for rank, (name, sequence, composite_score, scores) in enumerate(final_sequences, 1):
            f.write(f">{name}_Rank{rank:03d}_Score{composite_score:.3f}\n{sequence}\n")

    return csv_filename, fasta_filename

if __name__ == "__main__":
    print("Analyzing and ranking RBX-1 binder sequences...")

    # Load sequences
    sequences = load_sequences('rbx1_binder_submission.csv')
    print(f"Loaded {len(sequences)} sequences")

    # Rank sequences
    print("Calculating scores and ranking...")
    ranked_sequences = rank_sequences(sequences)

    # Optimize final selection
    print("Optimizing final selection for diversity...")
    final_selection = optimize_final_selection(ranked_sequences, target_count=100)

    # Create submission files
    print("Creating final submission files...")
    csv_file, fasta_file = create_submission_files(final_selection)

    # Print summary
    print(f"\n=== FINAL SELECTION SUMMARY ===")
    print(f"Selected {len(final_selection)} sequences")
    print(f"Files created: {csv_file}, {fasta_file}")

    # Top 10 summary
    print(f"\nTop 10 sequences:")
    for i, (name, sequence, score, scores) in enumerate(final_selection[:10], 1):
        length = len(sequence)
        print(f"{i:2d}. {name[:25]:25s} L={length:2d} Score={score:.3f} "
              f"(B:{scores['binding']:.2f} D:{scores['druggability']:.2f} S:{scores['structural']:.2f})")

    # Score distribution
    composite_scores = [score for _, _, score, _ in final_selection]
    print(f"\nScore statistics:")
    print(f"  Mean: {np.mean(composite_scores):.3f}")
    print(f"  Range: {np.min(composite_scores):.3f} - {np.max(composite_scores):.3f}")
    print(f"  Std: {np.std(composite_scores):.3f}")

    print(f"\n✅ Ready for competition submission!")