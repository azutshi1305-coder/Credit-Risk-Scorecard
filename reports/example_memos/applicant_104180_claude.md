# Credit Memo -- Applicant 104180 (Claude-Generated)

Generated via the Claude API (model: claude-opus-5-5), using only the retrieved policy text provided in the prompt.

---

# Credit Memo: Retail Credit

## 1. Application Details
| Field | Value |
|---|---|
| Applicant ID | 104180 |
| Application date | *Not provided in input. Underwriter to complete.* |

## 2. Score and Risk Band
| Field | Value |
|---|---|
| Final score | 399 |
| Risk band | E (score range ≤ 526) [1] |
| Band target PD | ≥ 20% [1] |

At initial validation, all bands (A–E) had observed default rates within their target PD ranges on held-out data [2].

## 3. Decision
| Field | Value |
|---|---|
| Automated band decision | Decline [1] |
| Final decision | **Manual review** |

**Override justification:** Hard rule R5 (missing/invalid delinquency data) was triggered. Under the R5 exception, the outcome is capped at Manual review even in Band E, rather than auto-declining [3]. A missing or invalid delinquency code means the bank does not know the applicant's actual payment history. It is treated as a data quality artifact from upstream credit bureau reporting, not confirmed evidence of poor payment behaviour. Auto-declining on a known data gap is considered hard to defend [3].

The Band E result and all reason codes below are recorded as context for the reviewing underwriter [3].

## 4. Top Reason Codes / Points Breakdown
| # | Variable | Bin | Points lost vs. best bin | Plain-language reason |
|---|---|---|---|---|
| 1 | NumberOfTimes90DaysLate | Missing | 56 | Payment history could not be confirmed (missing or invalid delinquency data on file) |
| 2 | RevolvingUtilizationOfUnsecuredLines | (0.978, 50708.0] | 55 | High use of available credit compared with credit limits |
| 3 | NumberOfTime30-59DaysPastDueNotWorse | Missing | 55 | Payment history could not be confirmed (missing or invalid delinquency data on file) |
| 4 | NumberOfTime60-89DaysPastDueNotWorse | Missing | 40 | Payment history could not be confirmed (missing or invalid delinquency data on file) |

Three of the four reason codes (151 points combined) come from missing delinquency data. The fourth (55 points) reflects high revolving utilization, which is a separate and evidenced risk factor.

## 5. Hard Policy Rules Triggered
| Rule | Condition | Required minimum action |
|---|---|---|
| R5 | Missing/invalid delinquency data (sentinel codes from data cleaning) | Manual review [3] |

**Underwriter notes:**
- Applications with missing or placeholder delinquency codes were the highest-risk group in the historical model build data, with an observed bad rate of around 60%+. Policy treats this as a strong risk signal in its own right [3].
- The manual review should include a delinquency-history review. This check must be carried out by a person [3].
- The utilization bin includes values above 100%, but R2 (revolving utilization above 100%) is not reported as triggered. The underwriter should confirm the actual utilization figure. If it exceeds 100%, R2 applies, and its minimum action is Refer to underwriter [3].
- No hard rule may result in an automatic Approve or Approve with conditions [3].

## 6. Principal Reasons for Adverse-Action Purposes
No adverse action notice is to be sent while the application is in Manual review, because this is not a final decision [4].

If the underwriter's final decision is **Decline**, the notice must state in plain language [4]:
1. That the application was not approved.
2. The principal reasons, up to about four, drawn from the reason codes as they stand after review. Based on the current automated results, these would be:
   - Payment history could not be confirmed (missing or invalid delinquency data on file).
   - High use of available credit compared with credit limits.
3. Any triggered hard rule, in plain language rather than as a rule code. For example: "valid payment history information was not available."
4. How to request further detail or dispute the decision, per applicable law.

These reasons may differ after review. For example, valid delinquency data obtained during review would replace the "could not be confirmed" reasons [4]. Disclosing the specific principal reasons, rather than a generic refusal, is consistent with Regulation B requirements [5].

If the final decision is **Approve** or **Approve with conditions**, the standard approval communication applies and no adverse action notice is required [4].

## 7. Preparation Details
| Field | Value |
|---|---|
| Preparer / system | *Not provided in input. To be completed.* |
| Memo date | *Not provided in input. To be completed.* |
| Policy references | 01_retail_credit_policy.md (Sections 3, 4, 7); 02_fair_lending_and_adverse_action.md (Sections 3, 5); 03_model_risk_and_validation.md (Section 3) |
| Policy / model version | *Not provided in input. To be completed.* |
