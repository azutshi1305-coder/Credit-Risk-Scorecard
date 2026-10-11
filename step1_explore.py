import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 140)

df = pd.read_csv("Data/cs-training.csv", index_col=0)

print("=" * 60)
print("SHAPE:", df.shape)
print("=" * 60)

print("\n--- DTYPES ---")
print(df.dtypes)

print("\n--- DEFAULT RATE (target = SeriousDlqin2yrs) ---")
print(df["SeriousDlqin2yrs"].value_counts())
print("Default rate: {:.2%}".format(df["SeriousDlqin2yrs"].mean()))

print("\n--- MISSING VALUES ---")
missing = df.isna().sum()
missing_pct = (df.isna().mean() * 100).round(2)
print(pd.DataFrame({"missing_count": missing, "missing_pct": missing_pct}))

print("\n--- DESCRIBE (ALL NUMERIC COLUMNS) ---")
print(df.describe().T)

print("\n--- DUPLICATE ROWS ---")
print("Fully duplicated rows:", df.duplicated().sum())
