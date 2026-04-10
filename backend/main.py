from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
import traceback
from datetime import datetime, timedelta, date

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'obd_data.db')
ML_MODELS_PATH = os.path.dirname(os.path.dirname(__file__))

# Load ML Models — captured explicitly so upload gives a clear error
behavior_model = None
health_model = None
MODELS_LOAD_ERROR = None

try:
    import joblib
    behavior_model = joblib.load(os.path.join(ML_MODELS_PATH, 'rf_behavior_model.pkl'))
    health_model = joblib.load(os.path.join(ML_MODELS_PATH, 'rf_health_model.pkl'))
    print("✅ ML Models loaded successfully.")
except Exception as e:
    MODELS_LOAD_ERROR = str(e)
    print(f"❌ ML Models failed to load: {e}")
    print("   → Install scikit-learn: pip install scikit-learn joblib")

FEATURES = [
    'ENGINE_RPM', 'VEHICLE_SPEED', 'THROTTLE', 'ENGINE_LOAD',
    'COOLANT_TEMPERATURE', 'LONG_TERM_FUEL_TRIM_BANK_1',
    'SHORT_TERM_FUEL_TRIM_BANK_1', 'INTAKE_MANIFOLD_PRESSURE'
]

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Ensure the obd_metrics table exists with the full correct schema.
    If the table exists but is missing columns (stale schema), drop and recreate it.
    """
    expected_cols = {'timestamp', 'Driver_Behavior', 'Car_Health'} | set(FEATURES)
    conn = get_db_connection()
    try:
        cursor = conn.execute("PRAGMA table_info(obd_metrics)")
        existing = {row[1] for row in cursor.fetchall()}
        if existing and not expected_cols.issubset(existing):
            print(f"⚠️  Schema mismatch detected. Dropping old obd_metrics table. Missing: {expected_cols - existing}")
            conn.execute("DROP TABLE IF EXISTS obd_metrics")
            conn.commit()
            existing = set()
        if not existing:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS obd_metrics (
                    timestamp       TIMESTAMP,
                    Driver_Behavior TEXT,
                    Car_Health      TEXT,
                    ENGINE_RPM                  REAL,
                    VEHICLE_SPEED               REAL,
                    THROTTLE                    REAL,
                    ENGINE_LOAD                 REAL,
                    COOLANT_TEMPERATURE         REAL,
                    LONG_TERM_FUEL_TRIM_BANK_1  REAL,
                    SHORT_TERM_FUEL_TRIM_BANK_1 REAL,
                    INTAKE_MANIFOLD_PRESSURE    REAL
                )
            """)
            conn.commit()
            print("✅ obd_metrics table initialised with full schema.")
        else:
            print("✅ obd_metrics table schema verified.")
    finally:
        conn.close()

init_db()

def get_time_format(group_by: str):
    if group_by == 'hour':
        return '%Y-%m-%d %H:00:00'
    elif group_by == 'day':
        return '%Y-%m-%d'
    elif group_by == 'week':
        return '%Y-W%W'
    elif group_by == 'month':
        return '%Y-%m'
    return '%Y-%m-%d'

@app.route("/api/upload", methods=["POST"])
def upload_file():
    # Guard: models must be loaded
    if behavior_model is None or health_model is None:
        return jsonify({
            'error': f'ML models not loaded. Please install dependencies: pip install scikit-learn joblib. Details: {MODELS_LOAD_ERROR}'
        }), 503

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are accepted'}), 400

    try:
        df = pd.read_csv(file)

        # ── Detect real timestamp BEFORE column normalisation ─────────────────
        # The CSV may already have a 'timestamp' column with real datetime values.
        # We must detect it now (case-insensitive) before normalisation upper-cases it,
        # because afterwards we can't tell if 'TIMESTAMP' was synthetic or real.
        has_real_timestamp = any(c.strip().lower() == 'timestamp' for c in df.columns)

        # Normalize column names: strip whitespace, remove " ()", replace spaces with _
        df.columns = [
            col.strip()
               .replace(' ()', '')
               .replace('()', '')
               .replace(' ', '_')
               .upper()
            for col in df.columns
        ]

        # Check for required ML features
        missing_features = [f for f in FEATURES if f not in df.columns]
        if missing_features:
            return jsonify({
                'error': f"CSV is missing required columns: {missing_features}",
                'found_columns': list(df.columns)
            }), 400

        # Drop rows with NaN in required features
        df = df.dropna(subset=FEATURES).copy()
        if len(df) == 0:
            return jsonify({'error': 'No valid rows remain after removing rows with missing values'}), 400

        # Run ML classification
        X = df[FEATURES].astype(float)
        df['Driver_Behavior'] = behavior_model.predict(X)
        df['Car_Health'] = health_model.predict(X)

        # ── Timestamp resolution (priority order) ────────────────────────────
        # Priority 1: CSV already has a real 'timestamp' column → parse & use it directly ✅
        # Priority 2: ENGINE_RUN_TINE (seconds since engine start) → anchor to today midnight
        # Priority 3: Fallback → synthetic 1-row-per-second from today midnight
        if has_real_timestamp and 'TIMESTAMP' in df.columns:
            df['timestamp'] = pd.to_datetime(df['TIMESTAMP'], errors='coerce')
            bad_count = df['timestamp'].isna().sum()
            if bad_count > 0:
                print(f"⚠️  {bad_count} rows had unparseable TIMESTAMP values — they will have NaT")
            print(f"✅ Using real TIMESTAMP from CSV: {df['timestamp'].min()} → {df['timestamp'].max()}")
        elif 'ENGINE_RUN_TINE' in df.columns:
            session_anchor = datetime.combine(date.today(), datetime.min.time())
            df['timestamp'] = df['ENGINE_RUN_TINE'].apply(
                lambda s: session_anchor + timedelta(seconds=float(s) if pd.notna(s) else 0)
            )
            print(f"ℹ️  Synthesised timestamps from ENGINE_RUN_TINE anchored to today midnight.")
        else:
            session_anchor = datetime.combine(date.today(), datetime.min.time())
            df['timestamp'] = [session_anchor + timedelta(seconds=i) for i in range(len(df))]
            print(f"ℹ️  No timestamp source found — using synthetic 1-row/sec timestamps.")
        # ─────────────────────────────────────────────────────────────────────

        # Keep only what we store
        cols_to_keep = ['timestamp', 'Driver_Behavior', 'Car_Health'] + FEATURES
        df_slim = df[cols_to_keep]

        # Write to SQLite
        conn = get_db_connection()
        try:
            df_slim.to_sql('obd_metrics', conn, if_exists='append', index=False)
            conn.commit()
        finally:
            conn.close()

        return jsonify({
            'message': f'Successfully classified and stored {len(df_slim):,} readings using Random Forest models.',
            'rows': len(df_slim)
        }), 200

    except Exception as e:
        err_trace = traceback.format_exc()
        print(f"UPLOAD ERROR:\n{err_trace}")
        return jsonify({'error': str(e), 'trace': err_trace}), 500

@app.route("/api/summary", methods=["GET"])
def get_summary():
    conn = get_db_connection()
    try:
        health_counts = pd.read_sql("SELECT Car_Health, COUNT(*) as count FROM obd_metrics GROUP BY Car_Health", conn)
        behavior_counts = pd.read_sql("SELECT Driver_Behavior, COUNT(*) as count FROM obd_metrics GROUP BY Driver_Behavior", conn)
        
        return jsonify({
            "health": health_counts.set_index('Car_Health')['count'].to_dict(),
            "behavior": behavior_counts.set_index('Driver_Behavior')['count'].to_dict()
        })
    finally:
        conn.close()

@app.route("/api/averages", methods=["GET"])
def get_averages():
    group_by = request.args.get('group_by', 'day')
    specific_date = request.args.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    conn = get_db_connection()
    try:
        # If specific date is selected, bounds are exact.
        if specific_date:
            span_label = f"For {specific_date}"
            health_df = pd.read_sql(f"SELECT Car_Health, COUNT(*) as count FROM obd_metrics WHERE strftime('%Y-%m-%d', timestamp) = '{specific_date}' GROUP BY Car_Health", conn)
            behavior_df = pd.read_sql(f"SELECT Driver_Behavior, COUNT(*) as count FROM obd_metrics WHERE strftime('%Y-%m-%d', timestamp) = '{specific_date}' GROUP BY Driver_Behavior", conn)
        else:
            # Get the latest timestamp in the DB
            max_ts_df = pd.read_sql("SELECT MAX(timestamp) as max_ts FROM obd_metrics", conn)
            max_ts_str = max_ts_df['max_ts'].iloc[0]
            
            if not max_ts_str:
                return jsonify({
                    "avg_good_behavior_ratio": 0,
                    "avg_neutral_behavior_ratio": 0,
                    "avg_good_health_ratio": 0,
                    "avg_total_readings": 0,
                    "driver_estimate": "N/A",
                    "health_estimate": "N/A",
                    "span_label": "No Data"
                })
                
            max_ts = pd.to_datetime(max_ts_str)
            
            if group_by == 'hour':
                start_ts = max_ts - timedelta(hours=1)
                span_label = "Latest Hour"
            elif group_by == 'day':
                start_ts = max_ts - timedelta(days=1)
                span_label = "Latest Day"
            elif group_by == 'week':
                start_ts = max_ts - timedelta(weeks=1)
                span_label = "Latest Week"
            elif group_by == 'month':
                start_ts = max_ts - timedelta(days=30)
                span_label = "Latest Month"
            
            start_ts_str = start_ts.strftime('%Y-%m-%d %H:%M:%S')
            
            # Query data only within this latest span
            health_df = pd.read_sql(f"SELECT Car_Health, COUNT(*) as count FROM obd_metrics WHERE timestamp >= '{start_ts_str}' GROUP BY Car_Health", conn)
            behavior_df = pd.read_sql(f"SELECT Driver_Behavior, COUNT(*) as count FROM obd_metrics WHERE timestamp >= '{start_ts_str}' GROUP BY Driver_Behavior", conn)
        
        
        h_dict = health_df.set_index('Car_Health')['count'].to_dict() if not health_df.empty else {}
        b_dict = behavior_df.set_index('Driver_Behavior')['count'].to_dict() if not behavior_df.empty else {}
        
        total_logs = sum(h_dict.values())
        
        if total_logs == 0:
             return jsonify({
                "avg_good_behavior_ratio": 0,
                "avg_neutral_behavior_ratio": 0,
                "avg_good_health_ratio": 0,
                "avg_total_readings": 0,
                "driver_estimate": "No Activity",
                "health_estimate": "No Activity",
                "span_label": span_label
            })
             
        # Global Ratios limits
        total_health_good = h_dict.get('Good', 0)
        avg_health_ratio = (total_health_good / total_logs * 100)
        
        total_behavior_good = b_dict.get('Good', 0)
        avg_behavior_ratio = (total_behavior_good / total_logs * 100)
        
        total_behavior_neutral = b_dict.get('Neutral', 0)
        avg_neutral_ratio = (total_behavior_neutral / total_logs * 100)
        
        # Estimate Logic
        b_bad = b_dict.get('Bad', 0)
        if total_behavior_good >= b_bad and total_behavior_good >= total_behavior_neutral:
            driver_est = "Driving Safely"
        elif b_bad > total_behavior_good and b_bad > total_behavior_neutral:
            driver_est = "Driving Badly"
        else:
            driver_est = "Driving Neutrally"
            
        h_bad = h_dict.get('Bad', 0)
        h_neutral = h_dict.get('Neutral', 0)
        if total_health_good >= h_bad and total_health_good >= h_neutral:
            health_est = "Car Health is Good"
        elif h_bad > total_health_good and h_bad > h_neutral:
            health_est = "Car Health is Bad"
        else:
            health_est = "Car Health is Neutral"
        
        return jsonify({
            "avg_good_behavior_ratio": avg_behavior_ratio,
            "avg_neutral_behavior_ratio": avg_neutral_ratio,
            "avg_good_health_ratio": avg_health_ratio,
            "avg_total_readings": total_logs, # total readings in this period
            "driver_estimate": driver_est,
            "health_estimate": health_est,
            "span_label": span_label
        })
    finally:
        conn.close()

@app.route("/api/car_health", methods=["GET"])
def get_car_health_over_time():
    group_by = request.args.get('group_by', 'day')
    specific_date = request.args.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    conn = get_db_connection()
    try:
        if specific_date:
            time_fmt = get_time_format('hour') # Force hourly breakdown for single day
            where_clause = f"WHERE strftime('%Y-%m-%d', timestamp) = '{specific_date}'"
        else:
            time_fmt = get_time_format(group_by)
            where_clause = ""
            
        query = f"""
            SELECT 
                strftime('{time_fmt}', timestamp) as time_period,
                Car_Health,
                COUNT(*) as count
            FROM obd_metrics
            {where_clause}
            GROUP BY time_period, Car_Health
            ORDER BY time_period ASC
        """
        df = pd.read_sql(query, conn)
        if df.empty:
            return jsonify([])
            
        pivot_df = df.pivot(index='time_period', columns='Car_Health', values='count').fillna(0).reset_index()
        for col in ['Good', 'Neutral', 'Bad']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
        return jsonify(pivot_df.to_dict(orient='records'))
    finally:
        conn.close()

@app.route("/api/driver_behavior", methods=["GET"])
def get_driver_behavior_over_time():
    group_by = request.args.get('group_by', 'day')
    specific_date = request.args.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    conn = get_db_connection()
    try:
        if specific_date:
            time_fmt = get_time_format('hour') # Force hourly breakdown for single day
            where_clause = f"WHERE strftime('%Y-%m-%d', timestamp) = '{specific_date}'"
        else:
            time_fmt = get_time_format(group_by)
            where_clause = ""
            
        query = f"""
            SELECT 
                strftime('{time_fmt}', timestamp) as time_period,
                Driver_Behavior,
                COUNT(*) as count
            FROM obd_metrics
            {where_clause}
            GROUP BY time_period, Driver_Behavior
            ORDER BY time_period ASC
        """
        df = pd.read_sql(query, conn)
        if df.empty:
            return jsonify([])
            
        pivot_df = df.pivot(index='time_period', columns='Driver_Behavior', values='count').fillna(0).reset_index()
        for col in ['Good', 'Neutral', 'Bad']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
        return jsonify(pivot_df.to_dict(orient='records'))
    finally:
        conn.close()

@app.route("/api/clear", methods=["DELETE"])
def clear_data():
    """Drop and recreate obd_metrics so users start fresh with the correct schema."""
    conn = get_db_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS obd_metrics")
        conn.execute("""
            CREATE TABLE obd_metrics (
                timestamp       TIMESTAMP,
                Driver_Behavior TEXT,
                Car_Health      TEXT,
                ENGINE_RPM                  REAL,
                VEHICLE_SPEED               REAL,
                THROTTLE                    REAL,
                ENGINE_LOAD                 REAL,
                COOLANT_TEMPERATURE         REAL,
                LONG_TERM_FUEL_TRIM_BANK_1  REAL,
                SHORT_TERM_FUEL_TRIM_BANK_1 REAL,
                INTAKE_MANIFOLD_PRESSURE    REAL
            )
        """)
        conn.commit()
        return jsonify({'message': 'All data cleared and table schema reset successfully.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route("/api/dates", methods=["GET"])
def get_available_dates():
    """Return a sorted list of distinct dates that have data, for the date-picker highlights."""
    conn = get_db_connection()
    try:
        df = pd.read_sql(
            "SELECT DISTINCT strftime('%Y-%m-%d', timestamp) as date FROM obd_metrics ORDER BY date ASC",
            conn
        )
        return jsonify(df['date'].tolist())
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
