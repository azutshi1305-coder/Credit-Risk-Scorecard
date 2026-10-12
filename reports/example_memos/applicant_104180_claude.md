# Credit Memo -- Applicant 104180 (Claude-Generated)

Generated via the Claude API (model: claude-opus-5-5), using only the retrieved policy text provided in the prompt.

---

# Credit Memo: Sample Bank Retail Credit

**Applicant ID:** 104180
**Final decision:** Manual review
**Prepared for:** Underwriter file

*Note on structure:* The retrieved policy text does not include a credit memo template. It does require the memo to record every triggered rule and the band's own reasoning, even when R5 caps the final decision, so the underwriter sees the full picture [3]. This memo is organised to meet that requirement.

---

## 1. Decision Summary

| Item | Result |
|---|---|
| Scorecard score | 399 |
| Risk band | E |
| Automated band decision | Decline |
| Hard policy rules triggered | R5: Missing/invalid delinquency data |
| **Final decision** | **Manual review** |

The automated band decision of Decline has been capped at Manual review under the R5 exception [3].

---

## 2. Score and Risk Band

- A score of 399 falls within Band E (≤ 526). Band E carries a target PD of ≥ 20% and a band decision of Decline [1].
- At initial validation, Band E's observed default rate fell inside its target range on held-out data, as did the rates of all other bands [1][2].

---

## 3. Principal Reason Codes

The four factors that cost the applicant the most points relative to the best bin for each variable:

| # | Factor | Variable / bin | Points lost |
|---|---|---|---|
| 1 | Payment history could not be confirmed (missing or invalid delinquency data on file) | NumberOfTimes90DaysLate / Missing | 56 |
| 2 | High use of available credit compared with credit limits | RevolvingUtilizationOfUnsecuredLines / (0.978, 50708.0] | 55 |
| 3 | Payment history could not be confirmed (missing or invalid delinquency data on file) | NumberOfTime30-59DaysPastDueNotWorse / Missing | 55 |
| 4 | Payment history could not be confirmed (missing or invalid delinquency data on file) | NumberOfTime60-89DaysPastDueNotWorse / Missing | 40 |

Three of the four principal reasons come from missing or invalid delinquency data. The fourth, high revolving utilization, is a separate risk factor based on data that is present.

---

## 4. Hard Policy Rules

**R5: Missing/invalid delinquency data (triggered).** Minimum action: Manual review [3].

- Applications with missing or placeholder delinquency codes were the highest-risk group in the historical data, with an observed bad rate of around 60% or more. Policy treats the absence of valid payment history as a strong risk signal in its own right [3].
- Because valid delinquency data is not on file, the system cannot evaluate R1 (any history of 90+ days late payment) [3].

**R2: Revolving utilization above 100% (not listed as triggered).** The utilization bin spans (0.978, 50708.0], which includes values both below and above 100%. R2 does not appear among the triggered rules, so this memo does not treat the threshold as breached [3]. The underwriter may wish to confirm the actual utilization figure.

---

## 5. Rationale for Manual Review Instead of Decline

- For R1–R4, the final decision is the most conservative of the band decision and each rule's minimum action. R5 is handled differently: it caps the outcome at Manual review even when the band alone indicates Decline [3].
- A missing or invalid delinquency code reflects a data-quality gap from upstream credit bureau reporting. It is not confirmed evidence of poor payment behaviour, and auto-declining on a known data gap is hard to defend to a regulator or the applicant [3].
- Policy accepts that this sends R5 cases to the manual queue, including cases flagged risky for other well-evidenced reasons such as very high utilization [3].

---

## 6. Points for Underwriter Review

1. **Delinquency history.** Under R5, a person must carry out the delinquency-history review; the system cannot perform it [3]. If valid delinquency data is obtained, the reason codes and the overall picture may change from the automated result [4].
2. **Revolving utilization.** High utilization is an independent, evidenced risk factor and remains relevant whatever the outcome of the delinquency review. R5 cases can carry well-evidenced risk factors alongside the data gap [3].
3. **Band context.** The automated score places the applicant in the band with the highest target PD (≥ 20%) [1]. This should be weighed together with any verified data the review produces.
4. **Outcome limits.** No hard rule may produce an automatic Approve or Approve with conditions. Any final outcome must come from the underwriter's review [3].

---

## 7. Applicant Communication

- Manual review is not a final decision, so **no adverse action notice is to be sent** while the application remains in this status [4].
- **If the underwriter approves** (with or without conditions), the standard approval communication applies and no adverse action notice is required [4].
- **If the underwriter declines**, the standard notice applies. It must state in plain language that the application was not approved, give the principal reasons (up to about four), describe any triggered hard rule without internal rule codes, and explain how to request further detail or dispute the decision [4]. The reasons must reflect the position after review, which may differ from the automated reason codes above [4]. Regulation B requires the specific principal reasons, not a generic refusal [5].
