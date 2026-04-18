const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');

dotenv.config();

const app = express();
const port = process.env.PORT || 8001;

app.use(cors());
app.use(express.json());

const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    user: process.env.DB_USER || 'auth_user',
    password: process.env.DB_PASSWORD || 'auth123',
    database: process.env.DB_NAME || 'auth_db',
});

pool.connect((err, client, release) => {
    if (err) {
        console.error('❌ Database connection failed:', err.message);
    } else {
        console.log('✅ Connected to PostgreSQL');
        release();
    }
});

const verifyToken = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
        return res.status(401).json({ detail: "No token provided" });
    }

    const token = authHeader.split(' ')[1];
    
    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        
        const result = await pool.query(
            'SELECT id, email, role FROM users WHERE id = $1 AND is_active = true',
            [decoded.user_id]
        );
        
        if (result.rows.length === 0) {
            return res.status(401).json({ detail: "User not found" });
        }
        
        req.user = result.rows[0];
        next();
    } catch (error) {
        return res.status(401).json({ detail: "Invalid token" });
    }
};

app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'grievance-service' });
});

app.post('/api/grievances', verifyToken, async (req, res) => {
    const { platform, category, title, description } = req.body;
    
    if (!platform || !category || !title || !description) {
        return res.status(400).json({ detail: "Missing required fields" });
    }
    
    if (req.user.role !== 'WORKER' && req.user.role !== 'ADMIN') {
        return res.status(403).json({ detail: "Only workers can create grievances" });
    }
    
    try {
        const result = await pool.query(
            `INSERT INTO grievances (worker_id, platform, category, title, description, status)
             VALUES ($1, $2, $3, $4, $5, 'open')
             RETURNING *`,
            [req.user.id, platform, category, title, description]
        );
        res.status(201).json(result.rows[0]);
    } catch (error) {
        res.status(500).json({ detail: "Failed to create grievance" });
    }
});

app.get('/api/grievances/my', verifyToken, async (req, res) => {
    try {
        const result = await pool.query(
            `SELECT * FROM grievances WHERE worker_id = $1 ORDER BY created_at DESC`,
            [req.user.id]
        );
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ detail: "Failed to fetch grievances" });
    }
});

app.get('/api/grievances', verifyToken, async (req, res) => {
    if (req.user.role !== 'ADVOCATE' && req.user.role !== 'ADMIN') {
        return res.status(403).json({ detail: "Advocate privileges required" });
    }
    
    try {
        const result = await pool.query(
            `SELECT g.*, u.name as worker_name 
             FROM grievances g
             JOIN users u ON g.worker_id = u.id
             ORDER BY g.created_at DESC`
        );
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ detail: "Failed to fetch grievances" });
    }
});

app.post('/api/grievances/:id/tags', verifyToken, async (req, res) => {
    const { id } = req.params;
    const { tag } = req.body;
    
    if (!tag) return res.status(400).json({ detail: "Tag required" });
    if (req.user.role !== 'ADVOCATE' && req.user.role !== 'ADMIN') {
        return res.status(403).json({ detail: "Advocate privileges required" });
    }
    
    try {
        await pool.query('INSERT INTO grievance_tags (grievance_id, tag) VALUES ($1, $2)', [id, tag]);
        res.json({ message: "Tag added" });
    } catch (error) {
        res.status(500).json({ detail: "Failed to add tag" });
    }
});

app.post('/api/grievances/:id/escalate', verifyToken, async (req, res) => {
    const { id } = req.params;
    
    if (req.user.role !== 'ADVOCATE' && req.user.role !== 'ADMIN') {
        return res.status(403).json({ detail: "Advocate privileges required" });
    }
    
    try {
        await pool.query(`UPDATE grievances SET status = 'escalated' WHERE id = $1`, [id]);
        await pool.query(
            `INSERT INTO grievance_escalations (grievance_id, escalated_by) VALUES ($1, $2)`,
            [id, req.user.id]
        );
        res.json({ message: "Grievance escalated" });
    } catch (error) {
        res.status(500).json({ detail: "Failed to escalate" });
    }
});

app.post('/api/grievances/cluster', verifyToken, async (req, res) => {
    if (req.user.role !== 'ADVOCATE' && req.user.role !== 'ADMIN') {
        return res.status(403).json({ detail: "Advocate privileges required" });
    }
    
    try {
        const result = await pool.query(
            `SELECT platform, category, COUNT(*) as count,
                    STRING_AGG(id::text, ',') as grievance_ids
             FROM grievances
             WHERE status != 'resolved'
             GROUP BY platform, category
             HAVING COUNT(*) > 1`
        );
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ detail: "Failed to cluster" });
    }
});

app.listen(port, () => {
    console.log(`🚀 Grievance service on port ${port}`);
});
