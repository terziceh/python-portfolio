# CarMax Analysis

# CarMax Purchase Gap Analysis  
Fall 2024 CarMax Analytics Showcase

## Project Overview

This project analyzes CarMax’s customer-level shopping journey data to identify where existing markets have unrealized sales potential and which marketing levers should be prioritized to close those gaps.

Rather than simply predicting purchases, the analysis compares model-expected demand to actual observed purchases at the state level, highlighting markets where customer behavior suggests stronger purchase intent than current outcomes reflect.

---

## Business Question

How should marketing strategy be approached to drive maximum sales depending on location?

This analysis focuses on existing CarMax markets and answers:
- Which states have the most room for improvement?
- Why are those states underperforming relative to predicted demand?
- Which marketing actions are most likely to close the conversion gap?

---

## Analytical Approach

### 1. Purchase Propensity Modeling
A Random Forest classifier is trained to predict the probability that a customer purchases a vehicle. Model inputs include website behavior, campaign touchpoints, financing indicators, and service-related features. Model performance is evaluated using accuracy, precision, and a confusion matrix.

### 2. State-Level Opportunity Identification
Customer-level predictions are aggregated to the state level to compute observed conversion rate, predicted conversion rate, predicted purchases, and actual purchases.

A purchase gap is defined as:

purchase_gap = predicted_purchases − actual_purchases

States with a positive purchase gap represent markets where demand exists but conversions lag.

---

### 3. Diagnosing the Conversion Gap
To understand why certain states underperform, feature averages are compared between high-gap states and all other states. These differences are combined with model feature importance to create a priority score:

priority_score = |behavior difference| × model importance

This identifies features that both differ meaningfully in underperforming states and strongly influence purchase likelihood.

---

## Key Insight: What to Focus On

### Marketing Priority Levers

See: outputs/figures/marketing_priority_levers.png

Interpretation:
High-priority levers are behaviors that the model finds predictive and that are weaker or misaligned in underperforming states. These tend to be conversion-stage signals rather than awareness-stage activity.

Strategic implication:
Increasing traffic alone is unlikely to close the gap. The highest ROI comes from improving financing engagement, service plan attachment, and late-stage digital intent signals.

---

## Outputs

Tables (outputs/tables):
- state_model.csv — State-level predicted vs actual performance
- improvement_states.csv — States with positive purchase gaps
- feature_focus_all.csv — Feature comparison and importance
- marketing_focus.csv — Final ranked marketing levers

Figures (outputs/figures):
- top_gap_states.png — States with the largest sales opportunity
- marketing_priority_levers.png — Key marketing actions to prioritize

---

## Repository Structure

01_carmax_analysis/
- analysis.py
- data/
  - Fall 2024 Dataset.csv
- outputs/
  - figures/
  - tables/
- README.md

---

## How to Run

1. Install dependencies:
pip install pandas numpy matplotlib scikit-learn

2. Place the dataset at:
data/Fall 2024 Dataset.csv

3. Run the analysis:
python analysis.py

All outputs will be automatically saved to the outputs directory.

---

## Data Disclaimer

This dataset is pseudorandomly generated for the CarMax Analytics Showcase. It does not represent real customers, transactions, or business performance.

---

## Key Takeaway

The strongest growth opportunities in existing CarMax markets do not come from increasing traffic or broadening top-of-funnel awareness. Instead, the data shows that many underperforming states already exhibit strong purchase intent—customers are researching vehicles, engaging with marketing, and signaling readiness to buy—but are failing to convert at the final stages of the journey.

By comparing predicted demand to actual purchases, this analysis reveals that the largest sales gains can be achieved by improving conversion efficiency, not volume. Features tied to financing engagement, service plan adoption, and late-stage digital behavior consistently differentiate high-opportunity states and are among the strongest drivers in the purchase propensity model.

The implication is clear:
rather than spending more to attract additional shoppers, CarMax can unlock incremental sales by removing friction at the moment of decision—clarifying financing options, reinforcing service value, and guiding high-intent customers across the finish line. In short, the path to growth is not wider funnels, but stronger closes.
