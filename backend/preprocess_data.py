import pandas as pd
import numpy as np
import os
import glob
import sqlite3
import joblib
from datetime import datetime, timedelta
import random

def generate_random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    if days_between_dates <= 0:
        days_between_dates = 1
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days, hours=random.randrange(24), minutes=random.randrange(60))
    return random_date

def main():
    dataset_path = 'c:/Users/Deep/Downloads/cardataset'
    all_files = glob.glob(os.path.join(dataset_path, "*.csv"))
    print(f"Found {len(all_files)} CSV files. Parsing...")

    # Load ML models
    behavior_model = joblib.load(os.path.join(dataset_path, 'rf_behavior_model.pkl'))
    health_model = joblib.load(os.path.join(dataset_path, 'rf_health_model.pkl'))
    
    features = [
        'ENGINE_RPM', 'VEHICLE_SPEED', 'THROTTLE', 'ENGINE_LOAD',
        'COOLANT_TEMPERATURE', 'LONG_TERM_FUEL_TRIM_BANK_1',
        'SHORT_TERM_FUEL_TRIM_BANK_1', 'INTAKE_MANIFOLD_PRESSURE'
    ]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365) # 1 year data
    
    dataframes = []
    
    for file in all_files:
        try:
            df = pd.read_csv(file)
            df.columns = [col.strip().replace(' ()', '').replace(' ', '_') for col in df.columns]
            
            # Ensure all required features are present
            missing_features = [f for f in features if f not in df.columns]
            if missing_features:
                continue
                
            # Drop rows where feature values are NaN
            df = df.dropna(subset=features).copy()
            if len(df) == 0:
                continue
                
            # Predict labels using ML models
            X = df[features]
            df['Driver_Behavior'] = behavior_model.predict(X)
            df['Car_Health'] = health_model.predict(X)
            
            # Generate synthetic dates
            base_date = generate_random_date(start_date, end_date)
            
            if 'ENGINE_RUN_TINE' in df.columns:
                df['timestamp'] = df['ENGINE_RUN_TINE'].apply(lambda s: base_date + timedelta(seconds=float(s) if not np.isnan(s) else 0))
            else:
                df['timestamp'] = [base_date + timedelta(seconds=i) for i in range(len(df))]
                
            cols_to_keep = ['timestamp', 'Driver_Behavior', 'Car_Health'] + features
            
            df_slim = df[cols_to_keep]
            dataframes.append(df_slim)
        except Exception as e:
            print(f"Skipping or error reading {file}: {e}")

    if not dataframes:
        print("No valid dataframes found.")
        return

    print("Concatenating data...")
    full_data = pd.concat(dataframes, ignore_index=True)
    
    print(f"Total rows: {len(full_data)}")
    
    db_path = os.path.join(dataset_path, 'backend', 'obd_data.db')
    conn = sqlite3.connect(db_path)
    
    print("Saving to database...")
    full_data.to_sql('obd_metrics', conn, if_exists='replace', index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON obd_metrics (timestamp)")
    conn.commit()
    conn.close()
    print("Database built successfully!")

if __name__ == "__main__":
    main()
