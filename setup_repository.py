#!/usr/bin/env python3
"""
Repository Setup Script for GitHub
Organizes files and creates proper structure
"""

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create organized directory structure"""
    directories = [
        "competition_files",
        "target_analysis",
        "design_pipeline",
        "strategy_docs",
        "data_results",
        "daily_logs",
        "scripts",
        "structures"
    ]

    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ Created directory: {dir_name}")

def organize_files():
    """Move files to appropriate directories"""

    # File organization mapping
    file_moves = {
        # Competition files
        "competition_files": [
            "final_rbx1_submission_competition.csv",
            "final_rbx1_submission.csv",
            "final_rbx1_submission.fasta",
            "COMPETITION_SUBMISSION_PACKAGE.md"
        ],

        # Target analysis
        "target_analysis": [
            "rbx1_sequence.fasta",
            "target_analysis_summary.md"
        ],

        # Design pipeline
        "design_pipeline": [
            "binder_pipeline_design.md"
        ],

        # Strategy documents
        "strategy_docs": [
            "COMPETITION_STRATEGY.md",
            "ULTRA_HIGH_SUCCESS_STRATEGY.md",
            "PRACTICAL_99_PERCENT_PLAN.md",
            "FINAL_EXECUTION_ROADMAP.md",
            "FINAL_COMPETITION_SUMMARY.md",
            "EXECUTION_CHECKLIST.md",
            "IMPLEMENTATION_WORKAROUNDS.md"
        ],

        # Data and results
        "data_results": [
            "rbx1_binder_submission.csv",
            "rbx1_binder_submission.fasta"
        ],

        # Scripts
        "scripts": [
            "generate_binder_sequences.py",
            "analyze_and_rank_binders_simple.py",
            "analyze_and_rank_binders.py",
            "daily_iteration.py"
        ],

        # Structures
        "structures": [
            "1LDJ.cif", "1U6G.cif", "2HYE.cif", "2LGV.cif", "4F52.cif"
        ]
    }

    # Move files
    moved_count = 0
    for directory, files in file_moves.items():
        for filename in files:
            if os.path.exists(filename):
                try:
                    dest_path = Path(directory) / filename
                    shutil.move(filename, dest_path)
                    print(f"✓ Moved {filename} → {directory}/")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ Failed to move {filename}: {e}")

    print(f"\n✓ Organized {moved_count} files into directories")

    # Move directories if they exist
    dir_moves = {
        "target_analysis": ["targets", "cleaned"],
        "design_pipeline": ["designs", "sequences"],
        "data_results": ["analysis", "predicted", "quality", "properties", "clustering", "binding"]
    }

    for dest_dir, source_dirs in dir_moves.items():
        for source_dir in source_dirs:
            if os.path.exists(source_dir):
                try:
                    dest_path = Path(dest_dir) / source_dir
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.move(source_dir, dest_path)
                    print(f"✓ Moved {source_dir}/ → {dest_dir}/{source_dir}/")
                except Exception as e:
                    print(f"✗ Failed to move directory {source_dir}: {e}")

def create_gitignore():
    """Create appropriate .gitignore file"""
    gitignore_content = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.pytest_cache/

# Virtual environments
venv/
.venv/
env/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Large structure files (keep some key ones)
*.pdb
!targets/*.pdb

# Temporary files
*.tmp
*.temp
temp_*

# Logs
*.log

# Output files that change frequently
temp_designs/
scratch/
test_output/

# Keep important results but ignore temporary analysis
daily_logs/*.json
!daily_logs/daily_progress.json
"""

    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    print("✓ Created .gitignore file")

def create_github_setup_script():
    """Create script for GitHub setup"""
    setup_script = """#!/bin/bash
# GitHub Repository Setup Script

echo "🏆 Setting up RBX-1 Competition Repository"

# Initialize git if not already done
if [ ! -d ".git" ]; then
    git init
    echo "✓ Initialized git repository"
fi

# Add remote if not exists
if ! git remote | grep -q "origin"; then
    git remote add origin https://github.com/pkaysantana/GEM-Adaptyv-RBX-1-2026.git
    echo "✓ Added GitHub remote"
fi

# Stage all files
git add .
echo "✓ Staged all files"

# Create initial commit
git commit -m "🚀 Initial commit: Competition-ready RBX-1 binders + daily iteration setup

- 100 optimized binder sequences ready for submission
- Multi-epitope design strategy (40-45% expected success)
- Daily iteration pipeline for continuous improvement
- Complete documentation and analysis tools
- 17 days until 21st birthday optimization deadline"

echo "✓ Created initial commit"

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push -u origin main || git push -u origin master

echo ""
echo "🎉 Repository setup complete!"
echo "🎯 Next steps:"
echo "   1. Run daily_iteration.py each day"
echo "   2. Implement suggested improvements"
echo "   3. Commit and push daily progress"
echo "   4. Optimize until March 20th birthday!"
echo "   5. Submit final version by March 26th"
echo ""
echo "🏆 Ready to win the competition!"
"""

    with open('setup_github.sh', 'w') as f:
        f.write(setup_script)

    # Make it executable
    os.chmod('setup_github.sh', 0o755)
    print("✓ Created setup_github.sh script")

def create_quick_start_guide():
    """Create quick start guide"""
    guide = """# 🚀 Quick Start Guide

## Daily Workflow (17 days until birthday!)

### Every Morning (5 min):
```bash
python scripts/daily_iteration.py
```

### Improvement Session (1-2 hours):
1. Review daily report
2. Implement 1-2 suggested improvements
3. Test new sequences
4. Update best results

### Evening Commit (5 min):
```bash
git add .
git commit -m "Day X improvements: [brief description]"
git push
```

## Key Files to Work With:

- **Main submission**: `competition_files/final_rbx1_submission_competition.csv`
- **Sequence generator**: `scripts/generate_binder_sequences.py`
- **Analysis pipeline**: `scripts/analyze_and_rank_binders_simple.py`
- **Daily tracker**: `scripts/daily_iteration.py`

## Improvement Targets:

- **Current best score**: 1.334
- **Target by birthday**: 1.5+
- **Stretch goal**: 1.8+

## Competition Timeline:

- **March 20**: 21st birthday - final optimization
- **March 26**: Competition deadline
- **April 26**: Results announcement at Rio de Janeiro

## Success Metrics:

- Binding score >2.5
- Druggability >0.95
- Structural quality >0.85
- Overall diversity maintained

## Quick Commands:

```bash
# Check current status
python scripts/daily_iteration.py

# Generate new sequences
python scripts/generate_binder_sequences.py

# Analyze and rank
python scripts/analyze_and_rank_binders_simple.py

# Commit progress
git add . && git commit -m "Daily improvement" && git push
```

🎯 **Goal**: Win $1,000 prize + scientific recognition!
"""

    with open('QUICK_START.md', 'w') as f:
        f.write(guide)
    print("✓ Created QUICK_START.md guide")

if __name__ == "__main__":
    print("🔧 Setting up repository structure...")
    print("=" * 50)

    # Create directory structure
    create_directory_structure()
    print()

    # Organize files
    organize_files()
    print()

    # Create supporting files
    create_gitignore()
    create_github_setup_script()
    create_quick_start_guide()

    print("\n" + "=" * 50)
    print("✅ Repository setup complete!")
    print()
    print("🚀 Next steps:")
    print("   1. Run: ./setup_github.sh")
    print("   2. Start daily iterations!")
    print("   3. Win the competition! 🏆")
    print()
    print("📅 17 days until birthday optimization deadline!")