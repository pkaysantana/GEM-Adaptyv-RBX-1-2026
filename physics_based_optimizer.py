#!/usr/bin/env python3
"""
Physics-Based Binder Optimization
Implements molecular mechanics principles for improved binding prediction.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple, Dict
import random
import math

@dataclass
class ResidueProperties:
    """Physical and chemical properties of amino acids."""
    hydrophobicity: float
    volume: float
    charge: float
    polarizability: float
    hydrogen_bonding: float
    aromatic: bool
    flexibility: float

# Comprehensive amino acid property database
RESIDUE_PROPERTIES = {
    'A': ResidueProperties(1.8, 67, 0, 0.046, 0, False, 0.8),
    'C': ResidueProperties(2.5, 86, 0, 0.128, 1, False, 0.3),
    'D': ResidueProperties(-3.5, 91, -1, 0.105, 1, False, 0.9),
    'E': ResidueProperties(-3.5, 109, -1, 0.151, 1, False, 0.9),
    'F': ResidueProperties(2.8, 135, 0, 0.290, 0, True, 0.4),
    'G': ResidueProperties(-0.4, 48, 0, 0.000, 0, False, 1.0),
    'H': ResidueProperties(-3.2, 118, 0.1, 0.230, 1, True, 0.7),
    'I': ResidueProperties(4.5, 124, 0, 0.186, 0, False, 0.3),
    'K': ResidueProperties(-3.9, 135, 1, 0.219, 1, False, 0.9),
    'L': ResidueProperties(3.8, 124, 0, 0.186, 0, False, 0.4),
    'M': ResidueProperties(1.9, 124, 0, 0.221, 0, False, 0.5),
    'N': ResidueProperties(-3.5, 96, 0, 0.134, 1, False, 0.8),
    'P': ResidueProperties(-1.6, 90, 0, 0.131, 0, False, 0.1),
    'Q': ResidueProperties(-3.5, 114, 0, 0.180, 1, False, 0.8),
    'R': ResidueProperties(-4.5, 148, 1, 0.291, 1, False, 0.9),
    'S': ResidueProperties(-0.8, 73, 0, 0.062, 1, False, 0.9),
    'T': ResidueProperties(-0.7, 93, 0, 0.108, 1, False, 0.7),
    'V': ResidueProperties(4.2, 105, 0, 0.140, 0, False, 0.2),
    'W': ResidueProperties(-0.9, 163, 0, 0.409, 1, True, 0.3),
    'Y': ResidueProperties(-1.3, 141, 0, 0.298, 1, True, 0.5),
}

class PhysicsBasedScorer:
    """Physics-based scoring for protein-protein interactions."""

    def __init__(self):
        self.binding_interface_size = 15  # Approximate residues in binding interface
        self.temperature = 300  # Kelvin
        self.kb = 0.001987  # Boltzmann constant (kcal/mol/K)

    def calculate_hydrophobic_interaction(self, sequence: str) -> float:
        """Calculate hydrophobic interaction energy."""
        hydrophobic_residues = [res for res in sequence if RESIDUE_PROPERTIES[res].hydrophobicity > 1.0]

        if len(hydrophobic_residues) < 3:
            return 0.0

        # Approximate hydrophobic interaction energy
        hydrophobic_energy = 0.0
        for i, res1 in enumerate(hydrophobic_residues[:-1]):
            for res2 in hydrophobic_residues[i+1:]:
                props1 = RESIDUE_PROPERTIES[res1]
                props2 = RESIDUE_PROPERTIES[res2]

                # Simplified hydrophobic interaction model
                interaction_strength = (props1.hydrophobicity * props2.hydrophobicity) / 100
                hydrophobic_energy += interaction_strength

        return hydrophobic_energy

    def calculate_electrostatic_energy(self, sequence: str) -> float:
        """Calculate electrostatic interaction energy."""
        charged_residues = [(i, res) for i, res in enumerate(sequence)
                          if RESIDUE_PROPERTIES[res].charge != 0]

        if len(charged_residues) < 2:
            return 0.0

        electrostatic_energy = 0.0
        for i, (pos1, res1) in enumerate(charged_residues[:-1]):
            for pos2, res2 in charged_residues[i+1:]:
                charge1 = RESIDUE_PROPERTIES[res1].charge
                charge2 = RESIDUE_PROPERTIES[res2].charge

                # Distance approximation based on sequence separation
                distance = max(3.8, abs(pos1 - pos2) * 1.5)  # Angstroms

                # Coulomb's law (simplified, in water)
                coulomb_energy = (332 * charge1 * charge2) / (78 * distance)
                electrostatic_energy += coulomb_energy

        return electrostatic_energy

    def calculate_aromatic_stacking(self, sequence: str) -> float:
        """Calculate pi-pi stacking interactions."""
        aromatic_positions = [i for i, res in enumerate(sequence)
                            if RESIDUE_PROPERTIES[res].aromatic]

        stacking_energy = 0.0
        for i, pos1 in enumerate(aromatic_positions[:-1]):
            for pos2 in aromatic_positions[i+1:]:
                separation = abs(pos1 - pos2)

                # Optimal stacking occurs at 3-6 residue separation
                if 2 <= separation <= 8:
                    distance_factor = math.exp(-abs(separation - 4) / 3)
                    stacking_energy += 2.5 * distance_factor  # kcal/mol

        return stacking_energy

    def calculate_hydrogen_bonding(self, sequence: str) -> float:
        """Calculate hydrogen bonding potential."""
        hbond_donors = [i for i, res in enumerate(sequence)
                       if RESIDUE_PROPERTIES[res].hydrogen_bonding > 0]

        if len(hbond_donors) < 2:
            return 0.0

        hbond_energy = 0.0
        for i, pos1 in enumerate(hbond_donors[:-1]):
            for pos2 in hbond_donors[i+1:]:
                separation = abs(pos1 - pos2)

                # Hydrogen bonds form optimally at 3-5 residue separation
                if 2 <= separation <= 7:
                    distance_factor = math.exp(-abs(separation - 3.5) / 2)
                    hbond_energy += 1.8 * distance_factor  # kcal/mol

        return hbond_energy

    def calculate_conformational_entropy(self, sequence: str) -> float:
        """Calculate conformational entropy penalty."""
        flexibility_sum = sum(RESIDUE_PROPERTIES[res].flexibility for res in sequence)
        mean_flexibility = flexibility_sum / len(sequence)

        # High flexibility increases entropy (unfavorable for binding)
        entropy_penalty = -self.temperature * self.kb * mean_flexibility * len(sequence) / 10
        return entropy_penalty

    def calculate_binding_affinity(self, sequence: str) -> float:
        """Calculate overall binding affinity score."""

        # Individual energy components
        hydrophobic = self.calculate_hydrophobic_interaction(sequence)
        electrostatic = self.calculate_electrostatic_energy(sequence)
        aromatic = self.calculate_aromatic_stacking(sequence)
        hbonds = self.calculate_hydrogen_bonding(sequence)
        entropy = self.calculate_conformational_entropy(sequence)

        # Total binding energy (more negative = stronger binding)
        total_energy = hydrophobic + electrostatic + aromatic + hbonds + entropy

        # Convert to affinity score (higher = better)
        affinity_score = math.exp(-total_energy / (self.kb * self.temperature))

        return {
            'total_score': affinity_score,
            'hydrophobic': hydrophobic,
            'electrostatic': electrostatic,
            'aromatic_stacking': aromatic,
            'hydrogen_bonding': hbonds,
            'entropy_penalty': entropy,
            'total_energy': total_energy
        }

class EvolutionaryOptimizer:
    """Evolutionary algorithm for sequence optimization."""

    def __init__(self, population_size=50):
        self.population_size = population_size
        self.mutation_rate = 0.15
        self.crossover_rate = 0.7
        self.scorer = PhysicsBasedScorer()

    def initialize_population(self, target_length=65) -> List[str]:
        """Initialize random population with bias toward aromatic residues."""

        # Biased amino acid distribution
        aromatic_bias = {'F': 0.15, 'W': 0.10, 'Y': 0.12}
        hydrophobic = {'L': 0.10, 'I': 0.08, 'V': 0.08}
        charged = {'R': 0.08, 'K': 0.07, 'D': 0.06, 'E': 0.07}
        polar = {'S': 0.05, 'T': 0.04, 'N': 0.04, 'Q': 0.04}
        others = {'A': 0.06, 'G': 0.04, 'P': 0.02}

        aa_distribution = {**aromatic_bias, **hydrophobic, **charged, **polar, **others}

        # Normalize weights to sum to 1.0
        total_weight = sum(aa_distribution.values())
        aa_distribution = {aa: weight/total_weight for aa, weight in aa_distribution.items()}

        amino_acids = list(aa_distribution.keys())
        weights = list(aa_distribution.values())

        population = []
        for _ in range(self.population_size):
            # Add some length variation
            length = random.randint(target_length - 5, target_length + 10)
            sequence = ''.join(np.random.choice(amino_acids, size=length, p=weights))
            population.append(sequence)

        return population

    def mutate(self, sequence: str) -> str:
        """Apply mutation to sequence."""
        sequence_list = list(sequence)

        for i in range(len(sequence_list)):
            if random.random() < self.mutation_rate:
                # Bias mutations toward aromatic residues
                if random.random() < 0.4:
                    sequence_list[i] = random.choice(['F', 'W', 'Y'])
                else:
                    sequence_list[i] = random.choice('ACDEFGHIKLMNPQRSTVWY')

        return ''.join(sequence_list)

    def crossover(self, parent1: str, parent2: str) -> Tuple[str, str]:
        """Perform crossover between two sequences."""
        if random.random() > self.crossover_rate:
            return parent1, parent2

        min_len = min(len(parent1), len(parent2))
        crossover_point = random.randint(1, min_len - 1)

        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]

        return child1, child2

    def evolve_generation(self, population: List[str]) -> List[str]:
        """Evolve one generation."""

        # Evaluate fitness
        fitness_scores = []
        for seq in population:
            result = self.scorer.calculate_binding_affinity(seq)
            fitness_scores.append(result['total_score'])

        # Selection (tournament selection)
        selected = []
        for _ in range(self.population_size):
            tournament_size = 3
            tournament_indices = random.sample(range(len(population)), tournament_size)
            winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
            selected.append(population[winner_idx])

        # Crossover and mutation
        next_generation = []
        for i in range(0, len(selected), 2):
            parent1 = selected[i]
            parent2 = selected[(i + 1) % len(selected)]

            child1, child2 = self.crossover(parent1, parent2)
            child1 = self.mutate(child1)
            child2 = self.mutate(child2)

            next_generation.extend([child1, child2])

        return next_generation[:self.population_size]

def run_physics_optimization(generations=20):
    """Run physics-based evolutionary optimization."""

    print("Physics-Based Evolutionary Optimization")
    print("=" * 45)

    optimizer = EvolutionaryOptimizer()
    population = optimizer.initialize_population()

    best_scores = []
    best_sequences = []

    for gen in range(generations):
        # Evaluate current population
        scores = []
        for seq in population:
            result = optimizer.scorer.calculate_binding_affinity(seq)
            scores.append((seq, result))

        # Track best performer
        best_individual = max(scores, key=lambda x: x[1]['total_score'])
        best_scores.append(best_individual[1]['total_score'])
        best_sequences.append(best_individual[0])

        if gen % 5 == 0:
            print(f"Generation {gen}: Best score = {best_individual[1]['total_score']:.4f}")
            print(f"  Length: {len(best_individual[0])} AA")
            print(f"  Aromatic content: {sum(1 for aa in best_individual[0] if aa in 'FWY') / len(best_individual[0]):.3f}")

        # Evolve to next generation
        population = optimizer.evolve_generation(population)

    # Final evaluation
    final_scores = []
    for seq in population:
        result = optimizer.scorer.calculate_binding_affinity(seq)
        final_scores.append({
            'sequence': seq,
            'length': len(seq),
            'aromatic_content': sum(1 for aa in seq if aa in 'FWY') / len(seq),
            **result
        })

    # Create DataFrame
    df = pd.DataFrame(final_scores)
    df = df.sort_values('total_score', ascending=False)

    print(f"\nOptimization Results:")
    print(f"Best final score: {df['total_score'].max():.4f}")
    print(f"Mean final score: {df['total_score'].mean():.4f}")
    print(f"Best sequence length: {df.iloc[0]['length']} AA")
    print(f"Best aromatic content: {df.iloc[0]['aromatic_content']:.3f}")

    # Save results
    output_file = "physics_optimized_binders.csv"
    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

    return df

if __name__ == "__main__":
    optimized_binders = run_physics_optimization(25)

    print("\nTop 5 Physics-Optimized Binders:")
    top_5 = optimized_binders.head()
    for i, row in top_5.iterrows():
        print(f"  {i+1}. Score: {row['total_score']:.4f}, Length: {row['length']}, Aromatic: {row['aromatic_content']:.3f}")
        print(f"     Energy: {row['total_energy']:.2f} kcal/mol")