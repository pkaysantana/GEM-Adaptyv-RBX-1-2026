#!/usr/bin/env python3
"""
Day 1 Ultimate Integration - ML-Enhanced Portfolio Optimization
Combines all three generations with machine learning for optimal selection.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings
from typing import Dict
warnings.filterwarnings('ignore')

def extract_advanced_features(sequence: str) -> Dict[str, float]:
    """Extract comprehensive features for ML scoring."""

    length = len(sequence)

    # Basic composition
    aa_counts = {aa: sequence.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY'}
    aa_fractions = {aa: count/length for aa, count in aa_counts.items()}

    # Advanced features
    features = {}

    # 1. Aromatic features (critical for binding)
    aromatic_aas = 'FWY'
    aromatic_total = sum(aa_fractions[aa] for aa in aromatic_aas)
    features['aromatic_total'] = aromatic_total
    features['aromatic_F'] = aa_fractions['F']
    features['aromatic_W'] = aa_fractions['W']
    features['aromatic_Y'] = aa_fractions['Y']

    # 2. Hydrophobic features
    hydrophobic_aas = 'FWYLIV'
    hydrophobic_total = sum(aa_fractions[aa] for aa in hydrophobic_aas)
    features['hydrophobic_total'] = hydrophobic_total

    # 3. Charge features
    positive_aas = 'RK'
    negative_aas = 'DE'
    features['positive_charge'] = sum(aa_fractions[aa] for aa in positive_aas)
    features['negative_charge'] = sum(aa_fractions[aa] for aa in negative_aas)
    features['net_charge'] = features['positive_charge'] - features['negative_charge']

    # 4. Polar features
    polar_aas = 'STNQ'
    features['polar'] = sum(aa_fractions[aa] for aa in polar_aas)

    # 5. Special amino acids
    features['proline'] = aa_fractions['P']
    features['glycine'] = aa_fractions['G']
    features['cysteine'] = aa_fractions['C']
    features['histidine'] = aa_fractions['H']

    # 6. Sequence properties
    features['length'] = length
    features['length_normalized'] = (length - 65) / 10  # Center around 65 AA

    # 7. Binding motif features
    binding_motifs = ['FW', 'WY', 'FF', 'WW', 'YY', 'FY', 'YF', 'WF']
    for motif in binding_motifs:
        features[f'motif_{motif}'] = sequence.count(motif) / max(1, length-1)

    # 8. Structural propensities (simplified)
    helix_favorable = 'AELKR'
    sheet_favorable = 'VIFYWTL'
    turn_favorable = 'GPSTDN'

    features['helix_propensity'] = sum(aa_fractions[aa] for aa in helix_favorable)
    features['sheet_propensity'] = sum(aa_fractions[aa] for aa in sheet_favorable)
    features['turn_propensity'] = sum(aa_fractions[aa] for aa in turn_favorable)

    return features

class MLEnhancedPortfolioOptimizer:
    """Machine learning enhanced portfolio optimization."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)
        self.clusterer = KMeans(n_clusters=8, random_state=42)
        self.quality_predictor = RandomForestRegressor(n_estimators=100, random_state=42)

    def load_all_generations(self):
        """Load all generated sequences from different versions."""
        all_sequences = []

        # Load Enhanced v2
        try:
            df_v2 = pd.read_csv('enhanced_rbx1_binders_v2.csv')
            df_v2['generation'] = 'enhanced_v2'
            df_v2['overall_score'] = df_v2['quality_score']
            all_sequences.append(df_v2)
            print(f"✓ Loaded Enhanced v2.0: {len(df_v2)} sequences")
        except Exception as e:
            print(f"⚠ Enhanced v2 not found: {e}")

        # Load Ultra-optimized v3
        try:
            df_v3 = pd.read_csv('ultra_optimized_rbx1_binders_v3.csv')
            df_v3['generation'] = 'ultra_v3'
            df_v3['overall_score'] = df_v3['quality_score']
            all_sequences.append(df_v3)
            print(f"✓ Loaded Ultra v3.0: {len(df_v3)} sequences")
        except Exception as e:
            print(f"⚠ Ultra v3 not found: {e}")

        if all_sequences:
            combined_df = pd.concat(all_sequences, ignore_index=True)
            print(f"📊 Total candidates: {len(combined_df)}")
            return combined_df
        else:
            print("❌ No sequences found!")
            return pd.DataFrame()

    def extract_features_for_all(self, df):
        """Extract ML features for all sequences."""
        print("🧬 Extracting advanced features...")

        features_list = []
        for _, row in df.iterrows():
            features = extract_advanced_features(row['sequence'])
            features['original_score'] = row['overall_score']
            features_list.append(features)

        features_df = pd.DataFrame(features_list)
        print(f"✓ Extracted {len(features_df.columns)} features")
        return features_df

    def train_ensemble_predictor(self, features_df):
        """Train ensemble predictor for quality scoring."""
        print("🤖 Training ML quality predictor...")

        # Use original scores as training targets (with some augmentation)
        X = features_df.drop(['original_score'], axis=1)
        y = features_df['original_score']

        # Add some synthetic high-quality targets based on feature combinations
        high_quality_mask = (
            (features_df['aromatic_total'] > 0.25) &
            (features_df['hydrophobic_total'] > 0.35) &
            (features_df['hydrophobic_total'] < 0.50) &
            (features_df['length'] > 55) &
            (features_df['length'] < 80)
        )

        # Boost scores for sequences matching optimal criteria
        y_enhanced = y.copy()
        y_enhanced[high_quality_mask] *= 1.2

        # Train predictor
        X_scaled = self.scaler.fit_transform(X)
        self.quality_predictor.fit(X_scaled, y_enhanced)

        # Get feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.quality_predictor.feature_importances_
        }).sort_values('importance', ascending=False)

        print("🎯 Top 5 Most Important Features:")
        for _, row in feature_importance.head().iterrows():
            print(f"   • {row['feature']}: {row['importance']:.3f}")

        return X_scaled

    def predict_enhanced_scores(self, features_df):
        """Predict enhanced quality scores."""
        X = features_df.drop(['original_score'], axis=1)
        X_scaled = self.scaler.transform(X)

        enhanced_scores = self.quality_predictor.predict(X_scaled)
        return enhanced_scores

    def optimize_portfolio_diversity(self, df, features_scaled, top_n=100):
        """Optimize portfolio for maximum diversity and quality."""
        print(f"🎲 Optimizing portfolio diversity (top {top_n})...")

        # Perform clustering for diversity
        self.pca.fit(features_scaled)
        features_pca = self.pca.transform(features_scaled)
        clusters = self.clusterer.fit_predict(features_pca)

        df_with_clusters = df.copy()
        df_with_clusters['cluster'] = clusters
        df_with_clusters['pca_1'] = features_pca[:, 0]
        df_with_clusters['pca_2'] = features_pca[:, 1]

        print(f"✓ Identified {len(np.unique(clusters))} diversity clusters")

        # Select diverse portfolio
        selected_indices = []

        # First, take top scorer from each cluster
        for cluster_id in np.unique(clusters):
            cluster_df = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
            best_in_cluster = cluster_df.loc[cluster_df['ml_score'].idxmax()]
            selected_indices.append(best_in_cluster.name)

        # Fill remaining slots with highest scorers
        remaining_slots = top_n - len(selected_indices)
        if remaining_slots > 0:
            excluded_df = df_with_clusters.drop(selected_indices)
            top_remaining = excluded_df.nlargest(remaining_slots, 'ml_score')
            selected_indices.extend(top_remaining.index.tolist())

        optimized_portfolio = df_with_clusters.loc[selected_indices]

        print(f"🎯 Portfolio Statistics:")
        print(f"   • Sequences selected: {len(optimized_portfolio)}")
        print(f"   • ML score range: {optimized_portfolio['ml_score'].min():.3f} - {optimized_portfolio['ml_score'].max():.3f}")
        print(f"   • Clusters represented: {len(optimized_portfolio['cluster'].unique())}/{len(np.unique(clusters))}")

        return optimized_portfolio

def run_ultimate_day1_integration():
    """Run the ultimate Day 1 integration pipeline."""

    print("🚀 DAY 1 ULTIMATE INTEGRATION - ML-Enhanced Portfolio")
    print("=" * 65)
    print("🎯 Features:")
    print("   • Multi-generation sequence integration")
    print("   • Machine learning quality prediction")
    print("   • Portfolio diversity optimization")
    print("   • Advanced feature engineering")
    print()

    optimizer = MLEnhancedPortfolioOptimizer()

    # Load all sequences
    print("📂 Loading all generated sequences...")
    all_df = optimizer.load_all_generations()

    if all_df.empty:
        print("❌ No sequences to optimize!")
        return

    # Extract features
    features_df = optimizer.extract_features_for_all(all_df)

    # Train ML predictor
    features_scaled = optimizer.train_ensemble_predictor(features_df)

    # Predict enhanced scores
    print("🔮 Generating ML-enhanced quality scores...")
    ml_scores = optimizer.predict_enhanced_scores(features_df)
    all_df['ml_score'] = ml_scores

    print(f"📈 Score Enhancement:")
    print(f"   • Original mean: {all_df['overall_score'].mean():.3f}")
    print(f"   • ML-enhanced mean: {all_df['ml_score'].mean():.3f}")
    print(f"   • Best ML score: {all_df['ml_score'].max():.3f}")

    # Optimize portfolio
    final_portfolio = optimizer.optimize_portfolio_diversity(all_df, features_scaled, top_n=100)

    # Save results
    output_file = "day1_ultimate_submission.csv"
    final_portfolio[['name', 'sequence']].to_csv(output_file, index=False)

    detailed_file = "day1_ultimate_submission_detailed.csv"
    final_portfolio.to_csv(detailed_file, index=False)

    print(f"\n💾 Ultimate Day 1 submission saved:")
    print(f"   • Competition format: {output_file}")
    print(f"   • Detailed analysis: {detailed_file}")

    # Final analysis
    print(f"\n🏆 FINAL DAY 1 STATISTICS:")
    print(f"   • Total sequences evaluated: {len(all_df)}")
    print(f"   • Final portfolio size: {len(final_portfolio)}")
    print(f"   • Best sequence: {final_portfolio.loc[final_portfolio['ml_score'].idxmax()]['name']}")
    print(f"   • Top ML score: {final_portfolio['ml_score'].max():.3f}")
    print(f"   • Portfolio mean score: {final_portfolio['ml_score'].mean():.3f}")
    print(f"   • Length range: {final_portfolio['length'].min()}-{final_portfolio['length'].max()} AA")
    print(f"   • Mean aromatic content: {final_portfolio['aromatic_content'].mean():.3f}")

    # Generation breakdown
    print(f"\n📊 Generation Breakdown in Final Portfolio:")
    gen_counts = final_portfolio['generation'].value_counts()
    for gen, count in gen_counts.items():
        print(f"   • {gen}: {count} sequences ({100*count/len(final_portfolio):.1f}%)")

    return final_portfolio

if __name__ == "__main__":
    final_portfolio = run_ultimate_day1_integration()
    print(f"\n✨ Day 1 Ultimate Integration Complete!")
    print(f"🎯 Ready for overnight optimization!")