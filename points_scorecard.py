import numpy as np
import pandas as pd

from scorecard_model import run_pipeline, TARGET

ANCHOR_SCORE = 600
ANCHOR_ODDS = 50  # good:bad odds of 50:1 at the anchor score
PDO = 20  # points to double the odds

FACTOR = PDO / np.log(2)
OFFSET = ANCHOR_SCORE - FACTOR * np.log(ANCHOR_ODDS)


def build_points_table(model, transformer, features) -> pd.DataFrame:
    """Turn a fitted logistic-regression-on-WoE model into a points table:
    one row per bin of every variable, plus a Base Points row for the
    intercept. Score = Base Points + sum of the bin points the applicant
    falls into."""
    coefs = model.params
    base_points = round(OFFSET - FACTOR * coefs["const"])

    rows = [{"variable": "Base Points", "bin": "-", "woe": np.nan, "points": base_points}]
    for feature in features:
        coef = coefs[feature]
        info = transformer.info[feature]
        for group_id, woe in info["woe_map"].items():
            points = round(-FACTOR * coef * woe)
            rows.append({
                "variable": feature, "bin": info["label_map"][group_id],
                "woe": woe, "points": points,
            })
    return pd.DataFrame(rows)


def score_applicants(df: pd.DataFrame, transformer, features, points_table: pd.DataFrame):
    """Score every row by looking up its bin in the points table (NOT by
    recomputing a continuous formula) -- this is exactly what a loan
    officer does by hand with a printed scorecard, so the table and the
    score are guaranteed to agree by construction."""
    base_points = points_table.loc[points_table["variable"] == "Base Points", "points"].iloc[0]

    bin_labels = pd.DataFrame(index=df.index)
    for feature in features:
        info = transformer.info[feature]
        s = df[feature]
        missing_mask = s.isna()
        labels = pd.Series(index=df.index, dtype=object)
        labels.loc[missing_mask] = "Missing"

        non_missing = s[~missing_mask]
        if info["type"] == "cap":
            bin_id = non_missing.clip(upper=info["cap"]).astype(int)
        elif info["type"] == "low_card":
            value_to_rank = info["edges"]
            known = sorted(value_to_rank.keys())
            bin_id = non_missing.map(
                lambda v: value_to_rank.get(v, value_to_rank[min(known, key=lambda k: abs(k - v))])
            ).astype(int)
        else:
            bin_id = pd.cut(non_missing, bins=info["edges"], labels=False, include_lowest=True) + 1
        group_id = bin_id.map(info["bin_id_to_group"])
        labels.loc[non_missing.index] = group_id.map(info["label_map"]).values
        bin_labels[feature] = labels

    points_lookup = {
        (row["variable"], row["bin"]): row["points"]
        for _, row in points_table.iterrows()
    }

    points_df = pd.DataFrame(index=df.index)
    for feature in features:
        points_df[feature] = bin_labels[feature].map(lambda b, f=feature: points_lookup[(f, b)])

    total_score = base_points + points_df.sum(axis=1)
    return bin_labels, points_df, total_score, base_points


def reason_codes(points_table: pd.DataFrame, features: list, bin_labels_row: pd.Series, top_n: int = 4):
    """For one applicant, rank variables by how many points they lost
    compared with that variable's BEST possible bin. These are the factors
    an adverse-action notice would cite."""
    reasons = []
    for feature in features:
        var_table = points_table[points_table["variable"] == feature]
        best_points = var_table["points"].max()
        applicant_bin = bin_labels_row[feature]
        applicant_points = var_table.loc[var_table["bin"] == applicant_bin, "points"].iloc[0]
        lost = best_points - applicant_points
        if lost > 0:
            reasons.append({
                "variable": feature, "applicant_bin": applicant_bin,
                "points_lost": lost, "best_bin": var_table.loc[var_table["points"].idxmax(), "bin"],
            })
    reasons.sort(key=lambda r: r["points_lost"], reverse=True)
    return reasons[:top_n]


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    pd.set_option("display.max_rows", None)

    print(f"Factor = {FACTOR:.4f}, Offset = {OFFSET:.4f}")
    print(f"(600 points = 50:1 odds, +20 points doubles the odds)\n")

    result = run_pipeline(verbose=False)
    transformer = result["transformer"]
    model_b = result["model_b"]
    features_b = result["features_b"]
    test = result["test"]

    points_table = build_points_table(model_b, transformer, features_b)
    print("=== POINTS TABLE (Model B, fair lending champion) ===")
    print(points_table.to_string(index=False))

    bin_labels, points_df, total_score, base_points = score_applicants(test, transformer, features_b, points_table)

    # --- validate: table-based score vs. the model's own continuous score ---
    import statsmodels.api as sm
    woe_test = transformer.transform_all(test)[features_b]
    X = sm.add_constant(woe_test, has_constant="add")
    linear_predictor = X.values @ model_b.params.values  # logit(P(bad))
    continuous_score = OFFSET - FACTOR * linear_predictor
    max_diff = np.abs(total_score.values - continuous_score).max()
    print(f"\nMax difference between table score (rounded) and continuous model score: {max_diff:.2f} points")
    print("(small, from rounding each bin to a whole number -- confirms the table faithfully represents the model)")

    print("\n=== LOW-SCORE APPLICANT EXAMPLE ===")
    worst_idx = total_score.idxmin()
    print(f"Applicant id {worst_idx}  |  Actual default: {test.loc[worst_idx, TARGET]}  |  Total score: {total_score[worst_idx]:.0f}")
    print("\nRaw values:")
    print(test.loc[worst_idx, features_b])
    print("\nPoints breakdown:")
    breakdown = pd.DataFrame({
        "bin": bin_labels.loc[worst_idx], "points": points_df.loc[worst_idx],
    })
    print(f"Base Points: {base_points:.0f}")
    print(breakdown.to_string())
    print(f"Sum check: {base_points + points_df.loc[worst_idx].sum():.0f} == {total_score[worst_idx]:.0f}")

    print("\nReason codes (top factors hurting this applicant's score):")
    for r in reason_codes(points_table, features_b, bin_labels.loc[worst_idx]):
        print(f"  - {r['variable']}: applicant is in bin '{r['applicant_bin']}' "
              f"(best bin is '{r['best_bin']}'), costing {r['points_lost']:.0f} points")
