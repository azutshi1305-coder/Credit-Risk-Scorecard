"""Run the full pipeline locally (needs Data/cs-training-cleaned.csv) and save
everything the Streamlit app needs into models/app_artifacts.pkl, so the app
can be deployed (e.g. Streamlit Community Cloud) without the Kaggle CSVs.

Deliberately saves plain pandas/numpy/dict objects, not library model objects
(no statsmodels results, no LightGBM boosters): those have fragile internal
pickle formats that can break across library versions, while a DataFrame, a
dict, or our own WoeTransformer (a plain class holding only dicts/arrays) load
back reliably as long as the pandas/numpy versions match requirements.txt.

The only non-stdlib class in the pickle is WoeTransformer itself -- unpickling
it just needs scorecard_model.py importable, which it always is (the .py
sources ship with the repo; only Data/*.csv is gitignored).

Run this after any change to the pipeline, then commit the updated pickle:
    python build_artifacts.py
"""
import os
import pickle

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants
from validate_and_report import assign_bands, ks_statistic, predict_proba_bad
from challenger_model import compare_models
import portfolio_economics as pe

ARTIFACT_PATH = "models/app_artifacts.pkl"


def build():
    print("Running the scorecard pipeline (needs Data/cs-training-cleaned.csv)...")
    result = run_pipeline(verbose=False)
    transformer = result["transformer"]
    model_b, features_b = result["model_b"], result["features_b"]
    train, test = result["train"], result["test"]

    print("Building the points table and scoring the test set...")
    points_table = build_points_table(model_b, transformer, features_b)
    _, _, scores, _ = score_applicants(test, transformer, features_b, points_table)
    bands, cutoffs = assign_bands(scores)

    print("Computing champion metrics (Gini/AUC/KS)...")
    pred = predict_proba_bad(model_b, transformer, test, features_b)
    ks = ks_statistic(test[TARGET].values, pred)
    metrics = {"gini": result["gini_b"], "auc": result["auc_b"], "ks": float(ks)}

    print("Training the LightGBM challengers for the model comparison table "
          "(this is the slow part -- only needed once, locally)...")
    comparison = compare_models(train, test, result, verbose=False)["comparison"]

    print("Computing the portfolio cut-off trade-off and expected-loss tables...")
    economics = pe.summarise(bands.astype(str).values, test[TARGET].values, cutoffs)

    artifacts = {
        "transformer": transformer,
        "features_b": features_b,
        "points_table": points_table,
        "score_min": float(scores.min()),
        "score_max": float(scores.max()),
        "cutoffs": cutoffs,
        "metrics": metrics,
        "comparison": comparison,
        "economics": economics,
    }

    os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
    with open(ARTIFACT_PATH, "wb") as f:
        pickle.dump(artifacts, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_kb = os.path.getsize(ARTIFACT_PATH) / 1024
    print(f"\nSaved {ARTIFACT_PATH} ({size_kb:.0f} KB)")
    print(f"  Champion: Gini={metrics['gini']:.4f}  AUC={metrics['auc']:.4f}  KS={metrics['ks']:.4f}")
    print(f"  Score range: {artifacts['score_min']:.0f}-{artifacts['score_max']:.0f}   Cut-offs: {cutoffs}")
    print(f"  Points table: {len(points_table)} rows   Features: {features_b}")
    print(f"  Comparison table:\n{comparison.to_string(index=False)}")


if __name__ == "__main__":
    build()
