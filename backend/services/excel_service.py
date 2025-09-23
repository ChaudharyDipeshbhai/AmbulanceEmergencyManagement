import os
import pandas as pd

def preprocess_ambulance_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes ambulance data from CSV into a consistent DataFrame.
    Expected columns: State, Lat, Long, Emergency_Level, availibility
    """
    df = df.rename(columns={
        'Lat': 'Latitude',
        'Long': 'Longitude',
        'availibility': 'Status'
    })

    # Generate unique IDs
    df['Ambulance_ID'] = [f"AMB_{i+1:03d}" for i in range(len(df))]

    # Normalize availability
    df['Status'] = df['Status'].str.lower().map({
        'yes': 'Available',
        'no': 'Unavailable'
    }).fillna('Unavailable')

    # If 'Category' is missing, just drop it from output
    output_cols = ['Ambulance_ID', 'State', 'Latitude', 'Longitude', 'Emergency_Level', 'Status']

    return df[output_cols]

def load_and_prepare_data(filepath: str, required_columns: list) -> pd.DataFrame:
    """
    Load ambulance data CSV and preprocess it.
    """
    full_path = os.path.join(os.path.dirname(__file__), "..", filepath)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")

    df = pd.read_csv(full_path)

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    return preprocess_ambulance_data(df)
