import pandas as pd

from .proposal_store import ensure_workbook, XLSX_PATH

# Backwards compatibility: retain previous constant name
FILE_PATH = XLSX_PATH


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
        print(
            f"❌ Error: '{FILE_PATH.name}' not found in '{FILE_PATH.parent}'. "
            "Creating empty workbook."
        )
        try:
            ensure_workbook()
        except Exception as e:
            print(f"❌ Failed to create workbook: {e}")
        if sheet_name is None:
            return {
                s: pd.DataFrame()
                for s in ("Referenda", "Proposals", "ExecutionResults", "Context")
            }
        # Requested sheet (including "Context") should yield an empty DataFrame
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        if sheet_name is None:
            return {}
        return pd.DataFrame()


def load_first_sheet() -> pd.DataFrame:
    """
    Convenience wrapper – always returns the first sheet as a DataFrame.
    """
    df = load_governance_data(sheet_name=0)      # 0 = first sheet
    # If caller accidentally asked for all sheets, pick the first
    if isinstance(df, dict):
        df = next(iter(df.values()))
    return df


def load_proposals() -> pd.DataFrame:
    """Return the ``Proposals`` worksheet as a DataFrame (empty if missing)."""
    try:
        return load_governance_data(sheet_name="Proposals")
    except Exception:
        return pd.DataFrame()


def load_execution_results() -> pd.DataFrame:
    """Return the ``ExecutionResults`` worksheet as a DataFrame (empty if missing)."""
    try:
        return load_governance_data(sheet_name="ExecutionResults")
    except Exception:
        return pd.DataFrame()


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
