# GovDeals Sales Analysis

## Overview
This project recreates and automates a multi-year GovDeals auction performance report that was originally built using Excel pivot tables and charts.  
Using Python, the analysis cleans raw GovDeals export data, aggregates key metrics, and generates reusable tables and visualizations.

The goal is to understand:
- which items and categories drive the most revenue,
- which listings receive traffic but fail to convert,
- how revenue split structures impact net sales,
- and how many items must be listed annually to cover overhead costs.

All outputs are generated programmatically from a raw GovDeals CSV file.

---

## Project Structure

03_govdeals_sales_analysis/
├─ data_sample/
│ └─ GovDeals_Data.csv
├─ govdeals_report/
│ ├─ report.py
│ └─ init.py
├─ scripts/
│ └─ run_report.py
├─ outputs/
│ ├─ figures/
│ └─ tables/
├─ requirements.txt
└─ README.md



---

## Key Analyses

### Top 10 Gross Sales Items
Identifies the individual auction items generating the highest gross sales.  
This highlights how a small number of high-value assets account for a large share of revenue.

**Outputs**
- `outputs/figures/top10_gross_sales_items.png`
- `outputs/tables/top10_gross_sales_items.csv`

---

### Top 10 No-Bid Items by Visitors
Shows items that attracted significant visitor traffic but failed to sell.  
These listings represent opportunities to improve pricing strategy, reserve levels, or listing quality.

**Outputs**
- `outputs/figures/top10_no_bid_items_visitors.png`
- `outputs/tables/top10_no_bid_items_visitors.csv`

---

### Highest Net Sales Categories (FY 2022–2024)
Aggregates net results by category across recent fiscal years to identify consistent revenue drivers.

**Outputs**
- `outputs/figures/top10_categories_net_results.png`
- `outputs/tables/top10_categories_net_results.csv`

---

### Revenue Split Comparison
Compares original vs. revised revenue split structures and quantifies their impact on annual net sales.

**Outputs**
- `outputs/figures/split_comparison.png`
- `outputs/tables/split_comparison_by_year.csv`

---

### Items Needed to Reach Overhead
Estimates the number of auction listings required each year to cover an assumed annual overhead cost of $240,000.

**Outputs**
- `outputs/tables/items_needed_for_overhead.csv`

---

## How to Run

Activate the virtual environment from the parent repository:
```bash
source ../.venv/Scripts/activate
setup:
  install_dependencies:
    command: pip install -r requirements.txt

  run_analysis:
    command: python -m scripts.run_report
    output: >
      All tables and charts will be regenerated
      in the outputs/ directory.

tools_and_technologies:
  - Python
  - pandas
  - numpy
  - matplotlib

why_this_project:
  demonstrates:
    - cleaning and handling real-world CSV data with encoding issues
    - translating Excel-based analysis into reproducible Python code
    - automating business reporting workflows
    - presenting results in a clear, portfolio-ready format

git_push:
  working_directory: 03_govdeals_sales_analysis
  commands:
    - git status
    - git add .
    - git commit -m "Add GovDeals sales analysis with automated reports and visualizations"
    - git push

