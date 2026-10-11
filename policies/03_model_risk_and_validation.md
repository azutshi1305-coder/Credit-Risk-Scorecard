# Sample Bank — Model Risk and Validation Standards

> **FICTIONAL / ILLUSTRATIVE DOCUMENT.** "Sample Bank" is not a real
> institution. Written for a personal portfolio project demonstrating credit
> scorecard model governance; not a real bank's model risk policy.

## 1. Purpose

This document sets the validation standards the Champion scorecard (and any
Challenger model) must meet before and during production use, and defines
the review triggers that follow from them.

## 2. Discrimination Metrics and Thresholds

Measured on a held-out test set that the model never saw during fitting:

| Metric | Weak / investigate | Acceptable | Strong |
|---|---|---|---|
| AUC | < 0.70 | 0.70 – 0.80 | > 0.80 |
| Gini (= 2*AUC - 1) | < 0.40 | 0.40 – 0.70 | > 0.70 (re-check for leakage above ~0.70) |
| KS | < 0.20 | 0.20 – 0.60 | > 0.60 (re-check above ~0.75) |

A result above the "strong" ceiling is not automatically accepted — it
triggers a leakage review, since real-world credit predictors this strong
are uncommon. The Champion scorecard measured AUC 0.854 / Gini 0.708 / KS
0.557 on test, which was investigated and attributed to legitimate
payment-history signal, not leakage (see model build notes).

## 3. Calibration by Risk Band

Discrimination (ranking good from bad) is necessary but not sufficient — the
model must also be **calibrated**: each risk band's actual observed default
rate must fall inside the band's target PD range on held-out data. This is
checked at every validation cycle. All five bands (A–E) met this bar at
initial validation.

## 4. Population Stability Index (PSI)

PSI measures how much a score distribution has shifted between a reference
population (the development/training sample) and a current population (test,
or — in production — a recent cohort of applicants).

| PSI | Interpretation | Action |
|---|---|---|
| < 0.10 | Stable | None |
| 0.10 – 0.25 | Moderate shift | Investigate drivers; monitor more closely |
| > 0.25 | Significant shift | Formal recalibration or redevelopment review |

In production, PSI should be recomputed on a regular cycle (e.g. monthly)
comparing the live applicant population's score distribution against the
original development sample — not just once at build time.

## 5. Champion vs. Challenger Policy

- The **Champion** is the model actually used for credit decisions. It must
  be the most interpretable model that clears the thresholds in Section 2 —
  currently the WoE logistic regression scorecard.
- A **Challenger** (e.g. a LightGBM model) may be built and benchmarked
  against the Champion using the same train/test split and the same metrics,
  but is not deployed into decisioning. Its purpose is to quantify how much
  accuracy, if any, is being left on the table by using an interpretable
  model, and to sanity-check the Champion's variable rankings.
- A Challenger replaces the Champion only through a formal model-risk review,
  not automatically — even if it scores higher on Section 2's metrics. That
  review must separately satisfy Section 6's explainability requirements and
  the fair lending comparison described in `02_fair_lending_and_adverse_action.md`.
- Every Challenger must be evaluated under the same fair-lending exclusions
  as the Champion (no protected or proxy attributes), so the comparison is
  fair and not just a theoretical accuracy ceiling.

## 6. Explainability Requirements

- The Champion must produce a **reason code** for every declined or
  conditioned application: the variables and bins that cost the applicant
  the most points relative to the best bin, per `01_retail_credit_policy.md`.
- Any Challenger considered for production use must have an equivalent
  per-applicant explanation mechanism (e.g. SHAP values) and a global
  explanation of what drives its predictions, reviewed against the
  Champion's variable rankings for consistency.
- Any material disagreement between the Champion's reason codes and a
  Challenger's explanations for the same applicant must be documented and
  investigated before the Challenger can be considered for promotion.
