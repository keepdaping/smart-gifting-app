import pandas as pd

# Load the dataset
file_name = "amazon-products2.xlsx"
df = pd.read_excel(file_name)

# Drop any columns that start with 'Unnamed'
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

print("Dataset loaded successfully!")
print(f"Cleaned rows and columns: {df.shape}")
print("\nActive columns we are keeping:")
print(df.columns.tolist())

# Show first row sample
print("\nFirst row sample:")
print(df[['title', 'brand', 'final_price']].head(1))