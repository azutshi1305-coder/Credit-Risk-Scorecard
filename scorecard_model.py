import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score

from woe_binning import MIN_BIN_SIZE, MAX_BINS, LOW_CARDINALITY_THRESHOLD, COUNT_CAP_FEATURES, _bin_stats
from split_data import split_train_test

IV_KEEP_THRESHOLD = 0.02
TARGET = "SeriousDlqin2yrs"
FAIR_LENDING_EXCLUDE = ["age", "NumberOfDependents"]


class WoeTransformer:
    """Fits WoE bins on one dataset (e.g. train) and can apply those SAME
    bins to any other dataset (e.g. test). Bins must never be refit on test
    data -- that would leak test information into the model."""

    def __init__(self):
        self.info = {}
        self.iv_ = {}

    def fit(self, df: pd.DataFrame, target: str, features: list) -> "WoeTransformer":
        for feature in features:
            fitted = self._fit_feature(df, feature, target)
            self.info[feature] = fitted
            self.iv_[feature] = fitted["iv"]
        return self

    def _fit_feature(self, df, feature, target):
        s = df[feature]
        y = df[target]
        missing_mask = s.isna()
        non_missing = s[~missing_mask]
        cap = COUNT_CAP_FEATURES.get(feature)

        if cap is not None:
            ftype = "cap"
            edges = None
            bin_id = non_missing.clip(upper=cap).astype(int)
        elif non_missing.nunique() <= LOW_CARDINALITY_THRESHOLD:
            ftype = "low_card"
            edges = {v: i + 1 for i, v in enumerate(sorted(non_missing.unique()))}
            bin_id = non_missing.map(edges)
        else:
            ftype = "quantile"
            bin_id, raw_edges = pd.qcut(non_missing, q=MAX_BINS, labels=False, duplicates="drop", retbins=True)
            bin_id = pd.Series(bin_id, index=non_missing.index) + 1
            raw_edges = raw_edges.copy()
            raw_edges[0], raw_edges[-1] = -np.inf, np.inf  # so test values outside train's range still bin correctly
            edges = raw_edges

        work = pd.DataFrame({"bin_id": bin_id.values, "target": y[~missing_mask].values})
        grouped = work.groupby("bin_id").agg(total=("target", "size"), bad=("target", "sum")).reset_index()
        grouped["bad_rate"] = grouped["bad"] / grouped["total"]
        min_count = max(1, int(len(non_missing) * MIN_BIN_SIZE))

        bin_id_to_group, merged = self._merge_to_monotonic(grouped, min_count)

        final = merged[["group_id", "total", "bad"]].rename(columns={"group_id": "label"})
        if missing_mask.any():
            final = pd.concat([final, pd.DataFrame({
                "label": ["Missing"], "total": [missing_mask.sum()], "bad": [y[missing_mask].sum()],
            })], ignore_index=True)

        stats = _bin_stats(final["total"], final["bad"])
        woe_map = dict(zip(final["label"], stats["woe"]))

        return {
            "type": ftype, "cap": cap, "edges": edges,
            "bin_id_to_group": bin_id_to_group, "woe_map": woe_map, "iv": stats["iv"].sum(),
        }

    @staticmethod
    def _merge_to_monotonic(grouped, min_count):
        grouped = grouped.sort_values("bin_id").reset_index(drop=True)
        grouped["members"] = grouped["bin_id"].apply(lambda x: [x])
        trend = 1 if grouped["bad_rate"].iloc[-1] >= grouped["bad_rate"].iloc[0] else -1

        changed = True
        while changed and len(grouped) > 1:
            changed = False
            for i in range(len(grouped) - 1):
                violates = (grouped["bad_rate"].iloc[i + 1] - grouped["bad_rate"].iloc[i]) * trend < 0
                too_small = (grouped["total"].iloc[i] < min_count) or (grouped["total"].iloc[i + 1] < min_count)
                zero_class = (grouped["bad"].iloc[i] == 0) or (grouped["bad"].iloc[i] == grouped["total"].iloc[i])
                if violates or too_small or zero_class:
                    new_row = pd.DataFrame({
                        "bin_id": [grouped["bin_id"].iloc[i]],
                        "total": [grouped["total"].iloc[i] + grouped["total"].iloc[i + 1]],
                        "bad": [grouped["bad"].iloc[i] + grouped["bad"].iloc[i + 1]],
                        "members": [grouped["members"].iloc[i] + grouped["members"].iloc[i + 1]],
                    })
                    new_row["bad_rate"] = new_row["bad"] / new_row["total"]
                    grouped = pd.concat([grouped.iloc[:i], new_row, grouped.iloc[i + 2:]]).reset_index(drop=True)
                    changed = True
                    break

        grouped["group_id"] = range(len(grouped))
        bin_id_to_group = {}
        for _, row in grouped.iterrows():
            for bid in row["members"]:
                bin_id_to_group[bid] = row["group_id"]
        return bin_id_to_group, grouped

    def transform(self, df: pd.DataFrame, feature: str) -> pd.Series:
        info = self.info[feature]
        s = df[feature]
        missing_mask = s.isna()
        result = pd.Series(np.nan, index=s.index, dtype=float)
        if missing_mask.any():
            result.loc[missing_mask] = info["woe_map"].get("Missing", 0.0)

        non_missing = s[~missing_mask]
        if len(non_missing) == 0:
            return result

        if info["type"] == "cap":
            bin_id = non_missing.clip(upper=info["cap"]).astype(int)
        elif info["type"] == "low_card":
            value_to_rank = info["edges"]
            known = sorted(value_to_rank.keys())

            def to_rank(v):
                if v in value_to_rank:
                    return value_to_rank[v]
                nearest = min(known, key=lambda k: abs(k - v))  # unseen value: snap to nearest trained value
                return value_to_rank[nearest]

            bin_id = non_missing.map(to_rank).astype(int)
        else:
            bin_id = pd.cut(non_missing, bins=info["edges"], labels=False, include_lowest=True) + 1

        group_id = bin_id.map(info["bin_id_to_group"])
        result.loc[non_missing.index] = group_id.map(info["woe_map"]).values
        return result

    def transform_all(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({f: self.transform(df, f) for f in self.info}, index=df.index)


def fit_logistic(woe_df: pd.DataFrame, y: pd.Series, features: list):
    X = sm.add_constant(woe_df[features])
    return sm.Logit(y, X).fit(disp=False)


def fit_with_sign_check(woe_df: pd.DataFrame, y: pd.Series, features: list):
    """Fit logistic regression; if any WoE coefficient is positive (wrong
    sign -- higher WoE means safer, so it should LOWER the odds of default),
    drop the worst offender and refit, until every sign is correct."""
    features = list(features)
    dropped = []
    while True:
        model = fit_logistic(woe_df, y, features)
        coefs = model.params.drop("const")
        wrong = coefs[coefs > 0]
        if wrong.empty:
            return model, features, dropped
        worst = wrong.idxmax()
        dropped.append((worst, float(coefs[worst])))
        features.remove(worst)


def gini_from_auc(auc: float) -> float:
    return 2 * auc - 1


def evaluate(model, transformer: WoeTransformer, df: pd.DataFrame, target: str, features: list):
    woe_df = transformer.transform_all(df)[features]
    X = sm.add_constant(woe_df, has_constant="add")
    pred = model.predict(X)
    auc = roc_auc_score(df[target], pred)
    return auc, gini_from_auc(auc)


if __name__ == "__main__":
    pd.set_option("display.width", 140)

    df = pd.read_csv("Data/cs-training-cleaned.csv", index_col=0)
    all_features = [c for c in df.columns if c != TARGET]

    train, test = split_train_test(df, TARGET, test_size=0.3, random_state=42)

    transformer = WoeTransformer().fit(train, TARGET, all_features)
    kept_features = [f for f, iv in transformer.iv_.items() if iv >= IV_KEEP_THRESHOLD]
    dropped_low_iv = [f for f in all_features if f not in kept_features]
    print("Features kept (IV >= {:.2f}): {}".format(IV_KEEP_THRESHOLD, kept_features))
    print("Features dropped for low IV:", dropped_low_iv if dropped_low_iv else "none")

    woe_train = transformer.transform_all(train)
    y_train = train[TARGET]

    print("\n=== MODEL A: all variables ===")
    model_a, features_a, dropped_a = fit_with_sign_check(woe_train, y_train, kept_features)
    for var, coef in dropped_a:
        print(f"Dropped '{var}' (coef was {coef:.4f}, expected negative) -- refit without it.")
    print(model_a.summary2().tables[1])

    print("\n=== MODEL B: fair lending (excludes age, NumberOfDependents) ===")
    fair_features = [f for f in kept_features if f not in FAIR_LENDING_EXCLUDE]
    model_b, features_b, dropped_b = fit_with_sign_check(woe_train, y_train, fair_features)
    for var, coef in dropped_b:
        print(f"Dropped '{var}' (coef was {coef:.4f}, expected negative) -- refit without it.")
    print(model_b.summary2().tables[1])

    auc_a, gini_a = evaluate(model_a, transformer, test, TARGET, features_a)
    auc_b, gini_b = evaluate(model_b, transformer, test, TARGET, features_b)

    print("\n=== TEST SET PERFORMANCE ===")
    print(f"Model A (all variables)   -- features: {features_a}")
    print(f"  AUC = {auc_a:.4f}   Gini = {gini_a:.4f}")
    print(f"Model B (fair lending)    -- features: {features_b}")
    print(f"  AUC = {auc_b:.4f}   Gini = {gini_b:.4f}")
    print(f"\nGini lost by excluding age & NumberOfDependents: {gini_a - gini_b:.4f} "
          f"({(gini_a - gini_b) / gini_a:.1%} relative drop)")
