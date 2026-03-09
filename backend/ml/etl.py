import pandas as pd
import numpy as np
import io
import os

def load_data(filepath: str) -> pd.DataFrame:
    """Load dataset from CSV, Excel, or JSON."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(filepath)
    elif ext in ['.xlsx', '.xls']:
        df = pd.read_excel(filepath)
    elif ext == '.json':
        df = pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic ETL: Fix types, handle missing values, clean headers."""
    # Standardize headers
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]
    
    # Drop empty columns/rows
    df.dropna(how='all', axis=1, inplace=True)
    df.dropna(how='all', axis=0, inplace=True)
    
    # Simple missing value imputation
    # Numerics -> Mean, Categorical -> Mode
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col].fillna(df[col].mean(), inplace=True)
        else:
            df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown", inplace=True)
            
    # Remove duplicates
    df.drop_duplicates(inplace=True)
    
    return df
