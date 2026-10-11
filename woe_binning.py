import numpy as np
import pandas as pd

MIN_BIN_SIZE = 0.02  # each numeric bin must hold at least 2% of non-missing rows
MAX_BINS = 10
LOW_CARDINALITY_THRESHOLD = 10  # features with <=10 unique values are binned by raw value

# Heavily right-skewed count variables (dominated by 0/1/2, long thin tail):
# bin on actual value with a capped tail bin instead of quantiles.
COUNT_CAP_FEATURES = {
    "NumberOfTime30-59DaysPastDueNotWorse": 3,
    "NumberOfTimes90DaysLate": 3,
    "NumberOfTime60-89DaysPastDueNotWorse": 3,
    "NumberOfDependents": 3,
    "NumberRealEstateLoansOrLines": 3,
}


def _bin_stats(total, bad):
    """Given per-bin total count and bad count, return woe/iv per bin."""
    good = total - bad
    total_good = good.sum()
    total_bad = bad.sum()
    dist_good = (good / total_good).replace(0, 0.0001)
    dist_bad = (bad / total_bad).replace(0, 0.0001)
    woe = np.log(dist_good / dist_bad)
    iv = (dist_good - dist_bad) * woe
    bad_rate = bad / total
    return pd.DataFrame({
        "total": total, "bad": bad, "good": good,
        "bad_rate": bad_rate, "woe": woe, "iv": iv,
    })


def _initial_bins(values, target, cap=None):
    """Assign each non-missing value to an initial ordered bin label."""
    if cap is not None:
        capped = values.clip(upper=cap)
        bin_id = capped.astype(int)
        labels = capped.astype(int).astype(str)
        labels = labels.where(capped < cap, f"{cap}+")
        return bin_id, labels

    n_unique = values.nunique()
    if n_unique <= LOW_CARDINALITY_THRESHOLD:
        bin_id = values.rank(method="dense").astype(int)
        labels = values.astype(str)
    else:
        bin_id, edges = pd.qcut(values, q=MAX_BINS, labels=False, duplicates="drop", retbins=True)
        bin_id = pd.Series(bin_id, index=values.index) + 1
        labels = pd.qcut(values, q=MAX_BINS, duplicates="drop")
    return bin_id, labels


def _merge_to_monotonic(df_bins, min_count):
    """Iteratively merge adjacent bins (by bin_id order) until bad_rate is
    monotonic and every bin meets the minimum size."""
    df_bins = df_bins.sort_values("bin_id").reset_index(drop=True)

    # decide the expected direction from the two endpoints
    trend = 1 if df_bins["bad_rate"].iloc[-1] >= df_bins["bad_rate"].iloc[0] else -1

    changed = True
    while changed and len(df_bins) > 1:
        changed = False
        for i in range(len(df_bins) - 1):
            violates_trend = (df_bins["bad_rate"].iloc[i + 1] - df_bins["bad_rate"].iloc[i]) * trend < 0
            too_small = (df_bins["total"].iloc[i] < min_count) or (df_bins["total"].iloc[i + 1] < min_count)
            zero_class = (df_bins["bad"].iloc[i] == 0) or (df_bins["bad"].iloc[i] == df_bins["total"].iloc[i])
            if violates_trend or too_small or zero_class:
                merged = pd.DataFrame({
                    "bin_id": [df_bins["bin_id"].iloc[i]],
                    "label": [f'{df_bins["label"].iloc[i]} | {df_bins["label"].iloc[i + 1]}'],
                    "total": [df_bins["total"].iloc[i] + df_bins["total"].iloc[i + 1]],
                    "bad": [df_bins["bad"].iloc[i] + df_bins["bad"].iloc[i + 1]],
                })
                merged["bad_rate"] = merged["bad"] / merged["total"]
                df_bins = pd.concat([
                    df_bins.iloc[:i], merged, df_bins.iloc[i + 2:]
                ]).reset_index(drop=True)
                changed = True
                break
    return df_bins


def woe_iv_table(df: pd.DataFrame, feature: str, target: str) -> pd.DataFrame:
    """Compute a monotonic WoE/IV bin table for one feature. Missing values
    get their own bin and are not subject to monotonic merging."""
    s = df[feature]
    y = df[target]

    missing_mask = s.isna()
    n_non_missing = (~missing_mask).sum()
    min_count = max(1, int(n_non_missing * MIN_BIN_SIZE))

    cap = COUNT_CAP_FEATURES.get(feature)
    bin_id, labels = _initial_bins(s[~missing_mask], y[~missing_mask], cap=cap)
    work = pd.DataFrame({"bin_id": bin_id, "label": labels, "target": y[~missing_mask]})
    grouped = work.groupby("bin_id").agg(total=("target", "size"), bad=("target", "sum"),
                                          label=("label", "first")).reset_index()
    grouped["bad_rate"] = grouped["bad"] / grouped["total"]

    merged = _merge_to_monotonic(grouped, min_count)

    rows = [merged[["label", "total", "bad"]]]
    if missing_mask.any():
        rows.append(pd.DataFrame({
            "label": ["Missing"],
            "total": [missing_mask.sum()],
            "bad": [y[missing_mask].sum()],
        }))
    final = pd.concat(rows, ignore_index=True)

    stats = _bin_stats(final["total"], final["bad"])
    result = pd.concat([final[["label"]], stats], axis=1)
    return result


def iv_summary(df: pd.DataFrame, target: str, features: list) -> pd.DataFrame:
    rows = []
    for f in features:
        table = woe_iv_table(df, f, target)
        rows.append({"feature": f, "iv": table["iv"].sum(), "n_bins": len(table)})
    summary = pd.DataFrame(rows).sort_values("iv", ascending=False).reset_index(drop=True)

    def strength(iv):
        if iv < 0.02:
            return "not predictive"
        if iv < 0.1:
            return "weak"
        if iv < 0.3:
            return "medium"
        if iv < 0.5:
            return "strong"
        return "suspiciously strong"

    summary["strength"] = summary["iv"].apply(strength)
    return summary


if __name__ == "__main__":
    from split_data import split_train_test

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 140)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")

    df = pd.read_csv("Data/cs-training-cleaned.csv", index_col=0)
    target = "SeriousDlqin2yrs"
    features = [c for c in df.columns if c != target]

    train, test = split_train_test(df, target, test_size=0.3, random_state=42)
    print(f"Train: {train.shape[0]} rows (default rate {train[target].mean():.2%})")
    print(f"Test:  {test.shape[0]} rows (default rate {test[target].mean():.2%})")
    print("Bins below are fit on TRAIN only.\n")

    summary = iv_summary(train, target, features)
    print("=== INFORMATION VALUE SUMMARY (ranked, train only) ===")
    print(summary.to_string(index=False))

    print("\n=== WOE TABLE FOR EVERY VARIABLE (train only) ===")
    for f in summary["feature"]:
        print(f"\n--- {f} ---")
        print(woe_iv_table(train, f, target).to_string(index=False))
