from sklearn.model_selection import train_test_split
import pandas as pd


def split_train_test(df: pd.DataFrame, target: str, test_size: float = 0.3, random_state: int = 42):
    """Stratified train/test split so both sets keep the same default rate."""
    train, test = train_test_split(
        df, test_size=test_size, random_state=random_state, stratify=df[target]
    )
    return train, test


if __name__ == "__main__":
    df = pd.read_csv("Data/cs-training-cleaned.csv", index_col=0)
    target = "SeriousDlqin2yrs"

    train, test = split_train_test(df, target)
    print("Train shape:", train.shape, "default rate: {:.4f}".format(train[target].mean()))
    print("Test shape:", test.shape, "default rate: {:.4f}".format(test[target].mean()))
