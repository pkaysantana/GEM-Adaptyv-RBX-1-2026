#!/usr/bin/env python3
"""
Combine Enhanced v2.0 sequences with original binders and create updated submission.
"""

import pandas as pd
import numpy as np

def load_and_combine_sequences():
    """Load both original and enhanced sequences, select best overall."""

    print("🔗 Combining Original and Enhanced v2.0 Sequences")
    print("=" * 55)

    # Load original sequences
    print("📁 Loading original sequences...")
    try:
        original_df = pd.read_csv('final_rbx1_submission.csv')
        print(f"   ✓ Loaded {len(original_df)} original sequences")
        print(f"   • Mean score: {original_df['overall_score'].mean():.3f}")
        print(f"   • Best score: {original_df['overall_score'].max():.3f}")
    except Exception as e:
        print(f"   ✗ Error loading original: {e}")
        original_df = pd.DataFrame()

    # Load enhanced v2.0 sequences
    print("\n📁 Loading enhanced v2.0 sequences...")
    try:
        enhanced_df = pd.read_csv('enhanced_rbx1_binders_v2.csv')
        print(f"   ✓ Loaded {len(enhanced_df)} enhanced sequences")
        print(f"   • Mean score: {enhanced_df['quality_score'].mean():.3f}")
        print(f"   • Best score: {enhanced_df['quality_score'].max():.3f}")

        # Rename quality_score to overall_score for consistency
        enhanced_df = enhanced_df.rename(columns={'quality_score': 'overall_score'})

    except Exception as e:
        print(f"   ✗ Error loading enhanced: {e}")
        enhanced_df = pd.DataFrame()

    # Combine and analyze
    if not original_df.empty and not enhanced_df.empty:
        print("\n📊 Performance Comparison:")
        print(f"   • Original Mean: {original_df['overall_score'].mean():.3f}")
        print(f"   • Enhanced Mean: {enhanced_df['overall_score'].mean():.3f}")
        print(f"   • Improvement: {((enhanced_df['overall_score'].mean() / original_df['overall_score'].mean()) - 1) * 100:.1f}%")

        # Combine dataframes
        all_sequences = pd.concat([original_df, enhanced_df], ignore_index=True)

        # Select top 100 overall
        top_100 = all_sequences.nlargest(100, 'overall_score').copy()
        top_100 = top_100.reset_index(drop=True)

        print(f"\n🎯 Final Selection Statistics:")
        print(f"   • Total candidates: {len(all_sequences)}")
        print(f"   • Selected top: 100")
        print(f"   • Final mean score: {top_100['overall_score'].mean():.3f}")
        print(f"   • Final best score: {top_100['overall_score'].max():.3f}")

        # Count sources in top 100
        enhanced_count = len(top_100[top_100['name'].str.contains('Enhanced')])
        original_count = 100 - enhanced_count

        print(f"   • Enhanced v2.0 sequences: {enhanced_count}")
        print(f"   • Original sequences: {original_count}")

        return top_100

    elif not enhanced_df.empty:
        print(f"\n📋 Using enhanced sequences only...")
        return enhanced_df.head(100).copy()

    elif not original_df.empty:
        print(f"\n📋 Using original sequences only...")
        return original_df.head(100).copy()

    else:
        print(f"\n❌ No sequences found!")
        return pd.DataFrame()

def create_competition_submission(df):
    """Create the final competition submission file."""

    print(f"\n📝 Creating Competition Submission File")
    print(f"=" * 45)

    # Prepare competition format
    submission_data = []

    for idx, row in df.iterrows():
        # Validate sequence (only standard amino acids, correct length)
        sequence = row['sequence'].upper()

        # Remove any invalid characters
        valid_aas = 'ACDEFGHIKLMNPQRSTVWY'
        clean_sequence = ''.join([aa for aa in sequence if aa in valid_aas])

        # Check length constraints
        if 40 <= len(clean_sequence) <= 250:
            submission_data.append({
                'name': row['name'],
                'sequence': clean_sequence,
                'length': len(clean_sequence),
                'score': row['overall_score']
            })

    submission_df = pd.DataFrame(submission_data)

    print(f"   ✓ Validated {len(submission_df)} sequences")
    print(f"   • Length range: {submission_df['length'].min()}-{submission_df['length'].max()} AA")
    print(f"   • Mean length: {submission_df['length'].mean():.1f} AA")
    print(f"   • Mean score: {submission_df['score'].mean():.3f}")

    # Save competition submission
    competition_file = 'final_rbx1_submission_enhanced_v2.csv'
    submission_df[['name', 'sequence']].to_csv(competition_file, index=False)

    # Save detailed version with scores
    detailed_file = 'final_rbx1_submission_enhanced_v2_detailed.csv'
    submission_df.to_csv(detailed_file, index=False)

    print(f"\n💾 Files saved:")
    print(f"   • Competition format: {competition_file}")
    print(f"   • Detailed analysis: {detailed_file}")

    return submission_df

def analyze_improvements(df):
    """Analyze the improvements in the new submission."""

    print(f"\n🔬 Improvement Analysis")
    print(f"=" * 30)

    # Enhanced vs original breakdown
    enhanced_mask = df['name'].str.contains('Enhanced', na=False)
    enhanced_seqs = df[enhanced_mask]
    original_seqs = df[~enhanced_mask]

    if not enhanced_seqs.empty and not original_seqs.empty:
        print(f"📈 Enhanced v2.0 Performance:")
        print(f"   • Count: {len(enhanced_seqs)}")
        print(f"   • Mean Score: {enhanced_seqs['overall_score'].mean():.3f}")
        print(f"   • Best Score: {enhanced_seqs['overall_score'].max():.3f}")
        print(f"   • Mean Length: {enhanced_seqs['length'].mean():.1f} AA")

        print(f"\n📊 Original Performance:")
        print(f"   • Count: {len(original_seqs)}")
        print(f"   • Mean Score: {original_seqs['overall_score'].mean():.3f}")
        print(f"   • Best Score: {original_seqs['overall_score'].max():.3f}")

        improvement = ((enhanced_seqs['overall_score'].mean() / original_seqs['overall_score'].mean()) - 1) * 100
        print(f"\n🚀 Overall Improvement: {improvement:.1f}%")

    # Top 10 analysis
    print(f"\n🏆 Top 10 Final Candidates:")
    top_10 = df.nlargest(10, 'overall_score')

    for idx, row in top_10.iterrows():
        seq_type = "Enhanced" if "Enhanced" in row['name'] else "Original"
        print(f"   {idx+1:2d}. {row['name'][:25]:<25} | Score: {row['overall_score']:.3f} | {row['length']} AA | {seq_type}")

if __name__ == "__main__":
    print("🔄 RBX-1 Submission Update - Enhanced v2.0 Integration")
    print("=" * 60)

    # Combine sequences
    combined_df = load_and_combine_sequences()

    if not combined_df.empty:
        # Create submission
        submission_df = create_competition_submission(combined_df)

        # Analyze improvements
        analyze_improvements(combined_df)

        print(f"\n✅ Updated submission ready!")
        print(f"🎯 Competition deadline: March 26, 2026")
        print(f"🎂 Your 21st birthday: March 20, 2026 ({17} days)")

    else:
        print(f"\n❌ Failed to create submission")