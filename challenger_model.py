import os
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from split_data import split_train_test
from scorecard_model import run_pipeline, TARGET, FAIR_LENDING_EXCLUDE
from validate_and_report import ks_statistic, predict_proba_bad, BLUE, FIG_DIR

RAW_FEATURES = [
    "RevolvingUtilizationOfUnsecuredLines", "age", "NumberOfTime30-59DaysPastDueNotWorse",
    "DebtRatio", "MonthlyIncome", "NumberOfOpenCreditLinesAndLoans", "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines", "NumberOfTime60-89DaysPastDueNotWorse", "NumberOfDependents",
]
FAIR_RAW_FEATURES = [f for f in RAW_FEATURES if f not in FAIR_LENDING_EXCLUDE]


def train_lightgbm(train: pd.DataFrame, target: str, features: list):
    """Train on the cleaned RAW features (no WoE transform -- LightGBM
    handles missing values and non-linearities natively). A slice of
    train is held out purely for early stopping; the real test set is
    never touched until final evaluation."""
    train_fit, train_val = split_train_test(train, target, test_size=0.15, random_state=42)

    X_fit, y_fit = train_fit[features], train_fit[target]
    X_val, y_val = train_val[features], train_val[target]

    model = lgb.LGBMClassifier(
        n_estimators=1000, learning_rate=0.03, num_leaves=31,
        min_child_samples=50, random_state=42, verbose=-1,
    )
    model.fit(
        X_fit, y_fit, eval_set=[(X_val, y_val)], eval_metric="auc",
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
    )
    return model


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    os.makedirs(FIG_DIR, exist_ok=True)

    df = pd.read_csv("Data/cs-training-cleaned.csv", index_col=0)
    train, test = split_train_test(df, TARGET, test_size=0.3, random_state=42)

    y_test = test[TARGET]

    print("=== Training LightGBM challenger on ALL raw (non-WoE) features (includes age, NumberOfDependents) ===")
    model = train_lightgbm(train, TARGET, RAW_FEATURES)
    print(f"Best iteration (early stopping): {model.best_iteration_}")
    X_test = test[RAW_FEATURES]
    pred_lgb = model.predict_proba(X_test)[:, 1]
    auc_lgb = roc_auc_score(y_test, pred_lgb)
    gini_lgb = 2 * auc_lgb - 1
    ks_lgb = ks_statistic(y_test.values, pred_lgb)

    print("\n=== Training LightGBM fair-lending challenger (excludes age, NumberOfDependents) ===")
    model_fair = train_lightgbm(train, TARGET, FAIR_RAW_FEATURES)
    print(f"Best iteration (early stopping): {model_fair.best_iteration_}")
    X_test_fair = test[FAIR_RAW_FEATURES]
    pred_lgb_fair = model_fair.predict_proba(X_test_fair)[:, 1]
    auc_lgb_fair = roc_auc_score(y_test, pred_lgb_fair)
    gini_lgb_fair = 2 * auc_lgb_fair - 1
    ks_lgb_fair = ks_statistic(y_test.values, pred_lgb_fair)

    champion = run_pipeline(verbose=False)
    pred_champ = predict_proba_bad(champion["model_b"], champion["transformer"], test, champion["features_b"])
    auc_champ, gini_champ = champion["auc_b"], champion["gini_b"]
    ks_champ = ks_statistic(test[TARGET].values, pred_champ)

    print("\n=== CHAMPION vs OFFICIAL CHALLENGER vs ALL-FEATURES REFERENCE (test set) ===")
    comparison = pd.DataFrame({
        "model": [
            "Scorecard (Model B, fair lending, WoE logistic regression) -- CHAMPION",
            "LightGBM (fair lending, excl. age & dependents) -- OFFICIAL CHALLENGER",
            "LightGBM (all raw features, incl. age & dependents) -- reference only",
        ],
        "AUC": [auc_champ, auc_lgb_fair, auc_lgb],
        "Gini": [gini_champ, gini_lgb_fair, gini_lgb],
        "KS": [ks_champ, ks_lgb_fair, ks_lgb],
    })
    print(comparison.to_string(index=False))
    print(f"\nOfficial challenger (fair-lending LightGBM) Gini advantage over scorecard: {gini_lgb_fair - gini_champ:+.4f} ({(gini_lgb_fair - gini_champ) / gini_champ:+.1%} relative)")
    print(f"All-features LightGBM Gini advantage over scorecard: {gini_lgb - gini_champ:+.4f} ({(gini_lgb - gini_champ) / gini_champ:+.1%} relative) -- not usable, uses protected attributes")
    print(f"LightGBM Gini COST of removing age & NumberOfDependents: {gini_lgb - gini_lgb_fair:.4f} ({(gini_lgb - gini_lgb_fair) / gini_lgb:.1%} relative drop)")

    # ================= SHAP (official challenger = fair-lending LightGBM) =================
    print("\n=== Computing SHAP values for the OFFICIAL CHALLENGER (fair-lending LightGBM) ===")
    explainer = shap.TreeExplainer(model_fair)
    shap_values = explainer(X_test_fair)

    plt.figure(figsize=(8, 6))
    shap.summary_plot(shap_values, X_test_fair, show=False, plot_size=None)
    fig = plt.gcf()
    fig.set_size_inches(8, 6)
    ax = fig.axes[0]
    ax.set_title("SHAP Summary -- Fair-Lending LightGBM Challenger (test set)")
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {FIG_DIR}/shap_summary.png")

    # Individual applicant -- same low-score applicant highlighted in step 5
    applicant_id = 104180
    if applicant_id not in X_test_fair.index:
        applicant_id = y_test.index[np.argmax(pred_lgb_fair)]  # fall back to highest-risk applicant
    row_pos = X_test_fair.index.get_loc(applicant_id)

    plt.figure()
    shap.plots.waterfall(shap_values[row_pos], show=False)
    fig = plt.gcf()
    fig.suptitle(f"SHAP Explanation -- Applicant {applicant_id} (Fair-Lending LightGBM predicted PD = {pred_lgb_fair[row_pos]:.1%})", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/shap_individual.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {FIG_DIR}/shap_individual.png (applicant {applicant_id})")
