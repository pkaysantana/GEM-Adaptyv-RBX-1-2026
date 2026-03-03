#!/usr/bin/env python3
"""
Experimental Validation Predictor
Predicts likelihood of successful experimental validation for designed binders.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import random
import math

class ExperimentalValidationPredictor:
    """Predicts experimental success probability for protein binders."""

    def __init__(self):
        # Experimental success factors based on literature
        self.success_factors = {
            'sequence_length': {'optimal_range': (60, 75), 'weight': 0.15},
            'aromatic_content': {'optimal_range': (0.25, 0.35), 'weight': 0.25},
            'hydrophobic_balance': {'optimal_range': (0.35, 0.45), 'weight': 0.20},
            'charge_balance': {'optimal_range': (-2, 2), 'weight': 0.10},
            'structural_stability': {'weight': 0.15},
            'expression_likelihood': {'weight': 0.10},
            'aggregation_resistance': {'weight': 0.05}
        }

    def calculate_expression_likelihood(self, sequence: str) -> float:
        """Predict expression likelihood in E. coli."""

        # Factors affecting expression
        factors = {}

        # Codon bias (simplified - avoid rare codons)
        rare_codons = ['R', 'P', 'G']  # Simplified - these can cause expression issues
        rare_count = sum(sequence.count(aa) for aa in rare_codons)
        factors['codon_bias'] = 1.0 - (rare_count / len(sequence)) * 0.3

        # N-terminal residues (avoid problematic starts)
        if sequence[0] in 'DEKR':  # Charged N-terminus can be problematic
            factors['n_terminal'] = 0.8
        else:
            factors['n_terminal'] = 1.0

        # Cysteine content (unpaired cysteines can cause issues)
        cys_count = sequence.count('C')
        if cys_count == 0:
            factors['cysteine'] = 1.0
        elif cys_count % 2 == 0:  # Even number, likely paired
            factors['cysteine'] = 0.9
        else:  # Odd number, unpaired cysteine
            factors['cysteine'] = 0.7

        # Overall expression score
        expression_score = np.mean(list(factors.values()))
        return min(1.0, max(0.0, expression_score))

    def calculate_aggregation_resistance(self, sequence: str) -> float:
        """Predict resistance to aggregation."""

        length = len(sequence)

        # Hydrophobic patches (consecutive hydrophobic residues)
        hydrophobic_aas = 'FWYLIV'
        max_hydrophobic_stretch = 0
        current_stretch = 0

        for aa in sequence:
            if aa in hydrophobic_aas:
                current_stretch += 1
                max_hydrophobic_stretch = max(max_hydrophobic_stretch, current_stretch)
            else:
                current_stretch = 0

        # Penalize long hydrophobic stretches
        if max_hydrophobic_stretch <= 4:
            hydrophobic_penalty = 0.0
        elif max_hydrophobic_stretch <= 6:
            hydrophobic_penalty = 0.2
        else:
            hydrophobic_penalty = 0.5

        # Beta-sheet propensity (high beta content can lead to aggregation)
        beta_prone_aas = 'VIFYWTL'
        beta_content = sum(sequence.count(aa) for aa in beta_prone_aas) / length

        if beta_content <= 0.4:
            beta_penalty = 0.0
        elif beta_content <= 0.6:
            beta_penalty = 0.1
        else:
            beta_penalty = 0.3

        # Aromatic content (very high can cause pi-stacking aggregation)
        aromatic_content = sum(sequence.count(aa) for aa in 'FWY') / length

        if aromatic_content <= 0.35:
            aromatic_penalty = 0.0
        elif aromatic_content <= 0.45:
            aromatic_penalty = 0.1
        else:
            aromatic_penalty = 0.4

        aggregation_resistance = 1.0 - (hydrophobic_penalty + beta_penalty + aromatic_penalty)
        return min(1.0, max(0.0, aggregation_resistance))

    def calculate_structural_stability(self, sequence: str) -> float:
        """Estimate structural stability."""

        length = len(sequence)

        # Proline content (too much reduces flexibility, too little reduces stability)
        proline_content = sequence.count('P') / length
        if 0.02 <= proline_content <= 0.08:
            proline_score = 1.0
        else:
            proline_score = 0.8

        # Glycine content (too much reduces stability)
        glycine_content = sequence.count('G') / length
        if glycine_content <= 0.08:
            glycine_score = 1.0
        elif glycine_content <= 0.12:
            glycine_score = 0.9
        else:
            glycine_score = 0.7

        # Hydrophobic core potential
        hydrophobic_aas = 'FWYLIV'
        hydrophobic_content = sum(sequence.count(aa) for aa in hydrophobic_aas) / length

        if 0.35 <= hydrophobic_content <= 0.50:
            hydrophobic_score = 1.0
        elif 0.25 <= hydrophobic_content < 0.35 or 0.50 < hydrophobic_content <= 0.60:
            hydrophobic_score = 0.8
        else:
            hydrophobic_score = 0.6

        stability_score = (proline_score + glycine_score + hydrophobic_score) / 3
        return stability_score

    def predict_experimental_success(self, sequence: str,
                                   additional_metrics: Dict = None) -> Dict[str, float]:
        """Predict overall experimental success probability."""

        length = len(sequence)

        # Calculate individual factors
        predictions = {}

        # Length factor
        optimal_min, optimal_max = self.success_factors['sequence_length']['optimal_range']
        if optimal_min <= length <= optimal_max:
            length_score = 1.0
        else:
            deviation = min(abs(length - optimal_min), abs(length - optimal_max))
            length_score = max(0.5, 1.0 - deviation / 20)
        predictions['length_score'] = length_score

        # Aromatic content factor
        aromatic_content = sum(sequence.count(aa) for aa in 'FWY') / length
        opt_min, opt_max = self.success_factors['aromatic_content']['optimal_range']
        if opt_min <= aromatic_content <= opt_max:
            aromatic_score = 1.0
        else:
            deviation = min(abs(aromatic_content - opt_min), abs(aromatic_content - opt_max))
            aromatic_score = max(0.3, 1.0 - deviation / opt_max)
        predictions['aromatic_score'] = aromatic_score

        # Hydrophobic balance
        hydrophobic_content = sum(sequence.count(aa) for aa in 'FWYLIV') / length
        opt_min, opt_max = self.success_factors['hydrophobic_balance']['optimal_range']
        if opt_min <= hydrophobic_content <= opt_max:
            hydrophobic_score = 1.0
        else:
            deviation = min(abs(hydrophobic_content - opt_min), abs(hydrophobic_content - opt_max))
            hydrophobic_score = max(0.4, 1.0 - deviation / opt_max)
        predictions['hydrophobic_score'] = hydrophobic_score

        # Charge balance
        positive_charges = sequence.count('R') + sequence.count('K') + sequence.count('H')
        negative_charges = sequence.count('D') + sequence.count('E')
        net_charge = positive_charges - negative_charges
        opt_min, opt_max = self.success_factors['charge_balance']['optimal_range']
        if opt_min <= net_charge <= opt_max:
            charge_score = 1.0
        else:
            charge_score = max(0.6, 1.0 - abs(net_charge) / 10)
        predictions['charge_score'] = charge_score

        # Structural stability
        predictions['stability_score'] = self.calculate_structural_stability(sequence)

        # Expression likelihood
        predictions['expression_score'] = self.calculate_expression_likelihood(sequence)

        # Aggregation resistance
        predictions['aggregation_score'] = self.calculate_aggregation_resistance(sequence)

        # Calculate weighted overall success probability
        overall_success = (
            predictions['length_score'] * self.success_factors['sequence_length']['weight'] +
            predictions['aromatic_score'] * self.success_factors['aromatic_content']['weight'] +
            predictions['hydrophobic_score'] * self.success_factors['hydrophobic_balance']['weight'] +
            predictions['charge_score'] * self.success_factors['charge_balance']['weight'] +
            predictions['stability_score'] * self.success_factors['structural_stability']['weight'] +
            predictions['expression_score'] * self.success_factors['expression_likelihood']['weight'] +
            predictions['aggregation_score'] * self.success_factors['aggregation_resistance']['weight']
        )

        predictions['overall_success_probability'] = overall_success

        # Risk assessment
        risk_factors = []
        if predictions['expression_score'] < 0.7:
            risk_factors.append("Low expression likelihood")
        if predictions['aggregation_score'] < 0.7:
            risk_factors.append("Aggregation risk")
        if predictions['stability_score'] < 0.7:
            risk_factors.append("Structural stability concerns")
        if aromatic_content > 0.4:
            risk_factors.append("Very high aromatic content")
        if net_charge > 5 or net_charge < -5:
            risk_factors.append("Extreme charge imbalance")

        predictions['risk_factors'] = risk_factors
        predictions['risk_level'] = 'High' if len(risk_factors) >= 3 else 'Medium' if len(risk_factors) >= 1 else 'Low'

        return predictions

def analyze_portfolio_for_experimental_validation(csv_file: str):
    """Analyze entire portfolio for experimental validation likelihood."""

    print("Experimental Validation Analysis")
    print("=" * 35)

    # Load sequences
    try:
        df = pd.read_csv(csv_file)
        print(f"Analyzing {len(df)} sequences from {csv_file}")
    except Exception as e:
        print(f"Error loading {csv_file}: {e}")
        return

    predictor = ExperimentalValidationPredictor()

    # Analyze each sequence
    validation_results = []

    for _, row in df.iterrows():
        sequence = row['sequence']
        name = row['name']

        predictions = predictor.predict_experimental_success(sequence)

        result = {
            'name': name,
            'sequence': sequence,
            'length': len(sequence),
            'aromatic_content': sum(sequence.count(aa) for aa in 'FWY') / len(sequence),
            **predictions
        }

        validation_results.append(result)

    # Create results DataFrame
    results_df = pd.DataFrame(validation_results)
    results_df = results_df.sort_values('overall_success_probability', ascending=False)

    # Summary statistics
    print(f"\nValidation Analysis Summary:")
    print(f"Mean success probability: {results_df['overall_success_probability'].mean():.3f}")
    print(f"Best success probability: {results_df['overall_success_probability'].max():.3f}")
    print(f"Sequences with >80% success probability: {len(results_df[results_df['overall_success_probability'] > 0.8])}")
    print(f"Sequences with >70% success probability: {len(results_df[results_df['overall_success_probability'] > 0.7])}")

    # Risk level distribution
    print(f"\nRisk Level Distribution:")
    risk_counts = results_df['risk_level'].value_counts()
    for risk, count in risk_counts.items():
        print(f"  {risk}: {count} sequences")

    # Top candidates for experimental validation
    print(f"\nTop 10 Candidates for Experimental Validation:")
    top_10 = results_df.head(10)
    for i, row in top_10.iterrows():
        print(f"  {row['name'][:30]:<30} | "
              f"Success: {row['overall_success_probability']:.3f} | "
              f"Risk: {row['risk_level']} | "
              f"Length: {row['length']}")

    # Save results
    output_file = f"experimental_validation_analysis_{csv_file.replace('.csv', '.csv')}"
    results_df.to_csv(output_file, index=False)
    print(f"\nDetailed analysis saved to: {output_file}")

    return results_df

if __name__ == "__main__":
    # Analyze the meta-ensemble final submission
    try:
        results = analyze_portfolio_for_experimental_validation('meta_ensemble_final_submission.csv')

        print(f"\nExperimental validation analysis complete")
        print(f"Ready for laboratory testing prioritization")

    except Exception as e:
        print(f"Analysis failed: {e}")
        print("Ensure meta_ensemble_final_submission.csv exists")