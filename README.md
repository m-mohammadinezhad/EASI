# EASI — Quantifying Enterprise Architecture Smells and Debt

EASI is a composite indicator that transforms ArchiMate models into
Enterprise Architecture Knowledge Graphs (EAKGs), detects architectural
smells, and combines local and global indicators into a normalized score.

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/run_analysis.py \
--input models/archisurance_3.1-revised.archimate \
--output results/
