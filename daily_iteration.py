#!/usr/bin/env python3
"""
Daily Iteration Script for RBX-1 Binder Design Competition
Run this daily to track progress and implement improvements
"""

import csv
import datetime
import json
import os
from typing import Dict, List, Tuple

def load_current_best() -> List[Tuple[str, str, float]]:
    """Load current best sequences with scores"""
    sequences = []

    if os.path.exists('final_rbx1_submission.csv'):
        with open('final_rbx1_submission.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    score = float(row['Composite_Score'])
                    sequences.append((row['Name'], row['Sequence'], score))
                except (KeyError, ValueError):
                    continue

    return sequences

def analyze_current_performance() -> Dict:
    """Analyze current performance metrics"""
    sequences = load_current_best()

    if not sequences:
        return {"error": "No sequences found"}

    # Extract scores and sequences
    scores = [score for _, _, score in sequences]
    seq_lengths = [len(seq) for _, seq, _ in sequences]

    # Calculate statistics
    performance = {
        "date": datetime.date.today().isoformat(),
        "total_sequences": len(sequences),
        "score_stats": {
            "mean": sum(scores) / len(scores),
            "max": max(scores),
            "min": min(scores),
            "top_10_mean": sum(sorted(scores, reverse=True)[:10]) / 10
        },
        "length_stats": {
            "mean": sum(seq_lengths) / len(seq_lengths),
            "range": f"{min(seq_lengths)}-{max(seq_lengths)}"
        },
        "top_sequences": sorted(sequences, key=lambda x: x[2], reverse=True)[:5]
    }

    return performance

def save_daily_log(performance: Dict):
    """Save daily performance log"""
    log_file = "daily_progress.json"

    # Load existing logs
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = {}

    # Add today's performance
    today = datetime.date.today().isoformat()
    logs[today] = performance

    # Save updated logs
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def generate_daily_report(performance: Dict) -> str:
    """Generate daily performance report"""

    report = f"""
🎯 DAILY PROGRESS REPORT - {performance['date']}

📊 Performance Metrics:
   • Total Sequences: {performance['total_sequences']}
   • Mean Score: {performance['score_stats']['mean']:.3f}
   • Best Score: {performance['score_stats']['max']:.3f}
   • Top 10 Mean: {performance['score_stats']['top_10_mean']:.3f}

📏 Length Distribution:
   • Mean Length: {performance['length_stats']['mean']:.1f} AA
   • Range: {performance['length_stats']['range']} AA

🏆 Top 5 Sequences:"""

    for i, (name, seq, score) in enumerate(performance['top_sequences'], 1):
        report += f"\n   {i}. {name[:20]:<20} Score: {score:.3f} Length: {len(seq)}"

    return report

def suggest_daily_improvements(performance: Dict) -> List[str]:
    """Suggest specific improvements for today"""
    suggestions = []

    current_best = performance['score_stats']['max']
    mean_score = performance['score_stats']['mean']

    # Score-based suggestions
    if current_best < 1.5:
        suggestions.append("🎯 Target: Optimize binding scores - add more aromatic residues (F,W,Y)")

    if mean_score < 1.1:
        suggestions.append("📈 Target: Improve overall quality - enhance druggability scores")

    # Length-based suggestions
    lengths = performance['length_stats']['range'].split('-')
    min_len, max_len = int(lengths[0]), int(lengths[1])

    if max_len > 85:
        suggestions.append("📏 Target: Generate more compact designs (60-75 AA optimal)")

    if min_len < 45:
        suggestions.append("🔗 Target: Ensure minimum stability (45+ AA designs)")

    # General improvements
    suggestions.extend([
        "🔬 Run new RFdiffusion with updated hotspots",
        "🧠 Generate alternative sequences with different temperatures",
        "⚡ Test new binding motifs from literature",
        "🎲 Increase scaffold diversity in next generation"
    ])

    return suggestions[:5]  # Return top 5 suggestions

def calculate_days_until_birthday() -> int:
    """Calculate days until March 20th birthday"""
    today = datetime.date.today()
    birthday = datetime.date(2026, 3, 20)
    return (birthday - today).days

def calculate_days_until_deadline() -> int:
    """Calculate days until competition deadline"""
    today = datetime.date.today()
    deadline = datetime.date(2026, 3, 26)
    return (deadline - today).days

def run_daily_check():
    """Run complete daily check and generate report"""
    print("🔍 Analyzing current performance...")

    # Analyze performance
    performance = analyze_current_performance()

    if "error" in performance:
        print(f"❌ Error: {performance['error']}")
        return

    # Save log
    save_daily_log(performance)

    # Generate report
    report = generate_daily_report(performance)
    print(report)

    # Calculate time remaining
    days_to_birthday = calculate_days_until_birthday()
    days_to_deadline = calculate_days_until_deadline()

    print(f"\n⏰ Timeline:")
    print(f"   • Days until 21st birthday: {days_to_birthday}")
    print(f"   • Days until competition deadline: {days_to_deadline}")

    # Suggest improvements
    suggestions = suggest_daily_improvements(performance)
    print(f"\n💡 Today's Improvement Suggestions:")
    for suggestion in suggestions:
        print(f"   {suggestion}")

    # Save daily report
    report_file = f"daily_logs/daily_report_{performance['date']}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Daily Report - {performance['date']}\n\n")
        f.write(report)
        f.write(f"\n\n## Timeline\n")
        f.write(f"- Days until 21st birthday: {days_to_birthday}\n")
        f.write(f"- Days until competition deadline: {days_to_deadline}\n")
        f.write(f"\n## Improvement Suggestions\n")
        for suggestion in suggestions:
            f.write(f"- {suggestion}\n")

    print(f"\n📄 Daily report saved to: {report_file}")

    return performance

def quick_improvement_cycle():
    """Run a quick improvement cycle"""
    print("\n🚀 Running Quick Improvement Cycle...")

    # This would integrate with the main pipeline
    # For now, provide manual steps
    steps = [
        "1. Run: python generate_binder_sequences.py (with new parameters)",
        "2. Run: python analyze_and_rank_binders_simple.py",
        "3. Compare new scores with current best",
        "4. Update final_rbx1_submission_competition.csv if improved",
        "5. Commit and push changes to GitHub"
    ]

    print("Manual improvement steps:")
    for step in steps:
        print(f"   {step}")

    print("\n🎯 Focus areas for improvement:")
    print("   • Increase aromatic content (F,W,Y) for binding")
    print("   • Optimize length distribution (60-75 AA)")
    print("   • Add more diverse binding motifs")
    print("   • Balance druggability vs binding affinity")

if __name__ == "__main__":
    print("🏆 RBX-1 Daily Iteration Script")
    print("=" * 50)

    # Run daily check
    performance = run_daily_check()

    # Option for quick improvement
    print(f"\n" + "="*50)
    choice = input("Run quick improvement cycle? (y/n): ").lower().strip()

    if choice in ['y', 'yes']:
        quick_improvement_cycle()

    print(f"\n🎉 Daily iteration complete! Keep pushing towards victory! 🏆")