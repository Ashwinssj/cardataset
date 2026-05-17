import os
import traceback
from datetime import datetime, timedelta, date

import pandas as pd
from django.db import connection
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import ObdMetric

ML_MODELS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

behavior_model = None
health_model = None
MODELS_LOAD_ERROR = None

try:
    import joblib
    behavior_model = joblib.load(os.path.join(ML_MODELS_PATH, 'rf_behavior_model.pkl'))
    health_model = joblib.load(os.path.join(ML_MODELS_PATH, 'rf_health_model.pkl'))
    print("ML Models loaded successfully.")
except Exception as e:
    MODELS_LOAD_ERROR = str(e)
    print(f"ML Models failed to load: {e}")

FEATURES = [
    'ENGINE_RPM', 'VEHICLE_SPEED', 'THROTTLE', 'ENGINE_LOAD',
    'COOLANT_TEMPERATURE', 'LONG_TERM_FUEL_TRIM_BANK_1',
    'SHORT_TERM_FUEL_TRIM_BANK_1', 'INTAKE_MANIFOLD_PRESSURE'
]

def get_time_format(group_by: str):
    if group_by == 'hour':
        return 'YYYY-MM-DD HH:00:00'
    elif group_by == 'day':
        return 'YYYY-MM-DD'
    elif group_by == 'week':
        return 'IYYY-IW' # PostgreSQL week format
    elif group_by == 'month':
        return 'YYYY-MM'
    return 'YYYY-MM-DD'

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, password=password)
    return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    if behavior_model is None or health_model is None:
        return Response({
            'error': f'ML models not loaded. Details: {MODELS_LOAD_ERROR}'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if 'file' not in request.FILES:
        return Response({'error': 'No file part in request'}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['file']
    if not file.name.endswith('.csv'):
        return Response({'error': 'Only CSV files are accepted'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        df = pd.read_csv(file)
        has_real_timestamp = any(c.strip().lower() == 'timestamp' for c in df.columns)

        df.columns = [
            col.strip().replace(' ()', '').replace('()', '').replace(' ', '_').upper()
            for col in df.columns
        ]

        missing_features = [f for f in FEATURES if f not in df.columns]
        if missing_features:
            return Response({
                'error': f"CSV is missing required columns: {missing_features}",
            }, status=status.HTTP_400_BAD_REQUEST)

        df = df.dropna(subset=FEATURES).copy()
        if len(df) == 0:
            return Response({'error': 'No valid rows remain'}, status=status.HTTP_400_BAD_REQUEST)

        X = df[FEATURES].astype(float)
        df['driver_behavior'] = behavior_model.predict(X)
        df['car_health'] = health_model.predict(X)

        if has_real_timestamp and 'TIMESTAMP' in df.columns:
            df['timestamp'] = pd.to_datetime(df['TIMESTAMP'], errors='coerce')
        elif 'ENGINE_RUN_TINE' in df.columns:
            session_anchor = datetime.combine(date.today(), datetime.min.time())
            df['timestamp'] = df['ENGINE_RUN_TINE'].apply(
                lambda s: session_anchor + timedelta(seconds=float(s) if pd.notna(s) else 0)
            )
        else:
            session_anchor = datetime.combine(date.today(), datetime.min.time())
            df['timestamp'] = [session_anchor + timedelta(seconds=i) for i in range(len(df))]

        df['user_id'] = request.user.id
        
        # Lowercase column names for model/DB compatibility
        df.rename(columns={col: col.lower() for col in FEATURES}, inplace=True)
        cols_to_keep = ['user_id', 'timestamp', 'driver_behavior', 'car_health'] + [f.lower() for f in FEATURES]
        df_slim = df[cols_to_keep]

        # Use bulk_create for performance instead of to_sql to bypass pandas schema issues
        metrics = []
        for row in df_slim.to_dict('records'):
            # Convert NaNs to None for Postgres
            for key, val in row.items():
                if pd.isna(val):
                    row[key] = None
            metrics.append(ObdMetric(**row))
        ObdMetric.objects.bulk_create(metrics, batch_size=5000)

        return Response({
            'message': f'Successfully classified and stored {len(df_slim):,} readings.',
            'rows': len(df_slim)
        })

    except Exception as e:
        err_trace = traceback.format_exc()
        return Response({'error': str(e), 'trace': err_trace}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_summary(request):
    try:
        query = f"SELECT car_health as \"Car_Health\", COUNT(*) as count FROM obd_metrics WHERE user_id={request.user.id} GROUP BY car_health"
        health_df = pd.read_sql(query, connection)
        query = f"SELECT driver_behavior as \"Driver_Behavior\", COUNT(*) as count FROM obd_metrics WHERE user_id={request.user.id} GROUP BY driver_behavior"
        behavior_df = pd.read_sql(query, connection)
        
        return Response({
            "health": health_df.set_index('Car_Health')['count'].to_dict() if not health_df.empty else {},
            "behavior": behavior_df.set_index('Driver_Behavior')['count'].to_dict() if not behavior_df.empty else {}
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_averages(request):
    group_by = request.query_params.get('group_by', 'day')
    specific_date = request.query_params.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    try:
        user_id = request.user.id
        if specific_date:
            span_label = f"For {specific_date}"
            health_query = f"SELECT car_health, COUNT(*) as count FROM obd_metrics WHERE TO_CHAR(timestamp, 'YYYY-MM-DD') = '{specific_date}' AND user_id={user_id} GROUP BY car_health"
            behavior_query = f"SELECT driver_behavior, COUNT(*) as count FROM obd_metrics WHERE TO_CHAR(timestamp, 'YYYY-MM-DD') = '{specific_date}' AND user_id={user_id} GROUP BY driver_behavior"
            health_df = pd.read_sql(health_query, connection)
            behavior_df = pd.read_sql(behavior_query, connection)
        else:
            max_ts_df = pd.read_sql(f"SELECT MAX(timestamp) as max_ts FROM obd_metrics WHERE user_id={user_id}", connection)
            max_ts_str = max_ts_df['max_ts'].iloc[0]
            
            if pd.isna(max_ts_str) or not max_ts_str:
                return Response({
                    "avg_good_behavior_ratio": 0, "avg_neutral_behavior_ratio": 0, "avg_good_health_ratio": 0,
                    "avg_total_readings": 0, "driver_estimate": "N/A", "health_estimate": "N/A", "span_label": "No Data"
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
            
            health_query = f"SELECT car_health, COUNT(*) as count FROM obd_metrics WHERE timestamp >= '{start_ts_str}' AND user_id={user_id} GROUP BY car_health"
            behavior_query = f"SELECT driver_behavior, COUNT(*) as count FROM obd_metrics WHERE timestamp >= '{start_ts_str}' AND user_id={user_id} GROUP BY driver_behavior"
            health_df = pd.read_sql(health_query, connection)
            behavior_df = pd.read_sql(behavior_query, connection)
        
        h_dict = health_df.set_index('car_health')['count'].to_dict() if not health_df.empty else {}
        b_dict = behavior_df.set_index('driver_behavior')['count'].to_dict() if not behavior_df.empty else {}
        
        total_logs = sum(h_dict.values())
        if total_logs == 0:
             return Response({
                "avg_good_behavior_ratio": 0, "avg_neutral_behavior_ratio": 0, "avg_good_health_ratio": 0,
                "avg_total_readings": 0, "driver_estimate": "No Activity", "health_estimate": "No Activity", "span_label": span_label
            })
             
        total_health_good = h_dict.get('Good', 0)
        avg_health_ratio = (total_health_good / total_logs * 100)
        
        total_behavior_good = b_dict.get('Good', 0)
        avg_behavior_ratio = (total_behavior_good / total_logs * 100)
        
        total_behavior_neutral = b_dict.get('Neutral', 0)
        avg_neutral_ratio = (total_behavior_neutral / total_logs * 100)
        
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
        
        return Response({
            "avg_good_behavior_ratio": avg_behavior_ratio,
            "avg_neutral_behavior_ratio": avg_neutral_ratio,
            "avg_good_health_ratio": avg_health_ratio,
            "avg_total_readings": total_logs,
            "driver_estimate": driver_est,
            "health_estimate": health_est,
            "span_label": span_label
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_car_health_over_time(request):
    group_by = request.query_params.get('group_by', 'day')
    specific_date = request.query_params.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    try:
        user_id = request.user.id
        if specific_date:
            time_fmt = get_time_format('hour')
            where_clause = f"WHERE TO_CHAR(timestamp, 'YYYY-MM-DD') = '{specific_date}' AND user_id={user_id}"
        else:
            time_fmt = get_time_format(group_by)
            where_clause = f"WHERE user_id={user_id}"
            
        query = f"""
            SELECT 
                TO_CHAR(timestamp, '{time_fmt}') as time_period,
                car_health as "Car_Health",
                COUNT(*) as count
            FROM obd_metrics
            {where_clause}
            GROUP BY time_period, car_health
            ORDER BY time_period ASC
        """
        df = pd.read_sql(query, connection)
        if df.empty:
            return Response([])
            
        pivot_df = df.pivot(index='time_period', columns='Car_Health', values='count').fillna(0).reset_index()
        for col in ['Good', 'Neutral', 'Bad']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
        return Response(pivot_df.to_dict(orient='records'))
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_behavior_over_time(request):
    group_by = request.query_params.get('group_by', 'day')
    specific_date = request.query_params.get('date', '')
    
    if group_by not in ['hour', 'day', 'week', 'month']:
        group_by = 'day'
        
    try:
        user_id = request.user.id
        if specific_date:
            time_fmt = get_time_format('hour')
            where_clause = f"WHERE TO_CHAR(timestamp, 'YYYY-MM-DD') = '{specific_date}' AND user_id={user_id}"
        else:
            time_fmt = get_time_format(group_by)
            where_clause = f"WHERE user_id={user_id}"
            
        query = f"""
            SELECT 
                TO_CHAR(timestamp, '{time_fmt}') as time_period,
                driver_behavior as "Driver_Behavior",
                COUNT(*) as count
            FROM obd_metrics
            {where_clause}
            GROUP BY time_period, driver_behavior
            ORDER BY time_period ASC
        """
        df = pd.read_sql(query, connection)
        if df.empty:
            return Response([])
            
        pivot_df = df.pivot(index='time_period', columns='Driver_Behavior', values='count').fillna(0).reset_index()
        for col in ['Good', 'Neutral', 'Bad']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
        return Response(pivot_df.to_dict(orient='records'))
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_anomalies(request):
    group_by = request.query_params.get('group_by', 'day')
    specific_date = request.query_params.get('date', '')
    
    try:
        user_id = request.user.id
        where_clause = f"WHERE user_id={user_id}"
        if specific_date:
            where_clause += f" AND TO_CHAR(timestamp, 'YYYY-MM-DD') = '{specific_date}'"
        else:
            max_ts_df = pd.read_sql(f"SELECT MAX(timestamp) as max_ts FROM obd_metrics WHERE user_id={user_id}", connection)
            max_ts_str = max_ts_df['max_ts'].iloc[0]
            if pd.notna(max_ts_str) and max_ts_str:
                max_ts = pd.to_datetime(max_ts_str)
                if group_by == 'hour':
                    start_ts = max_ts - timedelta(hours=1)
                elif group_by == 'day':
                    start_ts = max_ts - timedelta(days=1)
                elif group_by == 'week':
                    start_ts = max_ts - timedelta(weeks=1)
                elif group_by == 'month':
                    start_ts = max_ts - timedelta(days=30)
                else:
                    start_ts = max_ts - timedelta(days=1)
                start_ts_str = start_ts.strftime('%Y-%m-%d %H:%M:%S')
                where_clause += f" AND timestamp >= '{start_ts_str}'"
        
        feature_cols = [f.lower() for f in FEATURES]
        query = f"SELECT timestamp, {', '.join(feature_cols)} FROM obd_metrics {where_clause} ORDER BY timestamp ASC"
        df = pd.read_sql(query, connection)
        
        if df.empty:
            return Response([])
        
        window_size = 10
        anomalies = []
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
        
        for feature in feature_cols:
            if feature not in df.columns:
                continue
            
            rolling_mean = df[feature].shift(1).rolling(window=window_size, min_periods=1).mean().bfill()
            rolling_std = df[feature].shift(1).rolling(window=window_size, min_periods=1).std().fillna(0).bfill()
            
            z_scores = (df[feature] - rolling_mean) / (rolling_std + 1e-5)
            spike_indices = df.index[z_scores.abs() > 2.5].tolist()
            
            for idx in spike_indices:
                val = float(df.at[idx, feature])
                avg_val = float(rolling_mean[idx])
                if abs(val - avg_val) < 1.0 and feature.upper() not in ['THROTTLE', 'ENGINE_LOAD']:
                    continue
                    
                anomalies.append({
                    'timestamp': df.at[idx, 'timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'system': feature.replace('_', ' ').title(),
                    'value': round(val, 2),
                    'average': round(avg_val, 2),
                    'severity': round(float(z_scores.abs()[idx]), 2),
                    'type': 'Spike' if z_scores[idx] > 0 else 'Drop'
                })
        
        anomalies = sorted(anomalies, key=lambda x: x['severity'], reverse=True)
        return Response(anomalies[:50])
    except Exception as e:
        import traceback
        print(f"ANOMALY ERROR:\n{traceback.format_exc()}")
        return Response({'error': str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_data(request):
    try:
        ObdMetric.objects.filter(user=request.user).delete()
        return Response({'message': 'User data cleared successfully.'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_dates(request):
    try:
        df = pd.read_sql(
            f"SELECT DISTINCT TO_CHAR(timestamp, 'YYYY-MM-DD') as date FROM obd_metrics WHERE user_id={request.user.id} ORDER BY date ASC",
            connection
        )
        return Response(df['date'].tolist())
    except Exception as e:
        return Response({'error': str(e)}, status=500)
