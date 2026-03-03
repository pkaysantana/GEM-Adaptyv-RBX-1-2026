#!/usr/bin/env python3
"""
Competition Strategy Optimizer
Optimizes portfolio selection for maximum competition success.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import random
from itertools import combinations

class CompetitionStrategyOptimizer:
    """Optimize binder portfolio for competition success."""

    def __init__(self):
        self.competition_criteria = {
            'binding_affinity': {'weight': 0.35, 'min_threshold': 0.7},
            'experimental_success': {'weight': 0.25, 'min_threshold': 0.8},
            'structural_diversity': {'weight': 0.15, 'min_threshold': 0.6},
            'novelty_factor': {'weight': 0.15, 'min_threshold': 0.5},
            'druggability': {'weight': 0.10, 'min_threshold': 0.6}
        }

    def calculate_structural_diversity_score(self, sequences: List[str]) -> float:
        """Calculate diversity score for a set of sequences."""

        if len(sequences) < 2:
            return 0.0

        # Calculate pairwise sequence similarities
        similarities = []
        for i, seq1 in enumerate(sequences):
            for j, seq2 in enumerate(sequences[i+1:], i+1):
                # Simple similarity: fraction of identical positions
                min_len = min(len(seq1), len(seq2))
                matches = sum(1 for k in range(min_len) if seq1[k] == seq2[k])
                similarity = matches / min_len
                similarities.append(similarity)

        # Diversity is 1 - average similarity
        avg_similarity = np.mean(similarities) if similarities else 0
        diversity_score = 1.0 - avg_similarity

        return min(1.0, max(0.0, diversity_score))

    def calculate_novelty_score(self, sequence: str) -> float:
        """Calculate novelty score based on unusual patterns."""

        length = len(sequence)

        # Novel aromatic patterns
        aromatic_content = sum(sequence.count(aa) for aa in 'FWY') / length
        if aromatic_content > 0.35:  # Higher than typical
            aromatic_novelty = 0.8
        elif aromatic_content > 0.30:
            aromatic_novelty = 0.6
        else:
            aromatic_novelty = 0.4

        # Unusual amino acid combinations
        unusual_patterns = ['FWF', 'WYW', 'YFY', 'WWW', 'FFF', 'YYY']
        pattern_score = 0.0
        for pattern in unusual_patterns:
            if pattern in sequence:
                pattern_score += 0.2

        # Length novelty (very short or optimally sized)
        if 45 <= length <= 55:  # Very compact
            length_novelty = 0.8
        elif 65 <= length <= 70:  # Optimal size
            length_novelty = 0.6
        else:
            length_novelty = 0.3

        novelty_score = (aromatic_novelty + min(pattern_score, 1.0) + length_novelty) / 3
        return novelty_score

    def calculate_druggability_score(self, sequence: str) -> float:
        """Calculate druggability based on length and composition."""

        length = len(sequence)

        # Length factor (shorter is more druggable)
        if length <= 60:
            length_score = 1.0
        elif length <= 70:
            length_score = 0.8
        elif length <= 80:
            length_score = 0.6
        else:
            length_score = 0.4

        # Hydrophobic/hydrophilic balance
        hydrophobic_count = sum(sequence.count(aa) for aa in 'FWYLIV')
        hydrophilic_count = sum(sequence.count(aa) for aa in 'STNQDE')

        if hydrophobic_count + hydrophilic_count > 0:
            balance = min(hydrophobic_count, hydrophilic_count) / max(hydrophobic_count, hydrophilic_count)
            balance_score = balance
        else:
            balance_score = 0.5

        # Charge distribution (moderate charges better)
        positive_charges = sequence.count('R') + sequence.count('K')
        negative_charges = sequence.count('D') + sequence.count('E')
        total_charges = positive_charges + negative_charges

        if total_charges <= length * 0.2:  # <= 20% charged
            charge_score = 1.0
        elif total_charges <= length * 0.3:  # <= 30% charged
            charge_score = 0.8
        else:
            charge_score = 0.6

        druggability_score = (length_score + balance_score + charge_score) / 3
        return druggability_score

    def optimize_portfolio_selection(self, candidates_df: pd.DataFrame,
                                   portfolio_size: int = 100) -> pd.DataFrame:
        """Optimize portfolio for competition success."""

        print("Competition Portfolio Optimization")
        print("=" * 35)

        # Calculate scores for all candidates
        enhanced_candidates = []

        for _, row in candidates_df.iterrows():
            sequence = row['sequence']
            name = row['name']

            # Get existing scores
            binding_score = row.get('consensus_score', row.get('overall_success_probability', 0.7))
            experimental_score = row.get('overall_success_probability', 0.8)

            # Calculate additional scores
            novelty_score = self.calculate_novelty_score(sequence)
            druggability_score = self.calculate_druggability_score(sequence)

            enhanced_candidates.append({
                'name': name,
                'sequence': sequence,
                'binding_score': binding_score,
                'experimental_score': experimental_score,
                'novelty_score': novelty_score,
                'druggability_score': druggability_score,
                'length': len(sequence),
                'aromatic_content': sum(sequence.count(aa) for aa in 'FWY') / len(sequence)
            })

        enhanced_df = pd.DataFrame(enhanced_candidates)

        # Portfolio optimization using multiple strategies
        strategies = [
            self._greedy_selection,
            self._diversity_focused_selection,
            self._balanced_selection,
            self._high_confidence_selection
        ]

        best_portfolio = None
        best_score = -1

        for strategy in strategies:
            portfolio = strategy(enhanced_df, portfolio_size)
            portfolio_score = self._evaluate_portfolio(portfolio)

            print(f"Strategy {strategy.__name__}: Score {portfolio_score:.3f}")

            if portfolio_score > best_score:
                best_score = portfolio_score
                best_portfolio = portfolio

        print(f"\nBest strategy score: {best_score:.3f}")

        # Add diversity score to final portfolio
        sequences = best_portfolio['sequence'].tolist()
        diversity_score = self.calculate_structural_diversity_score(sequences)
        best_portfolio['portfolio_diversity'] = diversity_score

        # Calculate final competition score for each sequence
        final_scores = []
        for _, row in best_portfolio.iterrows():
            competition_score = (
                row['binding_score'] * self.competition_criteria['binding_affinity']['weight'] +
                row['experimental_score'] * self.competition_criteria['experimental_success']['weight'] +
                diversity_score * self.competition_criteria['structural_diversity']['weight'] +
                row['novelty_score'] * self.competition_criteria['novelty_factor']['weight'] +
                row['druggability_score'] * self.competition_criteria['druggability']['weight']
            )
            final_scores.append(competition_score)

        best_portfolio['competition_score'] = final_scores
        best_portfolio = best_portfolio.sort_values('competition_score', ascending=False)

        return best_portfolio

    def _greedy_selection(self, df: pd.DataFrame, size: int) -> pd.DataFrame:
        """Greedy selection prioritizing highest individual scores."""
        # Weight multiple factors
        df['greedy_score'] = (
            df['binding_score'] * 0.4 +
            df['experimental_score'] * 0.3 +
            df['novelty_score'] * 0.2 +
            df['druggability_score'] * 0.1
        )
        return df.nlargest(size, 'greedy_score')

    def _diversity_focused_selection(self, df: pd.DataFrame, size: int) -> pd.DataFrame:
        """Selection prioritizing diversity."""
        selected = []
        remaining = df.copy()

        # Start with highest scoring sequence
        best_idx = remaining['binding_score'].idxmax()
        selected.append(remaining.loc[best_idx])
        remaining = remaining.drop(best_idx)

        while len(selected) < size and len(remaining) > 0:
            best_candidate = None
            best_diversity = -1

            for idx, candidate in remaining.iterrows():
                # Calculate diversity with already selected
                selected_sequences = [seq['sequence'] for seq in selected]
                test_sequences = selected_sequences + [candidate['sequence']]
                diversity = self.calculate_structural_diversity_score(test_sequences)

                # Combined score: diversity + quality
                combined_score = diversity * 0.6 + candidate['binding_score'] * 0.4

                if combined_score > best_diversity:
                    best_diversity = combined_score
                    best_candidate = idx

            if best_candidate is not None:
                selected.append(remaining.loc[best_candidate])
                remaining = remaining.drop(best_candidate)

        return pd.DataFrame(selected)

    def _balanced_selection(self, df: pd.DataFrame, size: int) -> pd.DataFrame:
        """Balanced selection across all criteria."""
        df['balanced_score'] = (
            df['binding_score'] * 0.35 +
            df['experimental_score'] * 0.25 +
            df['novelty_score'] * 0.2 +
            df['druggability_score'] * 0.2
        )
        return df.nlargest(size, 'balanced_score')

    def _high_confidence_selection(self, df: pd.DataFrame, size: int) -> pd.DataFrame:
        """Selection prioritizing high confidence candidates."""
        # Filter for high experimental success first
        high_confidence = df[df['experimental_score'] > 0.8]
        if len(high_confidence) >= size:
            return high_confidence.nlargest(size, 'binding_score')
        else:
            # Fill remaining with next best
            remaining_needed = size - len(high_confidence)
            remaining_df = df[df['experimental_score'] <= 0.8]
            additional = remaining_df.nlargest(remaining_needed, 'experimental_score')
            return pd.concat([high_confidence, additional])

    def _evaluate_portfolio(self, portfolio: pd.DataFrame) -> float:
        """Evaluate portfolio against competition criteria."""
        sequences = portfolio['sequence'].tolist()
        diversity_score = self.calculate_structural_diversity_score(sequences)

        portfolio_score = (
            portfolio['binding_score'].mean() * self.competition_criteria['binding_affinity']['weight'] +
            portfolio['experimental_score'].mean() * self.competition_criteria['experimental_success']['weight'] +
            diversity_score * self.competition_criteria['structural_diversity']['weight'] +
            portfolio['novelty_score'].mean() * self.competition_criteria['novelty_factor']['weight'] +
            portfolio['druggability_score'].mean() * self.competition_criteria['druggability']['weight']
        )

        return portfolio_score

def run_competition_optimization():
    """Run complete competition optimization pipeline."""

    print("GEM-Adaptyv RBX-1 Competition Optimization")
    print("=" * 45)

    # Load experimental validation results
    try:
        candidates_df = pd.read_csv('experimental_validation_analysis_meta_ensemble_final_submission.csv')
        print(f"Loaded {len(candidates_df)} validated candidates")
    except Exception as e:
        print(f"Error loading validation data: {e}")
        return

    # Run optimization
    optimizer = CompetitionStrategyOptimizer()
    optimized_portfolio = optimizer.optimize_portfolio_selection(candidates_df, 100)

    # Save optimized portfolio
    competition_file = "gem_adaptyv_final_competition_submission.csv"
    optimized_portfolio[['name', 'sequence']].to_csv(competition_file, index=False)

    detailed_file = "gem_adaptyv_competition_analysis.csv"
    optimized_portfolio.to_csv(detailed_file, index=False)

    print(f"\nOptimized competition submission saved:")
    print(f"  Competition format: {competition_file}")
    print(f"  Detailed analysis: {detailed_file}")

    # Competition readiness summary
    print(f"\nCompetition Readiness Summary:")
    print(f"  Portfolio size: {len(optimized_portfolio)}")
    print(f"  Mean competition score: {optimized_portfolio['competition_score'].mean():.3f}")
    print(f"  Best competition score: {optimized_portfolio['competition_score'].max():.3f}")
    print(f"  Portfolio diversity: {optimized_portfolio['portfolio_diversity'].iloc[0]:.3f}")
    print(f"  Mean experimental success: {optimized_portfolio['experimental_score'].mean():.3f}")

    # Top 10 final candidates
    print(f"\nTop 10 Final Competition Candidates:")
    top_10 = optimized_portfolio.head(10)
    for i, row in top_10.iterrows():
        print(f"  {i+1:2d}. {row['name'][:30]:<30} | "
              f"Score: {row['competition_score']:.3f} | "
              f"Exp: {row['experimental_score']:.3f} | "
              f"Length: {row['length']:2d}")

    print(f"\nReady for GEM-Adaptyv RBX-1 submission!")
    return optimized_portfolio

if __name__ == "__main__":
    final_portfolio = run_competition_optimization()
    print(f"\nCompetition optimization complete")