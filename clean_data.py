import pandas as pd

DELINQUENCY_SENTINEL_COLS = [
    "NumberOfTime30-59DaysPastDueNotWorse",
    "NumberOfTimes90DaysLate",
    "NumberOfTime60-89DaysPastDueNotWorse",
]
SENTINEL_THRESHOLD = 96  # 96/98 are placeholder codes, not real counts


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw Give Me Some Credit dataset.

    Steps:
    1. Drop fully duplicated rows.
    2. Replace 96/98 sentinel codes in the delinquency columns with missing.
    3. Replace age < 18 with missing.
    4. Replace DebtRatio with missing where MonthlyIncome is missing
       (there, DebtRatio actually holds a raw debt amount, not a ratio).
    No imputation is performed here; missing values are left for WoE
    binning (step 3) to assign their own bin/bad rate.
    """
    df = df.drop_duplicates()

    sentinel_mask = (df[DELINQUENCY_SENTINEL_COLS] >= SENTINEL_THRESHOLD).any(axis=1)
    df.loc[sentinel_mask, DELINQUENCY_SENTINEL_COLS] = pd.NA

    df.loc[df["age"] < 18, "age"] = pd.NA

    df.loc[df["MonthlyIncome"].isna(), "DebtRatio"] = pd.NA

    return df


if __name__ == "__main__":
    raw = pd.read_csv("Data/cs-training.csv", index_col=0)
    print("Raw shape:", raw.shape)

    cleaned = clean_data(raw)
    print("Cleaned shape:", cleaned.shape)
    print("Rows dropped (duplicates):", raw.shape[0] - cleaned.shape[0])

    print("\nMissing values after cleaning:")
    print(cleaned.isna().sum())

    print("\nSentinel codes remaining >=96:")
    print((cleaned[DELINQUENCY_SENTINEL_COLS] >= SENTINEL_THRESHOLD).sum().sum())

    print("\nage min/max after cleaning:")
    print(cleaned["age"].min(), cleaned["age"].max())

    cleaned.to_csv("Data/cs-training-cleaned.csv")
    print("\nSaved to Data/cs-training-cleaned.csv")
