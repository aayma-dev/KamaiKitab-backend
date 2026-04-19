# 🖥️ KamaiKitab Backend

**Backend API for Pakistan's gig workforce platform.**

[![Node.js](https://img.shields.io/badge/Node.js-18.x-339933?style=for-the-badge&logo=nodedotjs)](https://nodejs.org/)
[![Express.js](https://img.shields.io/badge/Express.js-4.x-000000?style=for-the-badge&logo=express)](https://expressjs.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb)](https://mongodb.com/)

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- MongoDB

### Installation

```bash
# Clone repo
git clone https://github.com/aayma-codes/project-repo-backend.git
cd project-repo-backend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
PORT=5000
MONGODB_URI=mongodb://localhost:27017/kamaikitab
JWT_SECRET=your_secret_key_here
JWT_EXPIRE=7d
FRONTEND_URL=http://localhost:5173
EOF

# Run server
npm run dev
Server runs at http://localhost:5000

📁 Project Structure
text
project-backend/
├── src/
│   ├── controllers/     # Request handlers
│   ├── models/          # MongoDB schemas
│   ├── routes/          # API endpoints
│   ├── middleware/      # Auth, validation
│   └── services/        # Business logic
├── .env                 # Environment variables
└── server.js            # Entry point
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
del .env        # Windows
# rm .env       # Mac/Linux
git pull origin main
🚢 Deployment
Recommended platforms: Render (free) or Railway

Push code to GitHub

Connect repo to Render/Railway

Add environment variables

Deploy

📝 Environment Variables
Variable	Required	Default
PORT	No	5000
MONGODB_URI	Yes	-
JWT_SECRET	Yes	-
JWT_EXPIRE	No	7d
FRONTEND_URL	No	http://localhost:5173
👥 Team
Backend Developer: @aayma-codes

<div align="center">
Made with ❤️ for Pakistan's Gig Workers

</div> ```
