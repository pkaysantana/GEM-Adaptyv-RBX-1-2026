#!/usr/bin/env python3
"""
Molecular Docking-Inspired Binder Optimization
Uses simplified docking principles for RBX-1 binding prediction.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import random
import math

class RBX1StructuralModel:
    """Simplified RBX-1 binding site model based on known structure."""

    def __init__(self):
        # Key RBX-1 binding residues and their properties
        self.binding_site = {
            'hydrophobic_patches': [
                {'center': [0, 0, 0], 'radius': 8.0, 'strength': -2.5},    # LEU80, PHE81
                {'center': [5, -3, 2], 'radius': 6.0, 'strength': -2.0},   # VAL83, ILE87
            ],
            'electrostatic_features': [
                {'center': [2, 4, -1], 'charge': 0.5, 'radius': 10.0},     # Positive patch
                {'center': [-3, 1, 3], 'charge': -0.3, 'radius': 8.0},     # Negative patch
            ],
            'aromatic_sites': [
                {'center': [1, -2, 0], 'radius': 5.0, 'strength': -3.0},   # PHE81 stacking
                {'center': [-2, 3, 1], 'radius': 5.0, 'strength': -2.5},   # TYR interaction site
            ],
            'zinc_coordination': {
                'center': [0, 2, -2], 'radius': 4.0, 'strength': -4.0      # RING domain zinc
            }
        }

class ProteinGeometry:
    """Simple protein geometry model for docking calculations."""

    @staticmethod
    def estimate_residue_position(sequence: str, position: int) -> Tuple[float, float, float]:
        """Estimate 3D position of residue in extended conformation."""
        # Simplified: assume extended chain with some randomness
        phi = 3.8 * position  # Backbone length per residue
        theta = math.sin(position * 0.3) * 20  # Some secondary structure variation
        z = math.cos(position * 0.2) * 15

        return (phi, theta, z)

    @staticmethod
    def calculate_distance(pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

class DockingScorer:
    """Molecular docking-inspired scoring function."""

    def __init__(self):
        self.rbx1_model = RBX1StructuralModel()
        self.geometry = ProteinGeometry()

        # Amino acid interaction parameters
        self.aa_properties = {
            'F': {'hydrophobic': 3.2, 'aromatic': 3.0, 'volume': 135, 'charge': 0},
            'W': {'hydrophobic': 2.1, 'aromatic': 4.0, 'volume': 163, 'charge': 0},
            'Y': {'hydrophobic': 1.5, 'aromatic': 2.8, 'volume': 141, 'charge': 0},
            'L': {'hydrophobic': 3.8, 'aromatic': 0, 'volume': 124, 'charge': 0},
            'I': {'hydrophobic': 4.5, 'aromatic': 0, 'volume': 124, 'charge': 0},
            'V': {'hydrophobic': 4.2, 'aromatic': 0, 'volume': 105, 'charge': 0},
            'A': {'hydrophobic': 1.8, 'aromatic': 0, 'volume': 67, 'charge': 0},
            'G': {'hydrophobic': -0.4, 'aromatic': 0, 'volume': 48, 'charge': 0},
            'S': {'hydrophobic': -0.8, 'aromatic': 0, 'volume': 73, 'charge': 0},
            'T': {'hydrophobic': -0.7, 'aromatic': 0, 'volume': 93, 'charge': 0},
            'C': {'hydrophobic': 2.5, 'aromatic': 0, 'volume': 86, 'charge': 0},
            'M': {'hydrophobic': 1.9, 'aromatic': 0, 'volume': 124, 'charge': 0},
            'N': {'hydrophobic': -3.5, 'aromatic': 0, 'volume': 96, 'charge': 0},
            'Q': {'hydrophobic': -3.5, 'aromatic': 0, 'volume': 114, 'charge': 0},
            'D': {'hydrophobic': -3.5, 'aromatic': 0, 'volume': 91, 'charge': -1},
            'E': {'hydrophobic': -3.5, 'aromatic': 0, 'volume': 109, 'charge': -1},
            'K': {'hydrophobic': -3.9, 'aromatic': 0, 'volume': 135, 'charge': 1},
            'R': {'hydrophobic': -4.5, 'aromatic': 0, 'volume': 148, 'charge': 1},
            'H': {'hydrophobic': -3.2, 'aromatic': 1.5, 'volume': 118, 'charge': 0.1},
            'P': {'hydrophobic': -1.6, 'aromatic': 0, 'volume': 90, 'charge': 0},
        }

    def calculate_hydrophobic_interactions(self, sequence: str) -> float:
        """Calculate hydrophobic interaction score."""
        score = 0.0

        for i, aa in enumerate(sequence):
            pos = self.geometry.estimate_residue_position(sequence, i)
            aa_props = self.aa_properties[aa]

            for patch in self.rbx1_model.binding_site['hydrophobic_patches']:
                distance = self.geometry.calculate_distance(pos, patch['center'])

                if distance <= patch['radius']:
                    # Favorable hydrophobic interaction
                    interaction_strength = aa_props['hydrophobic'] * patch['strength']
                    distance_factor = math.exp(-distance / 3.0)
                    score += interaction_strength * distance_factor

        return score

    def calculate_aromatic_interactions(self, sequence: str) -> float:
        """Calculate aromatic stacking and pi interactions."""
        score = 0.0

        for i, aa in enumerate(sequence):
            if aa in 'FWY':
                pos = self.geometry.estimate_residue_position(sequence, i)
                aa_props = self.aa_properties[aa]

                for site in self.rbx1_model.binding_site['aromatic_sites']:
                    distance = self.geometry.calculate_distance(pos, site['center'])

                    if distance <= site['radius']:
                        # Aromatic stacking interaction
                        interaction_strength = aa_props['aromatic'] * site['strength']
                        optimal_distance = 3.8  # Optimal pi-pi stacking distance
                        distance_factor = math.exp(-abs(distance - optimal_distance) / 1.5)
                        score += interaction_strength * distance_factor

        return score

    def calculate_electrostatic_score(self, sequence: str) -> float:
        """Calculate electrostatic interactions."""
        score = 0.0

        for i, aa in enumerate(sequence):
            pos = self.geometry.estimate_residue_position(sequence, i)
            aa_charge = self.aa_properties[aa]['charge']

            if aa_charge != 0:
                for feature in self.rbx1_model.binding_site['electrostatic_features']:
                    distance = self.geometry.calculate_distance(pos, feature['center'])

                    if distance <= feature['radius'] and distance > 2.0:
                        # Electrostatic interaction (favorable if opposite charges)
                        interaction_energy = -aa_charge * feature['charge'] / distance
                        score += interaction_energy

        return score

    def calculate_shape_complementarity(self, sequence: str) -> float:
        """Calculate shape complementarity score."""
        # Simplified: favor optimal length and amino acid distribution
        length = len(sequence)
        optimal_length = 65
        length_score = math.exp(-abs(length - optimal_length) / 15)

        # Volume complementarity
        total_volume = sum(self.aa_properties[aa]['volume'] for aa in sequence)
        optimal_volume = optimal_length * 110  # Average AA volume
        volume_score = math.exp(-abs(total_volume - optimal_volume) / (optimal_volume * 0.2))

        return (length_score + volume_score) / 2

    def calculate_binding_specificity(self, sequence: str) -> float:
        """Calculate binding specificity for RBX-1."""
        # Favor specific amino acid patterns that complement RBX-1
        specificity_score = 0.0

        # Aromatic content (critical for RBX-1 binding)
        aromatic_count = sum(1 for aa in sequence if aa in 'FWY')
        aromatic_fraction = aromatic_count / len(sequence)
        if 0.25 <= aromatic_fraction <= 0.35:
            specificity_score += 2.0
        elif 0.20 <= aromatic_fraction < 0.25 or 0.35 < aromatic_fraction <= 0.40:
            specificity_score += 1.0

        # Hydrophobic patches
        hydrophobic_residues = [aa for aa in sequence if self.aa_properties[aa]['hydrophobic'] > 2.0]
        if 15 <= len(hydrophobic_residues) <= 25:
            specificity_score += 1.5

        # Charge balance
        positive_charges = sum(1 for aa in sequence if self.aa_properties[aa]['charge'] > 0)
        negative_charges = sum(1 for aa in sequence if self.aa_properties[aa]['charge'] < 0)
        charge_balance = abs(positive_charges - negative_charges) / len(sequence)
        if charge_balance <= 0.1:
            specificity_score += 1.0

        return specificity_score

    def calculate_docking_score(self, sequence: str) -> Dict[str, float]:
        """Calculate comprehensive docking score."""
        hydrophobic = self.calculate_hydrophobic_interactions(sequence)
        aromatic = self.calculate_aromatic_interactions(sequence)
        electrostatic = self.calculate_electrostatic_score(sequence)
        shape = self.calculate_shape_complementarity(sequence)
        specificity = self.calculate_binding_specificity(sequence)

        # Weighted combination
        total_score = (
            hydrophobic * 0.25 +
            aromatic * 0.30 +
            electrostatic * 0.15 +
            shape * 0.15 +
            specificity * 0.15
        )

        return {
            'total_score': total_score,
            'hydrophobic': hydrophobic,
            'aromatic': aromatic,
            'electrostatic': electrostatic,
            'shape_complementarity': shape,
            'binding_specificity': specificity
        }

class OptimizedBinderGenerator:
    """Generate binders using docking-guided optimization."""

    def __init__(self):
        self.scorer = DockingScorer()

    def generate_targeted_sequence(self, length: int = 65) -> str:
        """Generate sequence optimized for RBX-1 binding."""

        # Target composition based on docking insights
        target_composition = {
            'F': 0.14,  # High aromatic for pi-stacking
            'W': 0.09,  # Strong aromatic interactions
            'Y': 0.10,  # Aromatic + H-bonding
            'L': 0.11,  # Hydrophobic core
            'I': 0.09,  # Hydrophobic
            'V': 0.08,  # Branched hydrophobic
            'R': 0.08,  # Positive charge
            'K': 0.07,  # Positive charge
            'D': 0.06,  # Negative charge
            'E': 0.07,  # Negative charge
            'A': 0.07,  # Small hydrophobic
            'S': 0.04   # Polar
        }

        # Normalize
        total = sum(target_composition.values())
        target_composition = {aa: prob/total for aa, prob in target_composition.items()}

        amino_acids = list(target_composition.keys())
        weights = list(target_composition.values())

        sequence = ''.join(np.random.choice(amino_acids, size=length, p=weights))
        return sequence

    def optimize_sequence(self, initial_sequence: str, iterations: int = 100) -> str:
        """Optimize sequence using local search."""
        current_sequence = initial_sequence
        current_score = self.scorer.calculate_docking_score(current_sequence)['total_score']

        for _ in range(iterations):
            # Make random mutation
            pos = random.randint(0, len(current_sequence) - 1)
            original_aa = current_sequence[pos]

            # Try different amino acids at this position
            candidate_aas = ['F', 'W', 'Y', 'L', 'I', 'V', 'R', 'K', 'D', 'E']
            new_aa = random.choice([aa for aa in candidate_aas if aa != original_aa])

            # Create mutated sequence
            mutated_sequence = current_sequence[:pos] + new_aa + current_sequence[pos+1:]
            mutated_score = self.scorer.calculate_docking_score(mutated_sequence)['total_score']

            # Accept if improved
            if mutated_score > current_score:
                current_sequence = mutated_sequence
                current_score = mutated_score

        return current_sequence

def generate_docking_optimized_binders(num_sequences: int = 50) -> pd.DataFrame:
    """Generate docking-optimized binder library."""

    print("Molecular Docking-Inspired Optimization")
    print("=" * 42)

    generator = OptimizedBinderGenerator()
    sequences = []

    for i in range(num_sequences):
        # Generate initial sequence
        length = random.randint(60, 75)
        initial_seq = generator.generate_targeted_sequence(length)

        # Optimize sequence
        optimized_seq = generator.optimize_sequence(initial_seq, iterations=50)

        # Score final sequence
        scores = generator.scorer.calculate_docking_score(optimized_seq)

        sequences.append({
            'name': f'RBX1_Docking_v1_{i+1:03d}',
            'sequence': optimized_seq,
            'length': len(optimized_seq),
            'aromatic_content': sum(1 for aa in optimized_seq if aa in 'FWY') / len(optimized_seq),
            **scores
        })

        if (i + 1) % 10 == 0:
            print(f"Generated {i + 1}/{num_sequences} optimized binders")

    df = pd.DataFrame(sequences)
    df = df.sort_values('total_score', ascending=False)

    print(f"\nOptimization Results:")
    print(f"Best score: {df['total_score'].max():.4f}")
    print(f"Mean score: {df['total_score'].mean():.4f}")
    print(f"Mean aromatic content: {df['aromatic_content'].mean():.3f}")
    print(f"Length range: {df['length'].min()}-{df['length'].max()} AA")

    # Save results
    output_file = "docking_optimized_binders.csv"
    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

    return df

if __name__ == "__main__":
    optimized_df = generate_docking_optimized_binders(50)

    print("\nTop 10 Docking-Optimized Binders:")
    for i, row in optimized_df.head(10).iterrows():
        print(f"  {row['name']}: Score {row['total_score']:.4f}, "
              f"Length {row['length']}, Aromatic {row['aromatic_content']:.3f}")