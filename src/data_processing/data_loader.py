import pandas as pd
import os

# Define the path to the Excel file
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'input')
FILE_NAME = 'PKD Governance Data.xlsx'
FILE_PATH = os.path.join(DATA_DIR, FILE_NAME)


def load_governance_data(sheet_name=None):
    """
    Loads governance data from an Excel file into a pandas DataFrame or dictionary of DataFrames.

    Parameters:
        sheet_name (str, optional): Specific sheet to load. If None, loads all sheets.

    Returns:
        dict or pd.DataFrame: DataFrame or dictionary of DataFrames containing governance data.
    """
    try:
        df = pd.read_excel(FILE_PATH, sheet_name=sheet_name)
        if isinstance(df, dict):
            print(f"✅ Loaded multiple sheets: {list(df.keys())}")
        else:
            print(f"✅ Loaded sheet '{sheet_name or 'default'}'")
        return df
    except FileNotFoundError:
        print(f"❌ Error: '{FILE_NAME}' not found in '{DATA_DIR}'.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")


def load_first_sheet() -> pd.DataFrame:
    """
    Convenience wrapper – always returns the first sheet as a DataFrame.
    """
    df = load_governance_data(sheet_name=0)      # 0 = first sheet
    # If caller accidentally asked for all sheets, pick the first
    if isinstance(df, dict):
        df = next(iter(df.values()))
    return df


# Quick test
if __name__ == "__main__":
    dfs = load_governance_data()  # Load all sheets by default
    if isinstance(dfs, dict):
        # Print each sheet name and its head
        for sheet, df in dfs.items():
            print(f"\n📄 Sheet: {sheet}")
            print(df.head())
    else:
        print(dfs.head())
