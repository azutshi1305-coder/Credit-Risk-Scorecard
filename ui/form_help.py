"""Plain-language help for every field on the application form.

Shown through the (?) icon next to each label, so someone who has never seen
a credit application can work out what to enter and how to calculate it.
Streamlit renders this text as Markdown.
"""

HELP = {
    "name": (
        "The applicant's full name, as it should appear on the report.\n\n"
        "It's only printed on the result page and the PDF. It is **not** used in scoring "
        "and is **never** sent to the AI."
    ),
    "reference": (
        "A reference number for this application. One is filled in for you — "
        "change it if you have your own numbering."
    ),
    "utilisation": (
        "**What it is:** how much of the available credit on credit cards and personal "
        "lines of credit is currently being used.\n\n"
        "**How to calculate:** add up the balances on all cards and credit lines, divide by "
        "the total of their credit limits, then multiply by 100.\n\n"
        "**Example:** balances of 15,000 on limits of 50,000 → 15,000 ÷ 50,000 × 100 = **30**.\n\n"
        "Don't include mortgages, car loans or other fixed loans. It can be above 100 if "
        "accounts are over their limit."
    ),
    "late_30_59": (
        "**What it is:** how many times in the last two years a payment was between 30 and 59 "
        "days overdue (and didn't become more overdue than that).\n\n"
        "Count each occasion once. Enter **0** if it never happened."
    ),
    "late_60_89": (
        "**What it is:** how many times in the last two years a payment was between 60 and 89 "
        "days overdue (and didn't become more overdue than that).\n\n"
        "Enter **0** if it never happened."
    ),
    "late_90": (
        "**What it is:** how many times in the last two years a payment was 90 days or more "
        "overdue. Lenders treat this as serious delinquency.\n\n"
        "Enter **0** if it never happened."
    ),
    "history_unavailable": (
        "Tick this if the credit bureau record is missing or can't be trusted. The late-payment "
        "fields are skipped and the application goes to an underwriter for manual review."
    ),
    "income": (
        "**What it is:** total monthly income **before tax**, from all sources "
        "(salary, business income, rent received, pension).\n\n"
        "**Example:** an annual salary of 60,000 → 60,000 ÷ 12 = **5,000** a month."
    ),
    "income_not_declared": (
        "Tick this if the applicant didn't state their income. Debt-to-income can't be worked "
        "out without it, so that field is skipped and income must be verified before approval."
    ),
    "dti": (
        "**What it is:** the share of monthly income that goes on debt payments and other "
        "fixed obligations.\n\n"
        "**How to calculate:** add up all monthly payments (loan instalments, minimum card "
        "payments, rent or mortgage, other regular obligations), divide by gross monthly "
        "income, then multiply by 100.\n\n"
        "**Example:** payments of 1,500 on income of 5,000 → 1,500 ÷ 5,000 × 100 = **30**.\n\n"
        "Above 50 triggers an affordability check."
    ),
    "real_estate": (
        "**What it is:** the number of mortgages and other loans secured on property, "
        "including home-equity lines of credit.\n\n"
        "Enter **0** if the applicant has none."
    ),
}
