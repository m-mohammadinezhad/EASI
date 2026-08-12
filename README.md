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
python scr/easi.py \
  --input <path_to_input_directory> \
  --output <path_to_output_file>
Example
For example, to process models located in D:\TestDatasets\00 and save the results to results\easi_results.xlsx, run:  
python easi_evaluation.py \
  --input D:\TestDatasets\00 \
  --output results\easi_results.xlsx

Citation
If you use this implementation in your research, please cite the associated paper:

License
This repository is made available for research and academic use.
