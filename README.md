# Fleet Intelligence: OBD-II Telemetry Dashboard

A modern, high-performance web application for real-time car telemetry analysis and driver behavior monitoring. This project integrates machine learning models with a Flask backend and a premium React frontend to provide actionable insights from OBD-II data.

## 🚀 Features

- **ML-Powered Classification**: Automatically classifies driving behavior (Good/Bad/Neutral) and car health using Random Forest models.
- **Smart Time Analysis**: 
  - Detects real timestamps from uploaded CSV files.
  - Automatically anchors data to the current day for session-based hourly analysis if timestamps are missing.
- **Dynamic Dashboard**:
  - Interactive Area Charts using Recharts.
  - Snapshot analytics for behavior and health ratios.
  - Date-wise filtering for historical session analysis.
- **Premium UI**: Dark-mode glassmorphism design with responsive layouts and Lucide-React icons.

---

## 🛠️ Implementation Details

### Backend (Flask & Python)
- **API Engine**: Built with Flask and Flask-CORS for seamless frontend integration.
- **Data Processing**: Uses Pandas for high-speed data normalization and timestamp resolution.
- **Machine Learning**: Integrates pre-trained `scikit-learn` Random Forest models to predict telemetry states in real-time during upload.
- **Database**: SQLite3 storage with an automated schema-initialization engine that ensures the database layout is always up-to-date.

### Frontend (React & Vite)
- **Framework**: React 18+ powered by Vite for instant HMR.
- **State Management**: Real-time hooks for dynamic chart updates and file upload progress.
- **Aesthetics**: Premium CSS architecture using modern typography (Inter) and custom glassmorphism effects.

---

## 🏃 How to Run the Project

### Prerequisites
- Python 3.12+
- Node.js (v18+)
- npm

### 1. Setup Backend
```bash
cd backend
python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
# Alternatively: pip install flask flask-cors pandas scikit-learn joblib

python main.py
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
- `backend/`: Flask server, DB logic, and ML model integration.
- `frontend/`: React source code, components, and styling.
- `rf_behavior_model.pkl`: Model for predicting driving behavior.
- `rf_health_model.pkl`: Model for predicting car health.

---

## 📝 Usage Note
When uploading a CSV, ensure the file contains the required OBD-II headers (e.g., `ENGINE_RPM`, `VEHICLE_SPEED`, etc.). If the file includes a `timestamp` column, the dashboard will use it for precision analysis. Otherwise, it will distribute data across today's hours based on `ENGINE_RUN_TINE`.
