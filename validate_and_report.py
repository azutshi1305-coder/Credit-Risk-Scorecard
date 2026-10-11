import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants, FACTOR, OFFSET
from woe_binning import iv_summary

FIG_DIR = "reports/figures"

# --- validated palette (dataviz skill reference instance) ---
BLUE = "#2a78d6"
ORANGE = "#eb6834"
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
MUTED = "#898781"
GREY = "#b3b1aa"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
INK = "#0b0b0b"
SEQ_BLUE_5 = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # steps 250/350/450/550/650, light->dark

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": BASELINE, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": "#52514e", "ytick.color": "#52514e", "grid.color": GRID,
    "axes.grid": True, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10,
})


def predict_proba_bad(model, transformer, df, features):
    woe_df = transformer.transform_all(df)[features]
    X = sm.add_constant(woe_df, has_constant="add")
    return model.predict(X)


def ks_statistic(y_true, values):
    """Max distance between the cumulative distribution of goods and bads
    across the sorted values. Rank-based, so it gives the same number
    whether computed on predicted probability or on the final score."""
    order = np.argsort(values)
    y_sorted = np.asarray(y_true)[order]
    n_bad, n_good = y_sorted.sum(), len(y_sorted) - y_sorted.sum()
    cum_bad = np.cumsum(y_sorted == 1) / n_bad
    cum_good = np.cumsum(y_sorted == 0) / n_good
    return np.max(np.abs(cum_bad - cum_good))


def psi(train_scores, test_scores, n_buckets=10):
    """Population Stability Index: buckets fixed by TRAIN score deciles
    (the reference/development distribution), then compares how much of
    TEST falls in each bucket vs. how much of TRAIN did."""
    edges = np.quantile(train_scores, np.linspace(0, 1, n_buckets + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)

    train_counts = pd.cut(train_scores, bins=edges, include_lowest=True).value_counts().sort_index()
    test_counts = pd.cut(test_scores, bins=edges, include_lowest=True).value_counts().sort_index()

    train_pct = (train_counts / train_counts.sum()).replace(0, 0.0001)
    test_pct = (test_counts / test_counts.sum()).replace(0, 0.0001)
    return float(((test_pct - train_pct) * np.log(test_pct / train_pct)).sum())


def pd_to_score(p):
    return OFFSET + FACTOR * np.log((1 - p) / p)


BAND_DEFS = [
    ("A", 0.00, 0.02, "Approve", "< 2%"),
    ("B", 0.02, 0.05, "Approve", "2-5%"),
    ("C", 0.05, 0.10, "Approve with conditions", "5-10%"),
    ("D", 0.10, 0.20, "Refer to underwriter", "10-20%"),
    ("E", 0.20, 1.01, "Decline", ">= 20%"),
]


def assign_bands(total_score):
    cutoff_02 = round(pd_to_score(0.02))
    cutoff_05 = round(pd_to_score(0.05))
    cutoff_10 = round(pd_to_score(0.10))
    cutoff_20 = round(pd_to_score(0.20))
    edges = [-np.inf, cutoff_20, cutoff_10, cutoff_05, cutoff_02, np.inf]
    labels = ["E", "D", "C", "B", "A"]
    bands = pd.cut(total_score, bins=edges, labels=labels, right=True)
    cutoffs = {"A": cutoff_02, "B": cutoff_05, "C": cutoff_10, "D": cutoff_20}
    return bands, cutoffs


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    os.makedirs(FIG_DIR, exist_ok=True)

    result = run_pipeline(verbose=False)
    transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]
    train, test = result["train"], result["test"]

    points_table = build_points_table(model_b, transformer, features_b)
    _, _, score_train, _ = score_applicants(train, transformer, features_b, points_table)
    bin_labels_test, points_df_test, score_test, base_points = score_applicants(test, transformer, features_b, points_table)

    pred_test = predict_proba_bad(model_b, transformer, test, features_b)
    y_test = test[TARGET].values

    auc = roc_auc_score(y_test, pred_test)
    gini = 2 * auc - 1
    ks = ks_statistic(y_test, pred_test)
    stability = psi(score_train.values, score_test.values)

    print("=== VALIDATION METRICS (test data, Model B champion) ===")
    print(f"AUC  = {auc:.4f}   (0.5 = random, 1.0 = perfect; 0.70-0.80 good, >0.80 strong for credit scorecards)")
    print(f"Gini = {gini:.4f}   (= 2*AUC-1; 0.4-0.6 acceptable, 0.6-0.7 strong, >0.7 very strong -- also re-check for leakage)")
    print(f"KS   = {ks:.4f}   (max separation between good/bad cumulative distributions; 0.20-0.40 acceptable, 0.40-0.60 good, >0.60 very strong)")
    print(f"PSI (train vs test score) = {stability:.4f}   (<0.10 stable, 0.10-0.25 moderate shift (investigate), >0.25 significant shift (recalibrate))")
    print("Note: train/test here are a random split of the SAME population, so PSI near 0 just confirms the split didn't")
    print("introduce an artificial distribution shift -- it is not yet a live production drift check.")

    print("\n=== RISK BANDS ===")
    bands_test, cutoffs = assign_bands(score_test)
    print("Score cut-offs derived from the points formula (Score = Offset + Factor * ln(odds)):")
    print(f"  A: score > {cutoffs['A']}")
    print(f"  B: {cutoffs['B']} < score <= {cutoffs['A']}")
    print(f"  C: {cutoffs['C']} < score <= {cutoffs['B']}")
    print(f"  D: {cutoffs['D']} < score <= {cutoffs['C']}")
    print(f"  E: score <= {cutoffs['D']}")

    rows = []
    for band, lo, hi, decision, target_range in BAND_DEFS:
        mask = bands_test == band
        n = mask.sum()
        share = n / len(bands_test)
        actual_rate = y_test[mask].mean() if n > 0 else np.nan
        within = (lo <= actual_rate < hi) if n > 0 else False
        rows.append({
            "band": band, "decision": decision, "n": n, "share": share,
            "actual_default_rate": actual_rate, "target_range": target_range, "within_target": within,
        })
    band_table = pd.DataFrame(rows)
    print("\n" + band_table.to_string(index=False, formatters={
        "share": "{:.1%}".format, "actual_default_rate": "{:.2%}".format,
    }))

    # ================= CHARTS =================

    # 1. ROC curve
    fpr, tpr, _ = roc_curve(y_test, pred_test)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(fpr, tpr, color=BLUE, linewidth=2, label=f"Model B (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1.5, linestyle="--", label="Random")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC Curve -- Fair Lending Champion Model (test set)")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/roc_curve.png", dpi=150)
    plt.close(fig)

    # 2. Score distribution: defaulters vs non-defaulters, with band cut-offs marked
    fig, ax = plt.subplots(figsize=(8, 5))
    good_scores = score_test[y_test == 0]
    bad_scores = score_test[y_test == 1]
    bins = np.linspace(score_test.min(), score_test.max(), 40)
    ax.hist(good_scores, bins=bins, density=True, color=BLUE, alpha=0.55, label="Non-default")
    ax.hist(bad_scores, bins=bins, density=True, histtype="step", color=ORANGE, linewidth=2, label="Default")

    ymax = ax.get_ylim()[1]
    band_cutoffs = [cutoffs["A"], cutoffs["B"], cutoffs["C"], cutoffs["D"]]
    for cutoff in band_cutoffs:
        ax.axvline(cutoff, color=MUTED, linestyle=":", linewidth=1.2)
    band_regions = [
        ("A", cutoffs["A"], score_test.max()),
        ("B", cutoffs["B"], cutoffs["A"]),
        ("C", cutoffs["C"], cutoffs["B"]),
        ("D", cutoffs["D"], cutoffs["C"]),
        ("E", score_test.min(), cutoffs["D"]),
    ]
    for label, lo, hi in band_regions:
        ax.text((lo + hi) / 2, ymax * 0.97, label, ha="center", va="top", fontsize=10, color="#52514e")

    ax.set_xlabel("Score")
    ax.set_ylabel("Density")
    ax.set_title("Score Distribution by Outcome, with Risk Band Cut-offs (test set)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/score_distribution.png", dpi=150)
    plt.close(fig)

    # 3. Default rate by band
    fig, ax = plt.subplots(figsize=(7, 5))
    band_order = ["A", "B", "C", "D", "E"]
    rates = [band_table.set_index("band").loc[b, "actual_default_rate"] for b in band_order]
    bars = ax.bar(band_order, rates, color=SEQ_BLUE_5)
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{rate:.1%}",
                ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xlabel("Risk band")
    ax.set_ylabel("Actual default rate")
    ax.set_title("Default Rate by Risk Band (test set)")
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/default_rate_by_band.png", dpi=150)
    plt.close(fig)

    # 4. IV bar chart (train, all 10 raw variables) -- colored by champion-model status
    EXCLUSION_REASON = {
        "age": "fair lending", "NumberOfDependents": "fair lending",
        "MonthlyIncome": "wrong sign", "NumberOfOpenCreditLinesAndLoans": "wrong sign",
    }
    df_full = pd.read_csv("Data/cs-training-cleaned.csv", index_col=0)
    all_features = [c for c in df_full.columns if c != TARGET]
    iv_table = iv_summary(train, TARGET, all_features).sort_values("iv")
    colors = [BLUE if f in features_b else GREY for f in iv_table["feature"]]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(iv_table["feature"], iv_table["iv"], color=colors)
    for y, (feature, iv) in enumerate(zip(iv_table["feature"], iv_table["iv"])):
        reason = EXCLUSION_REASON.get(feature)
        if reason:
            ax.text(iv + 0.015, y, reason, va="center", fontsize=8, color=MUTED, style="italic")

    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor=BLUE, label="In champion model"),
        Patch(facecolor=GREY, label="Excluded"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", frameon=False)
    ax.set_xlabel("Information Value")
    ax.set_title("Information Value by Variable (train)")
    ax.set_xlim(0, iv_table["iv"].max() * 1.25)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/iv_bar_chart.png", dpi=150)
    plt.close(fig)

    print(f"\nSaved 4 charts to {FIG_DIR}/")
