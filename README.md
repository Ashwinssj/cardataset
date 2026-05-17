# Fleet Intelligence: OBD-II Telemetry Dashboard

A modern, high-performance web application for real-time car telemetry analysis and driver behavior monitoring. This project integrates machine learning models with a **Django REST Framework** backend, **PostgreSQL** database, and a premium **React** frontend to provide actionable insights from OBD-II data securely.

## 🚀 Features

- **Secure Authentication**: JWT-based token authentication to keep your telemetry data private and secure.
- **ML-Powered Classification**: Automatically classifies driving behavior (Good/Bad/Neutral) and car health using Random Forest models.
- **Smart Time Analysis**: 
  - Detects real timestamps from uploaded CSV files.
  - Automatically anchors data to the current day for session-based hourly analysis if timestamps are missing.
- **Advanced Anomaly Detection**: Uses rolling Z-scores across all telemetry features to identify and surface critical system spikes and drops.
- **Dynamic Dashboard**:
  - Interactive Area Charts using Recharts.
  - Snapshot analytics for behavior and health ratios.
  - Date-wise filtering for historical session analysis.
- **Premium UI**: Dark-mode glassmorphism design with responsive layouts and Lucide-React icons.

---

## 🛠️ Implementation Details

### Backend (Django & Python)
- **API Engine**: Built with **Django** and **Django REST Framework (DRF)** for robust, scalable API endpoints.
- **Authentication**: Secured using `djangorestframework-simplejwt` for industry-standard JWT authentication.
- **Data Processing**: Uses Pandas for high-speed data normalization and complex analytics (like rolling windows for anomalies).
- **Machine Learning**: Integrates pre-trained `scikit-learn` Random Forest models to predict telemetry states in real-time during upload.
- **Database**: **PostgreSQL** storage managed by Django ORM, utilizing efficient `bulk_create` operations for massive telemetry datasets.

### Frontend (React & Vite)
- **Framework**: React 18+ powered by Vite for instant HMR.
- **Routing & Auth**: Protected routes via `react-router-dom` and a centralized React Context for JWT lifecycle management.
- **State Management**: Real-time hooks for dynamic chart updates and file upload progress.
- **Aesthetics**: Premium CSS architecture using modern typography (Inter) and custom glassmorphism effects.

---

## 🏃 How to Run the Project

### Prerequisites
- Python 3.12+
- Node.js (v18+)
- npm
- PostgreSQL Installed & Running

### 1. Setup Backend

Navigate to the backend and install dependencies:
```bash
cd backend
python -m venv venv312
# Activate virtual environment:
# Windows: .\venv312\Scripts\activate
# Mac/Linux: source venv312/bin/activate

pip install -r requirements.txt
```

#### Configure PostgreSQL & Environment Variables
1. Open the `backend/.env` file.
2. Update `DB_PASSWORD` (and `DB_USER` if necessary) to match your PostgreSQL credentials.

#### Initialize Database & Migrations
We have provided an automated script to create the database and run migrations:
```bash
python setup_db.py
```

#### Start the Django Server
```bash
python manage.py runserver 8080
```
*Backend will run on `http://localhost:8080`*

### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
*Frontend will run on `http://localhost:5173`*

---

## 📂 Project Structure
- `backend/`: Django project (`obd_project`) and app (`api`), DB logic, and ML model integration.
- `frontend/`: React source code, components, routing, and styling.
- `rf_behavior_model.pkl`: Model for predicting driving behavior.
- `rf_health_model.pkl`: Model for predicting car health.

---

## 📝 Usage Note
When uploading a CSV, ensure the file contains the required OBD-II headers (e.g., `ENGINE_RPM`, `VEHICLE_SPEED`, etc.). If the file includes a `timestamp` column, the dashboard will use it for precision analysis. Otherwise, it will distribute data across today's hours based on `ENGINE_RUN_TINE`. You must create an account and log in before accessing the dashboard or uploading data.
