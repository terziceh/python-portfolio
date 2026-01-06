# analysis.py
# CarMax Purchase Gap Analysis (Local / VS Code)
# - Trains RF purchase propensity model
# - Aggregates to state-level predicted vs actual purchases
# - Finds "room for improvement" states (positive gap)
# - Diagnoses marketing levers using (gap difference × feature importance)
# - Saves tables + figures to outputs/

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier


# -----------------------------
# Config (paths are relative to this file)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.getenv(
    "CARMAX_DATA_PATH",
    os.path.join(BASE_DIR, "data", "Fall 2024 Dataset.csv")
)

CONV_BLEND = 0.5
LEAD_BLEND = 0.5
TOP_GAP_N_STATES = 10
TOP_GAP_PROFILE_N = 5
FINAL_MARKETING_N = 6

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_TABLES = os.path.join(OUTPUT_DIR, "tables")
OUTPUT_FIGURES = os.path.join(OUTPUT_DIR, "figures")


# -----------------------------
# Helpers
# -----------------------------
def ensure_dirs():
    os.makedirs(OUTPUT_TABLES, exist_ok=True)
    os.makedirs(OUTPUT_FIGURES, exist_ok=True)


def detect_target_col(frame: pd.DataFrame) -> str:
    candidates = [
        "purchased", "is_purchaser", "purchaser", "purchase_flag",
        "purchase", "buyer", "label", "target", "y",
        "Purchased", "IsPurchaser", "PURCHASED"
    ]
    for c in candidates:
        if c in frame.columns:
            return c

    # fallback: show binary-like columns
    binary_like = []
    for c in frame.columns:
        vals = frame[c].dropna().unique()
        if 1 <= len(vals) <= 3:
            binary_like.append((c, len(vals), list(vals)[:10]))

    msg = ["Could not detect target column automatically.",
           "Binary-like candidate columns:"]
    for c, n, sample in binary_like[:40]:
        msg.append(f" - {c:30} unique={n} sample={sample}")
    raise KeyError("\n".join(msg))


def coerce_binary_target(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(float).round().astype(int)

    s = series.astype(str).str.strip().str.lower()
    mapping = {
        "1": 1, "0": 0,
        "yes": 1, "no": 0,
        "true": 1, "false": 0,
        "purchaser": 1, "non-purchaser": 0,
        "purchase": 1, "no purchase": 0
    }
    out = s.map(mapping)

    # fallback: map top 2 categories
    if out.isna().any():
        cats = s.value_counts().index.tolist()
        if len(cats) >= 2:
            out = s.map({cats[0]: 1, cats[1]: 0})

    return out.fillna(0).astype(int)


def filter_marketing_features(features):
    marketing_keywords = [
        "visit", "touch", "campaign", "email", "click",
        "session", "page", "view", "impression",
        "finance", "service", "plan"
    ]
    return [f for f in features if any(k in f.lower() for k in marketing_keywords)]


# -----------------------------
# Main
# -----------------------------
def main():
    ensure_dirs()

    # Load
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset not found at:\n{DATA_PATH}\n\n"
            "Fix:\n"
            "1) Put the CSV at: <project>/data/Fall 2024 Dataset.csv\n"
            "or\n"
            "2) Set environment variable CARMAX_DATA_PATH to the full CSV path."
        )

    df = pd.read_csv(DATA_PATH)
    df.columns = [c.strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]  # remove index artifact cols

    if "state" not in df.columns:
        raise KeyError("Expected a 'state' column in the dataset.")

    df["state"] = df["state"].astype(str).str.upper().str.strip()

    # Target
    target_col = detect_target_col(df)
    df[target_col] = coerce_binary_target(df[target_col])

    # Features (numeric-only, robust)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    features = [c for c in numeric_cols if c != target_col]
    if len(features) < 2:
        raise ValueError("Not enough numeric features to train a model.")

    X = df[features].fillna(0)
    y = df[target_col].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )

    # Model
    rf = RandomForestClassifier(
        n_estimators=400,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("Model performance:")
    print(" - Accuracy:", round(acc, 4))
    print(" - Precision:", round(prec, 4))
    print(" - Confusion matrix:\n", cm)

    # Probabilities
    df["pred_prob"] = rf.predict_proba(df[features].fillna(0))[:, 1]

    # State aggregation
    state_model = (
        df.groupby("state")
          .agg(
              observed_conversion=(target_col, "mean"),
              avg_pred_prob=("pred_prob", "mean"),
              state_leads=(target_col, "size"),
              actual_purchases=(target_col, "sum")
          )
          .reset_index()
    )

    state_model["blended_conversion"] = (
        CONV_BLEND * state_model["observed_conversion"]
        + (1 - CONV_BLEND) * state_model["avg_pred_prob"]
    )

    avg_state_leads = state_model["state_leads"].mean()
    state_model["assumed_annual_leads"] = (
        LEAD_BLEND * state_model["state_leads"]
        + (1 - LEAD_BLEND) * avg_state_leads
    )

    state_model["predicted_purchases"] = (
        state_model["blended_conversion"] * state_model["assumed_annual_leads"]
    )

    state_model["purchase_gap"] = (
        state_model["predicted_purchases"] - state_model["actual_purchases"]
    )

    improvement_states = (
        state_model[state_model["purchase_gap"] > 0]
        .sort_values("purchase_gap", ascending=False)
        .reset_index(drop=True)
    )

    # Save tables
    state_model.to_csv(os.path.join(OUTPUT_TABLES, "state_model.csv"), index=False)
    improvement_states.to_csv(os.path.join(OUTPUT_TABLES, "improvement_states.csv"), index=False)

    # Plot: top gap states
    top_gap_states = improvement_states.head(TOP_GAP_N_STATES)

    plt.figure(figsize=(10, 5))
    plt.bar(top_gap_states["state"], top_gap_states["purchase_gap"])
    plt.xlabel("State")
    plt.ylabel("Purchase Gap (Predicted − Actual)")
    plt.title("States with the Most Room for Sales Improvement")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FIGURES, "top_gap_states.png"), dpi=200)
    plt.close()

    # Deep dive: top gap profile states
    profile_states = improvement_states.head(TOP_GAP_PROFILE_N)["state"].tolist()

    gap_df = df[df["state"].isin(profile_states)].copy()
    non_gap_df = df[~df["state"].isin(profile_states)].copy()

    # Feature compare
    compare_features = [c for c in features if c != target_col]
    gap_means = gap_df[compare_features].mean()
    non_gap_means = non_gap_df[compare_features].mean()

    feature_compare = pd.DataFrame({
        "gap_states_avg": gap_means,
        "other_states_avg": non_gap_means
    })
    feature_compare["difference"] = feature_compare["gap_states_avg"] - feature_compare["other_states_avg"]
    feature_compare = feature_compare.reset_index().rename(columns={"index": "feature"})

    # Feature importance
    feature_importance = pd.DataFrame({
        "feature": features,
        "importance": rf.feature_importances_
    }).sort_values("importance", ascending=False)

    # Merge + priority score
    feature_focus = (
        feature_compare
        .merge(feature_importance, on="feature", how="left")
        .fillna({"importance": 0})
    )
    feature_focus["priority_score"] = feature_focus["difference"].abs() * feature_focus["importance"]
    feature_focus = feature_focus.sort_values("priority_score", ascending=False)

    feature_focus.to_csv(os.path.join(OUTPUT_TABLES, "feature_focus_all.csv"), index=False)

    # Marketing focus
    marketing_features = filter_marketing_features(feature_focus["feature"].tolist())
    marketing_focus = feature_focus[feature_focus["feature"].isin(marketing_features)].copy()
    marketing_focus = marketing_focus.sort_values("priority_score", ascending=False)

    marketing_focus.to_csv(os.path.join(OUTPUT_TABLES, "marketing_focus.csv"), index=False)

    # Plot: marketing levers
    final_focus = marketing_focus.head(FINAL_MARKETING_N).copy()

    plt.figure(figsize=(10, 5))
    plt.barh(final_focus["feature"], final_focus["priority_score"])
    plt.gca().invert_yaxis()
    plt.xlabel("Priority Score (Behavior Gap × Model Importance)")
    plt.title("Marketing Levers to Focus On to Close the Conversion Gap")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FIGURES, "marketing_priority_levers.png"), dpi=200)
    plt.close()

    # Save a short summary TXT
    with open(os.path.join(OUTPUT_TABLES, "run_summary.txt"), "w", encoding="utf-8") as f:
        f.write("CarMax Purchase Gap Analysis\n")
        f.write(f"DATA_PATH={DATA_PATH}\n")
        f.write(f"TARGET_COL={target_col}\n")
        f.write(f"Accuracy={acc:.4f}\n")
        f.write(f"Precision={prec:.4f}\n\n")
        f.write("Top improvement states (by purchase_gap):\n")
        f.write(top_gap_states[["state", "purchase_gap"]].to_string(index=False))
        f.write("\n\nTop marketing levers:\n")
        f.write(final_focus[["feature", "priority_score"]].to_string(index=False))

    print("\nSaved outputs:")
    print(" - outputs/tables/state_model.csv")
    print(" - outputs/tables/improvement_states.csv")
    print(" - outputs/tables/feature_focus_all.csv")
    print(" - outputs/tables/marketing_focus.csv")
    print(" - outputs/figures/top_gap_states.png")
    print(" - outputs/figures/marketing_priority_levers.png")


if __name__ == "__main__":
    main()
