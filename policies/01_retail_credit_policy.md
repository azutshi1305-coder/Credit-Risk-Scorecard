# Sample Bank — Retail Credit Policy

> **FICTIONAL / ILLUSTRATIVE DOCUMENT.** "Sample Bank" is not a real institution.
> This document was written for a personal portfolio project demonstrating a
> credit risk scorecard build. It is not a real bank policy and must not be
> treated as one.

## 1. Purpose and Scope

This policy governs how Sample Bank's Retail Credit team uses the unsecured
consumer credit scorecard to decide, condition, refer, or decline personal
loan applications. It applies to all applications scored by the production
scorecard described in Section 2.

## 2. The Scorecard

The production scorecard ("the Champion") is a logistic regression fitted on
Weight-of-Evidence (WoE) encoded variables, calibrated to a points scale with:

- **600 points = 50:1 good:bad odds**
- **PDO (points to double the odds) = 20**

This gives `Score = Offset + Factor x ln(odds)`, with `Factor = 28.85` and
`Offset = 487.12`. Every applicant's score is the sum of a Base Points amount
plus the points earned from the bin each of their six scorecard variables
falls into (utilization, two past-due counts, debt ratio, real estate loans,
and a third past-due count — see the model documentation for the full points
table). Age and number of dependents are deliberately excluded; see
`02_fair_lending_and_adverse_action.md` for why.

## 3. Risk Bands and Decisions

| Band | Score range | Target PD | Decision |
|---|---|---|---|
| A | >= 599 | < 2% | Approve |
| B | 572 – 598 | 2–5% | Approve |
| C | 551 – 571 | 5–10% | Approve with conditions |
| D | 527 – 550 | 10–20% | Refer to underwriter |
| E | <= 526 | >= 20% | Decline |

Each cut-off score is the **lowest** score that belongs to the band it is
named after — e.g. a score of exactly 527 is Band D, not Band E. Bands are
contiguous integer ranges with no gaps and no overlaps between them; the code
and this table must always be kept in sync (see `assign_bands()` in
`validate_and_report.py`).

These cut-offs are derived directly from the points formula at each PD
boundary, and were validated against held-out test data: every band's actual
default rate fell inside its target range (see `03_model_risk_and_validation.md`).

## 4. Hard Policy Rules (Overrides)

The following rules can move an application to a more conservative outcome
than the band alone would suggest, regardless of score. A rule never makes
the decision *more* lenient than the band.

**No hard rule may ever result in an automatic Approve or Approve with
conditions.** Every rule below floors the outcome at a minimum of "Refer to
underwriter," because the check it requires — an affordability review, an
income verification, a delinquency-history review — has to be carried out by
a person. The system can flag that a check is needed; it cannot perform the
check itself and call the application approved.

| Rule | Condition | Minimum action |
|---|---|---|
| R1 | Any history of 90+ days late payment | Refer to underwriter — cannot be auto-approved |
| R2 | Revolving utilization above 100% | Refer to underwriter |
| R3 | Debt-to-income (DebtRatio) above 50% | Refer to underwriter — affordability check required |
| R4 | Declared monthly income missing | Refer to underwriter — income must be verified |
| R5 | Missing/invalid delinquency data (sentinel codes from data cleaning) | Manual review (see exception below) |

R5 exists because the model build found that applications with missing or
placeholder delinquency codes are themselves the single highest-risk group in
the historical data (around 60%+ observed bad rate) — "we don't have valid
payment history for this applicant" is itself a strong risk signal, not a
gap to quietly ignore.

**R5 exception — capped at Manual review, even in Band E.** For every other
rule, the final decision is the *most conservative* of the band decision and
each triggered rule's minimum action (so a Band A score with R1 triggered
still ends up at Refer to underwriter). R5 is handled differently: even when
the band alone says Decline, R5 caps the outcome at **Manual review** rather
than letting the system auto-decline. The reasoning is deliberate:

- **Why not just let it Decline:** a missing/invalid delinquency code is, by
  construction, a case where the bank doesn't actually know the applicant's
  real payment history — it's a data quality artifact from upstream credit
  bureau reporting, not confirmed evidence of bad behavior. Auto-declining
  someone on the strength of a known data gap is hard to defend to a
  regulator or the applicant, and risks penalizing people for a reporting
  problem that isn't their fault.
- **The trade-off:** this is not free. It adds every R5 case — including
  applicants who are also flagged risky for other, well-evidenced reasons
  (e.g. very high utilization) — to the manual review queue instead of
  resolving them automatically, which costs underwriter time and slows down
  the decision for those applicants. Sample Bank accepts this operational
  cost as the price of not making a fully automated adverse decision on
  incomplete data.
- Other triggered rules (R1–R4) and the band's own reasoning are still
  recorded as context in the credit memo even when R5 caps the final
  decision, so the underwriter doing the manual review sees the full
  picture, not just "R5 triggered."

All triggered rules are recorded as reasons even when they don't change the
final outcome, so the credit memo stays fully transparent about every factor
considered.

## 5. Conditions for Band C ("Approve with conditions") Approvals

A Band C automated decision only stands as "Approve with conditions" when
**no hard rule (R1–R5) is triggered** — per Section 4, any triggered rule
floors the outcome at Refer to underwriter (or Manual review for R5)
regardless of band, so a Band C applicant who also trips R3 or R4 is
referred, not conditionally approved. Band C's conditions are therefore
drawn only from factors outside the hard-rule set, for example:

- A shorter review cycle (e.g. 6-month check-in) for marginal approvals near
  the B/C boundary.
- Any other condition the underwriting team specifically requires for a
  Band C case that isn't already covered by a hard rule.

## 6. Overrides

An underwriter may override the automated decision only with:

1. A written justification referencing the specific band, score, and any
   triggered rules.
2. Sign-off from a second authorized approver for any override that
   *loosens* the automated decision (e.g. approving a Band D referral).
3. Logging of the override in the applicant's file for later model
   monitoring (overrides are tracked as part of ongoing model validation —
   a high override rate is itself a signal the scorecard may need review).

## 7. What a Credit Memo Must Contain

Every credit memo produced for an application must include:

1. Applicant identifier and application date.
2. Final score, risk band, and the band's target PD range.
3. The automated decision and the final decision (if different, with
   override justification).
4. Top reason codes / points breakdown (which variables and bins drove the
   score, consistent with Section 2's points table).
5. Any hard rules triggered (R1–R5) and their required conditions.
6. For adverse decisions (Refer or Decline), the principal reasons in plain
   language suitable for an adverse-action notice (see
   `02_fair_lending_and_adverse_action.md`).
7. Preparer name/system, date, and the policy and model version referenced.
