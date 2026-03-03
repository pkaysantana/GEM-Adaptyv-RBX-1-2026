#!/usr/bin/env python3
"""
Meta-Ensemble Optimizer - Ultimate Binder Selection
Combines all optimization approaches using ensemble methods.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import VotingRegressor, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

class MetaEnsembleOptimizer:
    """Meta-ensemble combining multiple optimization approaches."""

    def __init__(self):
        self.scalers = {
            'standard': StandardScaler(),
            'minmax': MinMaxScaler()
        }
        self.ensemble_model = None
        self.feature_importance = None

    def load_all_optimized_sequences(self) -> pd.DataFrame:
        """Load sequences from all optimization approaches."""

        all_dataframes = []

        # Load Enhanced v2.0
        try:
            df = pd.read_csv('enhanced_rbx1_binders_v2.csv')
            df['optimization_method'] = 'enhanced_v2'
            df['generation_score'] = df['quality_score']
            all_dataframes.append(df[['name', 'sequence', 'length', 'aromatic_content',
                                    'optimization_method', 'generation_score']])
        except:
            pass

        # Load Ultra v3.0
        try:
            df = pd.read_csv('ultra_optimized_rbx1_binders_v3.csv')
            df['optimization_method'] = 'ultra_v3'
            df['generation_score'] = df['quality_score']
            all_dataframes.append(df[['name', 'sequence', 'length', 'aromatic_content',
                                    'optimization_method', 'generation_score']])
        except:
            pass

        # Load Docking optimized
        try:
            df = pd.read_csv('docking_optimized_binders.csv')
            df['optimization_method'] = 'docking_v1'
            df['generation_score'] = df['total_score']
            all_dataframes.append(df[['name', 'sequence', 'length', 'aromatic_content',
                                    'optimization_method', 'generation_score']])
        except:
            pass

        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            print(f"Loaded {len(combined_df)} sequences from {len(all_dataframes)} optimization methods")
            return combined_df
        else:
            print("No optimization data found")
            return pd.DataFrame()

    def extract_comprehensive_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract comprehensive features for meta-learning."""

        features_list = []

        for _, row in df.iterrows():
            sequence = row['sequence']
            length = len(sequence)

            features = {
                'length': length,
                'aromatic_content': sum(1 for aa in sequence if aa in 'FWY') / length,
                'hydrophobic_content': sum(1 for aa in sequence if aa in 'FWYLIV') / length,
                'charged_content': sum(1 for aa in sequence if aa in 'DEKR') / length,
                'polar_content': sum(1 for aa in sequence if aa in 'STNQ') / length,
            }

            # Specific amino acid frequencies
            for aa in 'FWYLIV':
                features[f'freq_{aa}'] = sequence.count(aa) / length

            # Binding motifs
            binding_motifs = ['FW', 'WY', 'FF', 'WW', 'YY', 'LF', 'WL', 'FY']
            for motif in binding_motifs:
                features[f'motif_{motif}'] = sequence.count(motif)

            # Sequence properties
            features['net_charge'] = (sequence.count('R') + sequence.count('K') +
                                    sequence.count('H')) - (sequence.count('D') + sequence.count('E'))
            features['charge_density'] = abs(features['net_charge']) / length

            # Structural propensities
            helix_favoring = sum(1 for aa in sequence if aa in 'AELKR') / length
            sheet_favoring = sum(1 for aa in sequence if aa in 'VIFYWTL') / length
            features['helix_propensity'] = helix_favoring
            features['sheet_propensity'] = sheet_favoring

            # Method-specific encoding
            features['is_enhanced_v2'] = 1 if row['optimization_method'] == 'enhanced_v2' else 0
            features['is_ultra_v3'] = 1 if row['optimization_method'] == 'ultra_v3' else 0
            features['is_docking_v1'] = 1 if row['optimization_method'] == 'docking_v1' else 0

            # Original score from generation method
            features['original_score'] = row['generation_score']

            features_list.append(features)

        return pd.DataFrame(features_list)

    def build_ensemble_predictor(self, features_df: pd.DataFrame, target_scores: np.ndarray):
        """Build ensemble predictor combining multiple algorithms."""

        # Scale features
        X_scaled = self.scalers['standard'].fit_transform(features_df)

        # Define base models
        base_models = [
            ('rf', RandomForestRegressor(n_estimators=100, random_state=42)),
            ('gb', GradientBoostingRegressor(n_estimators=100, random_state=42)),
            ('lr', LinearRegression())
        ]

        # Create voting ensemble
        self.ensemble_model = VotingRegressor(estimators=base_models)
        self.ensemble_model.fit(X_scaled, target_scores)

        # Get feature importance from random forest
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_scaled, target_scores)

        self.feature_importance = pd.DataFrame({
            'feature': features_df.columns,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("Top 10 Most Important Features:")
        for _, row in self.feature_importance.head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        return X_scaled

    def predict_ensemble_scores(self, features_df: pd.DataFrame) -> np.ndarray:
        """Predict scores using ensemble model."""
        X_scaled = self.scalers['standard'].transform(features_df)
        return self.ensemble_model.predict(X_scaled)

    def calculate_consensus_score(self, df: pd.DataFrame, features_df: pd.DataFrame) -> np.ndarray:
        """Calculate consensus score across all methods."""

        # Normalize original scores to 0-1 range for each method
        normalized_scores = []

        for method in df['optimization_method'].unique():
            method_mask = df['optimization_method'] == method
            method_scores = df.loc[method_mask, 'generation_score'].values

            if len(method_scores) > 1:
                min_score, max_score = method_scores.min(), method_scores.max()
                if max_score > min_score:
                    norm_scores = (method_scores - min_score) / (max_score - min_score)
                else:
                    norm_scores = np.ones_like(method_scores) * 0.5
            else:
                norm_scores = np.array([0.5])

            normalized_scores.extend(norm_scores)

        # Get ensemble predictions
        ensemble_scores = self.predict_ensemble_scores(features_df)

        # Normalize ensemble scores
        ensemble_min, ensemble_max = ensemble_scores.min(), ensemble_scores.max()
        if ensemble_max > ensemble_min:
            ensemble_normalized = (ensemble_scores - ensemble_min) / (ensemble_max - ensemble_min)
        else:
            ensemble_normalized = np.ones_like(ensemble_scores) * 0.5

        # Combine with weights
        consensus_scores = (
            0.4 * np.array(normalized_scores) +  # Original method scores
            0.6 * ensemble_normalized            # Ensemble predictions
        )

        return consensus_scores

    def select_diverse_portfolio(self, df: pd.DataFrame, scores: np.ndarray,
                               num_select: int = 100) -> pd.DataFrame:
        """Select diverse portfolio using clustering and optimization."""

        df_scored = df.copy()
        df_scored['consensus_score'] = scores

        # First, take top performers from each method
        selected_indices = []

        for method in df['optimization_method'].unique():
            method_df = df_scored[df_scored['optimization_method'] == method]
            if len(method_df) > 0:
                # Take top 5 from each method
                top_method = method_df.nlargest(5, 'consensus_score')
                selected_indices.extend(top_method.index.tolist())

        # Fill remaining slots with highest consensus scores
        remaining_slots = num_select - len(selected_indices)
        if remaining_slots > 0:
            excluded_df = df_scored.drop(selected_indices)
            if len(excluded_df) > 0:
                top_remaining = excluded_df.nlargest(remaining_slots, 'consensus_score')
                selected_indices.extend(top_remaining.index.tolist())

        final_portfolio = df_scored.loc[selected_indices[:num_select]]

        return final_portfolio.sort_values('consensus_score', ascending=False)

def run_meta_ensemble_optimization():
    """Run complete meta-ensemble optimization pipeline."""

    print("Meta-Ensemble Optimization Pipeline")
    print("=" * 38)

    optimizer = MetaEnsembleOptimizer()

    # Load all sequences
    print("Loading sequences from all optimization methods...")
    all_sequences_df = optimizer.load_all_optimized_sequences()

    if all_sequences_df.empty:
        print("No sequences found!")
        return

    print(f"Loaded {len(all_sequences_df)} total sequences")
    print("\nMethod distribution:")
    method_counts = all_sequences_df['optimization_method'].value_counts()
    for method, count in method_counts.items():
        print(f"  {method}: {count} sequences")

    # Extract features
    print("\nExtracting comprehensive features...")
    features_df = optimizer.extract_comprehensive_features(all_sequences_df)
    print(f"Extracted {len(features_df.columns)} features")

    # Build ensemble model
    print("\nBuilding ensemble predictor...")
    target_scores = all_sequences_df['generation_score'].values
    X_scaled = optimizer.build_ensemble_predictor(features_df, target_scores)

    # Calculate consensus scores
    print("\nCalculating consensus scores...")
    consensus_scores = optimizer.calculate_consensus_score(all_sequences_df, features_df)

    # Select final portfolio
    print(f"\nSelecting final portfolio of 100 sequences...")
    final_portfolio = optimizer.select_diverse_portfolio(
        all_sequences_df, consensus_scores, num_select=100
    )

    # Save results
    output_file = "meta_ensemble_final_submission.csv"
    final_portfolio[['name', 'sequence']].to_csv(output_file, index=False)

    detailed_file = "meta_ensemble_detailed_analysis.csv"
    final_portfolio.to_csv(detailed_file, index=False)

    print(f"\nMeta-ensemble results saved:")
    print(f"  Competition format: {output_file}")
    print(f"  Detailed analysis: {detailed_file}")

    # Final analysis
    print(f"\nFinal Portfolio Analysis:")
    print(f"  Best consensus score: {final_portfolio['consensus_score'].max():.4f}")
    print(f"  Mean consensus score: {final_portfolio['consensus_score'].mean():.4f}")
    print(f"  Length range: {final_portfolio['length'].min()}-{final_portfolio['length'].max()} AA")
    print(f"  Mean aromatic content: {final_portfolio['aromatic_content'].mean():.3f}")

    print(f"\nMethod representation in final portfolio:")
    final_method_counts = final_portfolio['optimization_method'].value_counts()
    for method, count in final_method_counts.items():
        percentage = 100 * count / len(final_portfolio)
        print(f"  {method}: {count} sequences ({percentage:.1f}%)")

    print(f"\nTop 10 Final Candidates:")
    top_10 = final_portfolio.head(10)
    for i, (_, row) in enumerate(top_10.iterrows(), 1):
        print(f"  {i:2d}. {row['name'][:30]:<30} | "
              f"Score: {row['consensus_score']:.4f} | "
              f"Length: {row['length']:2d} | "
              f"Method: {row['optimization_method']}")

    return final_portfolio

if __name__ == "__main__":
    final_results = run_meta_ensemble_optimization()
    print(f"\nMeta-ensemble optimization complete")
    print(f"Ultimate submission ready for competition")