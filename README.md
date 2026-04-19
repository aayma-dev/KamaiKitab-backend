# 🖥️ KamaiKitab Backend

**Backend API for Pakistan's gig workforce platform.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org/)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL

### Installation

```bash
# Clone repo
git clone https://github.com/aayma-codes/project-repo-backend.git
cd project-repo-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://user:password@localhost:5432/kamaikitab
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PORT=8000
EOF

# Run database migrations
alembic upgrade head

# Run server
uvicorn main:app --reload --port 8000
Server runs at http://localhost:8000
API Docs at http://localhost:8000/docs

📁 Project Structure
text
project-backend/
├── app/
│   ├── api/             # Route endpoints
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── crud/            # Database operations
│   ├── auth/            # JWT authentication
│   └── config.py        # Settings
├── migrations/          # Alembic migrations
├── requirements.txt
├── .env
└── main.py
🔌 Main API Endpoints
Method	Endpoint	Description
POST	/api/auth/register	Register user
POST	/api/auth/login	Login
GET	/api/earnings	Get earnings
POST	/api/earnings	Add earnings
POST	/api/verify/upload	Upload proof
GET	/api/certificates	Get certificates
POST	/api/reports/anonymous	Submit report
GET	/api/advocate/heatmap	Heatmap data
🔄 Pull Latest Changes
bash
git restore .
git pull origin main

# Recreate .env file with your values
# Reactivate virtual environment if needed
🚢 Deployment
Recommended platforms: Render, Railway, or Heroku

Push code to GitHub

Connect repo to platform

Add PostgreSQL database

Set environment variables

Deploy

📝 Environment Variables
Variable	Required	Description
DATABASE_URL	Yes	PostgreSQL connection string
SECRET_KEY	Yes	JWT secret key
ALGORITHM	No	HS256
ACCESS_TOKEN_EXPIRE_MINUTES	No	30
PORT	No	8000
📦 Dependencies (requirements.txt)
text
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.12.1
pydantic==2.5.0
python-dotenv==1.0.0
👥 Team
Backend Developer: @aayma-codes

<div align="center">
Made with ❤️ for Pakistan's Gig Workers

</div> ```
