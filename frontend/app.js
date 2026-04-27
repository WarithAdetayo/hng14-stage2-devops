'use strict';

const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();

// Bug fix: API_URL was hardcoded as "http://localhost:8000".
// Inside Docker, "localhost" refers to the container itself, not the API
// service.  Services communicate via their Compose network alias ("api").
// We read from the environment so the value can be overridden per deployment.
const API_URL = process.env.API_URL || 'http://api:8000';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'views')));

app.post('/submit', async (req, res) => {
    try {
        const response = await axios.post(`${API_URL}/jobs`);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ error: 'something went wrong' });
    }
});

app.get('/status/:id', async (req, res) => {
    try {
        const response = await axios.get(`${API_URL}/jobs/${req.params.id}`);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ error: 'something went wrong' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Frontend running on port ${PORT}`);
});
