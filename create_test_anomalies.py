import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_test_data():
    num_rows = 100
    # Start time a couple of hours ago so it shows up in "Today" or "Hour" filters
    start_time = datetime.now() - timedelta(minutes=num_rows)

    # Base normal data (simulating a smooth highway drive)
    data = {
        'TIMESTAMP': [(start_time + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(num_rows)],
        'ENGINE_RPM': np.random.normal(2000, 100, num_rows),
        'VEHICLE_SPEED': np.random.normal(65, 5, num_rows),
        'THROTTLE': np.random.normal(25, 2, num_rows),
        'ENGINE_LOAD': np.random.normal(40, 5, num_rows),
        'COOLANT_TEMPERATURE': np.random.normal(90, 2, num_rows),
        'LONG_TERM_FUEL_TRIM_BANK_1': np.random.normal(0, 1, num_rows),
        'SHORT_TERM_FUEL_TRIM_BANK_1': np.random.normal(0, 1, num_rows),
        'INTAKE_MANIFOLD_PRESSURE': np.random.normal(30, 2, num_rows)
    }

    df = pd.DataFrame(data)

    # --- INJECT SUDDEN SPIKES ---
    
    # 1. Sudden RPM Spike (e.g. accidental rev or slipping gear)
    df.loc[20, 'ENGINE_RPM'] = 6500 
    
    # 2. Coolant Temperature Spike (e.g. sudden overheating)
    df.loc[45, 'COOLANT_TEMPERATURE'] = 135 
    
    # 3. Sudden Speed Drop (e.g. hard braking)
    df.loc[70, 'VEHICLE_SPEED'] = 15 
    
    # 4. Engine Load Spike
    df.loc[85, 'ENGINE_LOAD'] = 98 

    # Round to 2 decimal places for cleaner CSV
    for col in df.columns:
        if col != 'TIMESTAMP':
            df[col] = df[col].round(2)

    output_file = 'test_anomalies.csv'
    df.to_csv(output_file, index=False)
    print(f"Successfully generated '{output_file}' with 100 rows.")
    print("Injected anomalies at:")
    print(f"- Row 20: ENGINE_RPM spiked to {df.loc[20, 'ENGINE_RPM']}")
    print(f"- Row 45: COOLANT_TEMPERATURE spiked to {df.loc[45, 'COOLANT_TEMPERATURE']}")
    print(f"- Row 70: VEHICLE_SPEED dropped to {df.loc[70, 'VEHICLE_SPEED']}")
    print(f"- Row 85: ENGINE_LOAD spiked to {df.loc[85, 'ENGINE_LOAD']}")

if __name__ == "__main__":
    create_test_data()
