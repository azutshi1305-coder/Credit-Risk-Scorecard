import os
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from split_data import split_train_test
from scorecard_model import run_pipeline, TARGET
from validate_and_report import ks_statistic, predict_proba_bad, BLUE, FIG_DIR

RAW_FEATURES = [
    "RevolvingUtilizationOfUnsecuredLines", "age", "NumberOfTime30-59DaysPastDueNotWorse",
    "DebtRatio", "MonthlyIncome", "NumberOfOpenCreditLinesAndLoans", "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines", "NumberOfTime60-89DaysPastDueNotWorse", "NumberOfDependents",
]


def train_lightgbm(train: pd.DataFrame, target: str):
    """Train on the cleaned RAW features (no WoE transform -- LightGBM
    handles missing values and non-linearities natively). A slice of
    train is held out purely for early stopping; the real test set is
    never touched until final evaluation."""
    train_fit, train_val = split_train_test(train, target, test_size=0.15, random_state=42)

    X_fit, y_fit = train_fit[RAW_FEATURES], train_fit[target]
    X_val, y_val = train_val[RAW_FEATURES], train_val[target]

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

    print("=== Training LightGBM challenger on raw (non-WoE) features ===")
    model = train_lightgbm(train, TARGET)
    print(f"Best iteration (early stopping): {model.best_iteration_}")

    X_test, y_test = test[RAW_FEATURES], test[TARGET]
    pred_lgb = model.predict_proba(X_test)[:, 1]

    auc_lgb = roc_auc_score(y_test, pred_lgb)
    gini_lgb = 2 * auc_lgb - 1
    ks_lgb = ks_statistic(y_test.values, pred_lgb)

    champion = run_pipeline(verbose=False)
    pred_champ = predict_proba_bad(champion["model_b"], champion["transformer"], test, champion["features_b"])
    auc_champ, gini_champ = champion["auc_b"], champion["gini_b"]
    ks_champ = ks_statistic(test[TARGET].values, pred_champ)

    print("\n=== CHAMPION vs CHALLENGER (test set) ===")
    comparison = pd.DataFrame({
        "model": ["Scorecard (Model B, WoE logistic regression)", "LightGBM (raw features)"],
        "AUC": [auc_champ, auc_lgb],
        "Gini": [gini_champ, gini_lgb],
        "KS": [ks_champ, ks_lgb],
    })
    print(comparison.to_string(index=False))
    print(f"\nLightGBM Gini advantage: {gini_lgb - gini_champ:+.4f} ({(gini_lgb - gini_champ) / gini_champ:+.1%} relative)")

    # ================= SHAP =================
    print("\n=== Computing SHAP values (TreeExplainer) ===")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)

    plt.figure(figsize=(8, 6))
    shap.summary_plot(shap_values, X_test, show=False, plot_size=None)
    fig = plt.gcf()
    fig.set_size_inches(8, 6)
    ax = fig.axes[0]
    ax.set_title("SHAP Summary -- What Drives LightGBM's Predictions (test set)")
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {FIG_DIR}/shap_summary.png")

    # Individual applicant -- same low-score applicant highlighted in step 5
    applicant_id = 104180
    if applicant_id not in X_test.index:
        applicant_id = y_test.index[np.argmax(pred_lgb)]  # fall back to highest-risk applicant
    row_pos = X_test.index.get_loc(applicant_id)

    plt.figure()
    shap.plots.waterfall(shap_values[row_pos], show=False)
    fig = plt.gcf()
    fig.suptitle(f"SHAP Explanation -- Applicant {applicant_id} (LightGBM predicted PD = {pred_lgb[row_pos]:.1%})", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIG_DIR}/shap_individual.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {FIG_DIR}/shap_individual.png (applicant {applicant_id})")
