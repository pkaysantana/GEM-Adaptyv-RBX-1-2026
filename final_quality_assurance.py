#!/usr/bin/env python3
"""
Final Quality Assurance System
Comprehensive validation before competition submission.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import re

class FinalQualityAssurance:
    """Final quality checks for competition submission."""

    def __init__(self):
        self.validation_rules = {
            'sequence_format': {
                'allowed_characters': set('ACDEFGHIKLMNPQRSTVWY'),
                'min_length': 40,
                'max_length': 250
            },
            'competition_requirements': {
                'max_sequences': 100,
                'file_format': 'CSV',
                'required_columns': ['name', 'sequence']
            },
            'quality_thresholds': {
                'min_experimental_success': 0.7,
                'min_diversity_score': 0.8,
                'min_binding_potential': 0.6
            }
        }

    def validate_sequence_format(self, sequences: List[str]) -> Dict:
        """Validate sequence format compliance."""

        validation_results = {
            'valid_sequences': [],
            'invalid_sequences': [],
            'warnings': [],
            'errors': []
        }

        allowed_chars = self.validation_rules['sequence_format']['allowed_characters']
        min_len = self.validation_rules['sequence_format']['min_length']
        max_len = self.validation_rules['sequence_format']['max_length']

        for i, seq in enumerate(sequences):
            seq_issues = []

            # Check characters
            invalid_chars = set(seq) - allowed_chars
            if invalid_chars:
                seq_issues.append(f"Invalid characters: {invalid_chars}")

            # Check length
            if len(seq) < min_len:
                seq_issues.append(f"Too short: {len(seq)} < {min_len}")
            elif len(seq) > max_len:
                seq_issues.append(f"Too long: {len(seq)} > {max_len}")

            # Check for suspicious patterns
            if 'XXX' in seq:
                seq_issues.append("Contains placeholder 'XXX'")
            if len(set(seq)) < 5:
                seq_issues.append("Very low amino acid diversity")

            if seq_issues:
                validation_results['invalid_sequences'].append({
                    'index': i,
                    'sequence': seq[:50] + '...' if len(seq) > 50 else seq,
                    'issues': seq_issues
                })
            else:
                validation_results['valid_sequences'].append(seq)

        return validation_results

    def validate_competition_format(self, df: pd.DataFrame) -> Dict:
        """Validate competition file format."""

        validation_results = {
            'format_valid': True,
            'warnings': [],
            'errors': []
        }

        required_cols = self.validation_rules['competition_requirements']['required_columns']
        max_seqs = self.validation_rules['competition_requirements']['max_sequences']

        # Check columns
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            validation_results['format_valid'] = False
            validation_results['errors'].append(f"Missing columns: {missing_cols}")

        # Check sequence count
        if len(df) > max_seqs:
            validation_results['format_valid'] = False
            validation_results['errors'].append(f"Too many sequences: {len(df)} > {max_seqs}")

        # Check for duplicates
        if 'sequence' in df.columns:
            duplicate_count = df['sequence'].duplicated().sum()
            if duplicate_count > 0:
                validation_results['warnings'].append(f"Found {duplicate_count} duplicate sequences")

        # Check name uniqueness
        if 'name' in df.columns:
            duplicate_names = df['name'].duplicated().sum()
            if duplicate_names > 0:
                validation_results['warnings'].append(f"Found {duplicate_names} duplicate names")

        return validation_results

    def validate_portfolio_quality(self, df: pd.DataFrame) -> Dict:
        """Validate overall portfolio quality."""

        validation_results = {
            'quality_passed': True,
            'metrics': {},
            'warnings': [],
            'recommendations': []
        }

        # Calculate portfolio metrics
        if 'experimental_score' in df.columns:
            exp_success_mean = df['experimental_score'].mean()
            validation_results['metrics']['experimental_success_mean'] = exp_success_mean

            min_threshold = self.validation_rules['quality_thresholds']['min_experimental_success']
            if exp_success_mean < min_threshold:
                validation_results['quality_passed'] = False
                validation_results['warnings'].append(
                    f"Low experimental success: {exp_success_mean:.3f} < {min_threshold}"
                )

        # Check aromatic content distribution
        if 'sequence' in df.columns:
            aromatic_contents = []
            for seq in df['sequence']:
                aromatic_content = sum(seq.count(aa) for aa in 'FWY') / len(seq)
                aromatic_contents.append(aromatic_content)

            mean_aromatic = np.mean(aromatic_contents)
            validation_results['metrics']['mean_aromatic_content'] = mean_aromatic

            if mean_aromatic < 0.25:
                validation_results['recommendations'].append(
                    f"Consider increasing aromatic content: {mean_aromatic:.3f} < 0.25"
                )

        # Check length distribution
        if 'sequence' in df.columns:
            lengths = [len(seq) for seq in df['sequence']]
            mean_length = np.mean(lengths)
            validation_results['metrics']['mean_length'] = mean_length

            optimal_range = (60, 75)
            if not (optimal_range[0] <= mean_length <= optimal_range[1]):
                validation_results['recommendations'].append(
                    f"Length outside optimal range: {mean_length:.1f} not in {optimal_range}"
                )

        return validation_results

    def generate_submission_report(self, df: pd.DataFrame) -> str:
        """Generate comprehensive submission report."""

        report = []
        report.append("GEM-ADAPTYV RBX-1 FINAL SUBMISSION REPORT")
        report.append("=" * 50)
        report.append("")

        # Basic statistics
        report.append("PORTFOLIO OVERVIEW")
        report.append("-" * 20)
        report.append(f"Total sequences: {len(df)}")

        if 'sequence' in df.columns:
            lengths = [len(seq) for seq in df['sequence']]
            aromatic_contents = [sum(seq.count(aa) for aa in 'FWY')/len(seq) for seq in df['sequence']]

            report.append(f"Length range: {min(lengths)}-{max(lengths)} AA")
            report.append(f"Mean length: {np.mean(lengths):.1f} AA")
            report.append(f"Mean aromatic content: {np.mean(aromatic_contents):.3f}")

        if 'experimental_score' in df.columns:
            report.append(f"Mean experimental success: {df['experimental_score'].mean():.3f}")
            report.append(f"Best experimental success: {df['experimental_score'].max():.3f}")

        if 'competition_score' in df.columns:
            report.append(f"Mean competition score: {df['competition_score'].mean():.3f}")
            report.append(f"Best competition score: {df['competition_score'].max():.3f}")

        report.append("")

        # Validation results
        format_validation = self.validate_competition_format(df)
        sequence_validation = self.validate_sequence_format(df['sequence'].tolist() if 'sequence' in df.columns else [])
        quality_validation = self.validate_portfolio_quality(df)

        report.append("VALIDATION STATUS")
        report.append("-" * 18)
        report.append(f"Format validation: {'PASS' if format_validation['format_valid'] else 'FAIL'}")
        report.append(f"Sequence validation: {'PASS' if len(sequence_validation['invalid_sequences']) == 0 else 'FAIL'}")
        report.append(f"Quality validation: {'PASS' if quality_validation['quality_passed'] else 'FAIL'}")

        if format_validation['errors']:
            report.append("\nFormat errors:")
            for error in format_validation['errors']:
                report.append(f"  - {error}")

        if sequence_validation['invalid_sequences']:
            report.append(f"\nInvalid sequences: {len(sequence_validation['invalid_sequences'])}")
            for invalid in sequence_validation['invalid_sequences'][:5]:  # Show first 5
                report.append(f"  - Index {invalid['index']}: {invalid['issues']}")

        if quality_validation['warnings']:
            report.append("\nQuality warnings:")
            for warning in quality_validation['warnings']:
                report.append(f"  - {warning}")

        if quality_validation['recommendations']:
            report.append("\nRecommendations:")
            for rec in quality_validation['recommendations']:
                report.append(f"  - {rec}")

        report.append("")

        # Top candidates
        if 'competition_score' in df.columns:
            report.append("TOP 10 CANDIDATES")
            report.append("-" * 18)
            top_10 = df.nlargest(10, 'competition_score')
            for i, (_, row) in enumerate(top_10.iterrows(), 1):
                name = row['name'] if 'name' in row else f"Sequence_{i}"
                score = row['competition_score'] if 'competition_score' in row else 0
                exp = row.get('experimental_score', 0)
                length = len(row['sequence']) if 'sequence' in row else 0
                report.append(f"  {i:2d}. {name:<30} Score: {score:.3f} Exp: {exp:.3f} Len: {length}")

        report.append("")
        report.append("SUBMISSION READY FOR GEM-ADAPTYV RBX-1 COMPETITION")

        return "\n".join(report)

def run_final_quality_assurance():
    """Run complete quality assurance pipeline."""

    print("Final Quality Assurance - GEM-Adaptyv RBX-1")
    print("=" * 45)

    qa = FinalQualityAssurance()

    # Load final competition submission
    try:
        df = pd.read_csv('gem_adaptyv_competition_analysis.csv')
        print(f"Loaded final submission: {len(df)} sequences")
    except Exception as e:
        print(f"Error loading submission: {e}")
        return

    # Run all validations
    print("\nRunning comprehensive validation...")

    format_validation = qa.validate_competition_format(df)
    sequence_validation = qa.validate_sequence_format(df['sequence'].tolist())
    quality_validation = qa.validate_portfolio_quality(df)

    # Generate and display report
    report = qa.generate_submission_report(df)
    print(report)

    # Save report
    with open('final_submission_report.txt', 'w') as f:
        f.write(report)

    print(f"\nQuality assurance complete!")
    print(f"Final submission report saved to: final_submission_report.txt")

    # Final validation summary
    all_validations_passed = (
        format_validation['format_valid'] and
        len(sequence_validation['invalid_sequences']) == 0 and
        quality_validation['quality_passed']
    )

    if all_validations_passed:
        print("STATUS: READY FOR COMPETITION SUBMISSION")
    else:
        print("STATUS: ISSUES DETECTED - REVIEW REQUIRED")

    return all_validations_passed

if __name__ == "__main__":
    submission_ready = run_final_quality_assurance()
    if submission_ready:
        print("\nFinal submission validated and ready!")
    else:
        print("\nPlease address validation issues before submission.")