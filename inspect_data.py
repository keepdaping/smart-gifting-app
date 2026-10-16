"""Inspect the product catalogue to verify the fields used by the app."""

from gift_data import load_product_catalog


def main():
    dataframe = load_product_catalog()
    print("Dataset loaded successfully!")
    print(f"Cleaned rows and columns: {dataframe.shape}")
    print("\nActive columns we are keeping:")
    print(dataframe.columns.tolist())
    print("\nFirst row sample:")
    print(dataframe[["title", "brand", "final_price"]].head(1))


if __name__ == "__main__":
    main()