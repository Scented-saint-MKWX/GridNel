# 🛡️ SentinelGrid — Smart City Traffic Analytics & Road Trajectory Engine

> **A High-Performance Fog-to-Cloud Surveillance & ANPR Intelligence Platform for Smart Cities.**

SentinelGrid unifies distributed edge camera nodes with a central cloud analytics engine. It detects vehicles, extracts license plates using computer vision, validates them against strict registration standards, and reconstructs vehicle journeys **along physical city road networks** on an interactive GIS map — all while maintaining low latency and privacy standards.

---

## 🏛️ Architecture Overview

```text
[ANPR Camera Feeds]
       │ (Raw Frame Drop / Stream)
       ▼
┌─────────────────────────────────────────────────────────┐
│ 🚀 EDGE AI NODE (fog-node/)                             │
│ 1. Vehicle & Plate Localization via YOLOv8 (CPU mode)   │
│ 2. CLAHE & Bilateral Image Pre-processing Enhancement   │
│ 3. Text Extraction (PaddleOCR / EasyOCR PyTorch Engine) │
│ 4. Strict Regex Filter: ^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$│
│ 5. Hardware Fusion & Fallback SQLite Buffer             │
│ 6. Watchdog Folder Monitoring (fog-node/images/)        │
└──────────────────────────┬──────────────────────────────┘
                           │ POST /ingest (JSON Telemetry)
                           ▼
┌─────────────────────────────────────────────────────────┐
│ ☁️ CENTRAL CLOUD API (api/ & db/)                       │
│ 1. FastAPI Gateway (0.0.0.0:8000, CORS enabled)         │
│ 2. Ingestion Deduplication (5-sec Redis SETNX)          │
│ 3. Redis High-Throughput Stream: sightings:stream       │
│ 4. Background Flusher Engine (drains Redis -> Postgres) │
│ 5. Real-Time Blacklist Sighting Alerts (alert_events)   │
│ 6. PostgreSQL 15 Relational Persistence                 │
└──────────────────────────┬──────────────────────────────┘
                           │ REST Endpoints & OSRM Routing
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 🗺️ GIS FRONTEND DASHBOARD (frontend/index.html)         │
│ 1. Live Interactive Leaflet Map (OpenStreetMap Tiles)   │
│ 2. Turn-by-Turn Road Routing via OSRM                   │
│ 3. Real-Time Analytics Counters (Sightings, Nodes, Hits)│
│ 4. Live Blacklist Alert Ticker with Quick Tracking      │
│ 5. Chronological Sighting Timeline with Transit Metrics │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.10+ (Virtual environment in `./venv`)

### 2. Start Database & Cache Containers
```bash
docker compose up -d
```
*Spins up PostgreSQL 15 on port `5432` and Redis 7 on port `6379` with pre-seeded camera network (`db/seed.sql`).*

### 3. Start Cloud API & Flusher
```bash
# Terminal 1: Start FastAPI Server
./venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Redis Stream Flusher
./venv/bin/python -m api.flusher
```

### 4. Start Edge Watchdog Node
```bash
# Terminal 3: Edge camera folder monitoring
./venv/bin/python fog-node/edge_watcher.py
```
*Drop any `.jpg` image into `fog-node/images/` to automatically trigger detection and cloud ingestion.*

### 5. Open the Live Dashboard
Navigate to **`http://localhost:8000/`** in your browser.

---

## 📊 Dataset Ingestion & Output Generation

### 1. Kaggle Dataset Processor
Process any Kaggle dataset (or local unzipped image folder):
```bash
./venv/bin/python scripts/ingest_kaggle_dataset.py <dataset_slug_or_folder> --limit 20
```
- Local folder example:
  ```bash
  ./venv/bin/python scripts/ingest_kaggle_dataset.py data/sample_images --limit 5
  ```
- **Output Generated**: [`output/kaggle_dataset_output.json`](output/kaggle_dataset_output.json) detailing detected plates, confidence scores, garbage discards, and processing latency.

### 2. Multi-Camera Trajectory Replay
Replay historical multi-hop vehicle journeys across the city cameras:
```bash
./venv/bin/python scripts/replay.py --dataset data/trajectories.json
```
- **Output Generated**: [`output/replay_summary.json`](output/replay_summary.json) detailing reconstructed routes, transit durations, and blacklist hits.

---

## 🛣️ Features & Capabilities

- **Turn-by-Turn Road Routing**: Queries OSRM to snap trajectories to physical streets, avenues, and curves instead of straight lines.
- **Strict Indian Plate Regex Validation**: Enforces `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$` to eliminate OCR noise, street signs, and billboard text.
- **Zero API Key Dependency**: Runs completely self-contained with OpenStreetMap tiles and local Docker services.
- **Privacy-First Offline Buffer**: Edge nodes retain SQLite cache (`fog-node/data/buffer.db`) if network connectivity is interrupted.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Ingests edge ANPR JSON payload to Redis |
| `GET` | `/track/{plate}` | Reconstructed chronological sightings |
| `GET` | `/analytics/summary` | Live global sightings, cameras, and alert counts |
| `GET` | `/cameras` | Active ANPR camera coordinates and zones |
| `GET` | `/alerts` | Recent blacklist detection events |
| `GET` | `/` | Serves the interactive GIS Leaflet dashboard |
