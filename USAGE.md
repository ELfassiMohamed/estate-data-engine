# 🚀 Estate Data Engine Usage Guide

Welcome to the **Estate Data Engine** usage guide. This document provides step-by-step instructions on how to set up, configure, and run the asynchronous real estate data pipeline.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.10+**
- **Docker & Docker Compose** (for Redis stack)
- **PostgreSQL** (Active database instance)
- **Git**

---

## 📥 Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd estate-data-engine
   ```

2. **Set up Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright Browsers**
   ```bash
   playwright install
   ```

---

## ⚙️ Configuration

1. **Environment Variables**
   Copy the example environment file and update it with your credentials:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`**
   Open `.env` and configure your PostgreSQL and Redis settings:
   ```env
   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=realestate
   PGUSER=postgres
   PGPASSWORD=yourpassword

   MAX_LISTING_PAGES=3
   HEADLESS=true
   REDIS_URL=redis://localhost:6379/0
   ```

---

## 🗄️ Database Setup

Ensure your PostgreSQL database is running and execute the schema script to create the necessary tables:

```bash
psql -h localhost -U postgres -d realestate -f sql/schema.sql
```

---

## 🚀 Running the Engine

The engine supports two modes of execution: **Sequential** (standard) and **Distributed** (using Celery/Redis).

### 1. Sequential Mode (Default)
Best for small-scale scraping or testing.
```bash
python main.py --mode sequential
```

### 2. Distributed Mode
Designed for high-performance, parallel scraping across multiple workers.

> [!IMPORTANT]
> You must have Redis running before starting the distributed pipeline.

**A. Start Redis Stack**
```bash
docker-compose up -d
```

**B. Start Celery Worker**
Open a new terminal, activate the venv, and run:
```bash
# Windows
celery -A src.celery_app worker --loglevel=info -P solo

# Linux/Mac
celery -A src.celery_app worker --loglevel=info
```

**C. Launch the Pipeline**
```bash
python main.py --mode distributed
```

---

## 📊 Monitoring & Workflows

### Redis Stack Management
Access the Redis Insight GUI at `http://localhost:8001` (if using redis-stack-server) to monitor task queues and data.

### n8n Integration
The project includes an `n8n_workflow.json` which can be imported into your n8n instance to automate post-processing or notifications of the scraped data.

---

> [!TIP]
> Use `HEADLESS=false` in your `.env` during development to see Playwright in action!
