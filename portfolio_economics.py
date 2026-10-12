"""Business view of the scorecard: what each approval cut-off means for the
portfolio, and what each risk band is expected to lose.

Everything is measured on the held-out TEST set (applicants the model never
saw while it was built), using the champion scorecard's scores and bands.

Expected loss follows the standard credit-risk formula

    Expected loss = PD x LGD x EAD

  PD  - probability of default: the observed rate at which applicants in a
        band went 90+ days past due within two years (the dataset's target).
  LGD - loss given default: the share of the balance not recovered after a
        default. ASSUMED at 45%, a common benchmark for unsecured consumer
        lending. Change LGD below to test other assumptions.
  EAD - exposure at default: the balance outstanding when the default
        happens. ASSUMED to equal the amount lent, so results are quoted
        "per 1,000 lent".

Because PD here is a two-year default rate, expected loss is a two-year
figure, not an annual one.
"""
import numpy as np
import pandas as pd

LGD = 0.45          # loss given default (assumption)
PER_AMOUNT = 1000   # results are quoted per this amount lent

BAND_ORDER = ["A", "B", "C", "D", "E"]
BAND_DECISION = {
    "A": "Approve",
    "B": "Approve",
    "C": "Approve with conditions",
    "D": "Refer to underwriter",
    "E": "Decline",
}

# Approval policies compared in the cut-off table: approve every band down to
# and including the named one.
POLICIES = [
    ("A", "Approve band A only"),
    ("B", "Approve bands A–B"),
    ("C", "Approve bands A–C (current policy)"),
    ("D", "Approve bands A–D"),
    ("E", "Approve everyone"),
]
CURRENT_POLICY = "C"


def band_table(bands, y) -> pd.DataFrame:
    """One row per band: share of applicants, observed default rate (PD) and
    expected loss per 1,000 lent."""
    bands = pd.Series(np.asarray(bands, dtype=object))
    y = pd.Series(np.asarray(y, dtype=float))
    rows = []
    for b in BAND_ORDER:
        mask = (bands == b).values
        n = int(mask.sum())
        pd_rate = float(y[mask].mean()) if n else float("nan")
        rows.append({
            "band": b,
            "decision": BAND_DECISION[b],
            "applicants": n,
            "share": n / len(y) if len(y) else float("nan"),
            "pd": pd_rate,
            "el_per_1000": pd_rate * LGD * PER_AMOUNT if n else float("nan"),
        })
    return pd.DataFrame(rows)


def cutoff_table(bands, y, cutoffs: dict) -> pd.DataFrame:
    """One row per approval policy: how many applicants get approved, the
    default rate among them, how many of all eventual defaulters are kept out,
    how many good applicants are turned away, and the expected loss per 1,000
    lent across the approved book."""
    bands = np.asarray(bands, dtype=object)
    y = np.asarray(y, dtype=float)
    n_total, n_bad, n_good = len(y), y.sum(), (1 - y).sum()
    rows = []
    for i, (lowest, label) in enumerate(POLICIES):
        approved = np.isin(bands, BAND_ORDER[: i + 1])
        n_app = int(approved.sum())
        bad_rate = float(y[approved].mean()) if n_app else float("nan")
        rows.append({
            "lowest_band": lowest,
            "policy": label,
            "min_score": cutoffs.get(lowest),            # None for band E (no floor)
            "approval_rate": n_app / n_total if n_total else float("nan"),
            "bad_rate": bad_rate,
            "bads_avoided": float(y[~approved].sum() / n_bad) if n_bad else float("nan"),
            "goods_declined": float((1 - y[~approved]).sum() / n_good) if n_good else float("nan"),
            "el_per_1000": bad_rate * LGD * PER_AMOUNT if n_app else float("nan"),
            "current": lowest == CURRENT_POLICY,
        })
    return pd.DataFrame(rows)


def summarise(bands, y, cutoffs: dict) -> dict:
    """Plain dict (safe to cache, pickle and hand to the PDF builder)."""
    return {
        "lgd": LGD,
        "per_amount": PER_AMOUNT,
        "n_test": int(len(y)),
        "portfolio_bad_rate": float(np.mean(np.asarray(y, dtype=float))),
        "bands": band_table(bands, y).to_dict("records"),
        "cutoffs": cutoff_table(bands, y, cutoffs).to_dict("records"),
    }


if __name__ == "__main__":
    # Print the tables for the real model (needs the full project environment).
    from scorecard_model import run_pipeline, TARGET
    from points_scorecard import build_points_table, score_applicants
    from validate_and_report import assign_bands

    result = run_pipeline(verbose=False)
    pts = build_points_table(result["model_b"], result["transformer"], result["features_b"])
    _, _, scores, _ = score_applicants(result["test"], result["transformer"], result["features_b"], pts)
    bands, cuts = assign_bands(scores)
    s = summarise(bands.astype(str).values, result["test"][TARGET].values, cuts)

    pd.set_option("display.width", 160)
    print(f"Test applicants: {s['n_test']:,}   overall default rate: {s['portfolio_bad_rate']:.2%}   "
          f"LGD assumption: {s['lgd']:.0%}\n")
    print("=== EXPECTED LOSS BY BAND ===")
    print(pd.DataFrame(s["bands"]).to_string(index=False, formatters={
        "share": "{:.1%}".format, "pd": "{:.2%}".format, "el_per_1000": "{:.1f}".format}))
    print("\n=== CUT-OFF TRADE-OFF ===")
    print(pd.DataFrame(s["cutoffs"]).to_string(index=False, formatters={
        "approval_rate": "{:.1%}".format, "bad_rate": "{:.2%}".format, "bads_avoided": "{:.1%}".format,
        "goods_declined": "{:.1%}".format, "el_per_1000": "{:.1f}".format}))
