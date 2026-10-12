# Fair Lending and Adverse Action Summary

> **Illustrative document — not legal advice.** This is a plain-language,
> high-level summary written to demonstrate a credit risk scorecard build.
> It is not a substitute for
> legal review and must not be relied on for actual compliance decisions.
> Real institutions must consult qualified counsel and the current text of
> applicable law and regulation.

## 1. Purpose and Disclaimer

This document summarizes, at a plain-language level, two regulatory regimes
that shape how the bank communicates credit decisions, and explains a
design choice made in the scorecard build. It is deliberately simplified for
illustration and omits many details, exceptions, and jurisdiction-specific
rules that would matter in a real implementation.

## 2. RBI Fair Practices Code (India) — Summary

The Reserve Bank of India's Fair Practices Code framework expects regulated
lenders to communicate credit decisions transparently, including conveying
the main reason(s) for rejecting a loan application, in writing, if the
applicant asks. The general spirit is: an applicant whose loan is declined is
entitled to understand, in plain terms, why.

## 3. US ECOA and Regulation B — Summary

The US Equal Credit Opportunity Act (ECOA) and its implementing Regulation B
prohibit credit decisions based on certain protected characteristics,
including **age**, race, color, religion, national origin, sex, marital
status, and receipt of public assistance income. When a creditor takes
"adverse action" (denies an application, or offers materially worse terms),
Regulation B requires a notice stating the **specific principal reasons** for
that action — not a generic refusal. Common industry practice, when a
statistical scoring system is used, is to disclose the small number of
factors (commonly cited as up to about four) that most affected the score —
this is exactly what the scorecard's "reason codes" (built in step 5) and the
challenger model's SHAP explanations (step 7) are designed to produce.

## 4. Why Our Scorecard Excludes Age and Number of Dependents

Two variables with real predictive power — `age` and `NumberOfDependents` —
are deliberately excluded from the production scorecard (see the "fair
lending" model comparison in the model build):

- **Age is an explicitly protected characteristic under ECOA.** Using it
  directly as a scoring input, even if statistically predictive, creates
  direct legal exposure.
- **NumberOfDependents is a proxy variable.** It is not itself a protected
  class, but it correlates strongly with marital and family status, and a
  model that scores on it can disadvantage applicants (for example, single
  parents) in a way regulators scrutinize closely as a form of indirect
  discrimination.

In this build, removing both variables cost only about **0.7% of the
scorecard's Gini** (and, separately, about the same ~0.7% for the LightGBM
challenger) — a small accuracy cost relative to the fair-lending risk
avoided, which is exactly the kind of trade-off a model risk committee would
expect to see documented before approving a scorecard for production use.

## 5. Adverse Action / Rejection Notice — What It Should Contain

For any Refer-to-underwriter-then-decline or Decline outcome, the bank's
notice to the applicant should state, in plain language:

1. That the application was not approved (or was referred and subsequently
   declined).
2. The principal reasons (up to about four), drawn from the scorecard's
   reason codes — i.e., which variables and bins cost the applicant the most
   points relative to the best possible bin for that variable.
3. Any hard policy rule that was triggered (e.g., "utilization above 100%"),
   stated in plain language rather than as an internal rule code.
4. Information on how to request further detail or dispute the decision, per
   applicable law.

Reason codes and rule triggers must never reference age, dependents, or any
other protected characteristic, even indirectly — consistent with Section 4.

**Notice timing for Manual review and Refer to underwriter.** Manual review
and Refer to underwriter are not final decisions, so no adverse action
notice is sent while an application sits in either status — an applicant is
not told "declined" when a human simply hasn't looked at the file yet.
Once the underwriter reaches a final decision:

- **Approve or Approve with conditions:** the standard approval
  communication applies; no adverse action notice is required.
- **Decline:** the standard notice described above applies at that point,
  using the reason codes and triggered rules as they stand after review
  (which may differ from the automated reason codes if the underwriter's
  review changed the picture — e.g. valid delinquency data was obtained that
  the automated score couldn't see).
