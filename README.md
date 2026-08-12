text
# EASI — Quantifying Enterprise Architecture Smells and Debt

EASI (Enterprise Architecture Smell Indicator) is a composite index designed to quantify architectural debt in enterprise systems. By transforming ArchiMate models into Enterprise Architecture Knowledge Graphs (EAKGs), EASI detects structural smells and aggregates them into a normalized score.

## Quick Start

### Prerequisites
- Python 3.x
- A directory containing your `.archimate` models.

### Installation
```bash
pip install -r requirements.txt
Usage
bash
python scripts/run_analysis.py \
  --input models/archisurance_3.1-revised.archimate \
  --output results/
Citation
If you use this implementation in your research, please cite the associated paper:

bibtex
@article{easi2025,
  title={EASI: A Composite Index for Quantifying Enterprise Architecture Smells and Debt},
  author={[Insert Author Names]},
  journal={Information and Software Technology},
  year={2025},
  doi={[Insert DOI]}
}
License
This repository is made available for research and academic use.
