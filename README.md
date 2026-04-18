# 🚀 KamaiKitab - Gig Worker Income Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)

> **Empowering gig workers to track, verify, and understand their earnings**

## ✨ Features

| Feature | Status |
|---------|--------|
| 🔐 JWT Authentication | ✅ Working |
| 📧 Email Verification | ✅ Working |
| 💰 Earnings CRUD | ✅ Working |
| 📊 CSV Bulk Import | ✅ Working |
| 🔍 Anomaly Detection | ✅ Working |
| 💬 AI Chatbot | ✅ Working |
| 📋 Grievance System | ✅ Working |
| ✅ Verification Flow | ✅ Working |
| 👥 Role Management | ✅ Working |

## 🚀 Quick Start

`ash
# Clone & setup
git clone https://github.com/YOUR_USERNAME/KamaiKitab-backend.git
cd KamaiKitab-backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
📡 API Documentation
Once running, visit: http://localhost:8000/docs

🧪 Test Credentials
json
{
  "email": "worker@test.com",
  "password": "Test1234!"
}
📊 System Status
text
✅ Authentication Service  - Operational
✅ Earnings Service       - Operational  
✅ Anomaly Detection      - Operational
✅ Chatbot Service        - Operational
✅ Grievance Service      - Operational
✅ Database (PostgreSQL)  - Connected
🛠️ Tech Stack
FastAPI - High-performance backend

PostgreSQL - Reliable database

JWT - Secure authentication

bcrypt - Password hashing

SQLAlchemy - ORM

📁 Project Structure
text
KamaiKitab-backend/
├── app/
│   ├── routers/     # API endpoints
│   ├── models.py    # Database models
│   ├── auth.py      # Authentication logic
│   └── security.py  # Security utilities
├── grievance-service/  # Node.js service
├── requirements.txt
└── .env.example
👥 Roles
Role    Permissions
👷 Worker    Add earnings, view analytics, submit grievances
✅ Verifier    Verify earnings submissions
📊 Advocate    Analytics, manage grievances
👑 Admin    Full system access
🎯 Anomaly Detection Example
bash
curl -X POST http://localhost:8000/api/anomaly/detect \
  -H "Content-Type: application/json" \
  -d '{
    "earnings_history": [
      {"date":"2024-04-01","net_received":5000},
      {"date":"2024-04-08","net_received":3000},
      {"date":"2024-04-15","net_received":2000}
    ]
  }'
Response: Detects 40% income drop with explanation

📞 Support
API Docs: http://localhost:8000/docs

Health Check: http://localhost:8000/health

Built with ❤️ for gig workers | SOFTEC 2026
