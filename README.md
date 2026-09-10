# GridNel

GridNel is an urban multi-target multi-camera tracking (MTMCT) foundation that combines:

- FastAPI for asynchronous event ingestion
- Graph-based routing logic for blind-spot trajectory reconstruction
- YOLOv8 + OCR for edge camera processing
- PostGIS-backed spatial persistence
- Privacy-first SHA-256 hashing for PII such as plate strings

## 1) System Dependencies

Install these services/tools before running the stack:

- PostgreSQL
- PostGIS extension for PostgreSQL
- Redis
- Node.js + npm
- Python 3.10+

## 2) Backend Setup (Python)

```bash
cd /home/runner/work/GridNel/GridNel
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

The backend requirements include:

- API/data handling: `fastapi`, `uvicorn[standard]`, `python-dotenv`
- Graph/algorithms: `networkx`, `numpy`, `pandas`
- Vision/OCR: `ultralytics`, `easyocr`, `opencv-python-headless`
- Database/security/cache: `asyncpg`, `geoalchemy2`, `redis`, `PyJWT`, `passlib[bcrypt]`

## 3) Frontend Setup (Next.js)

Initialize frontend in a separate terminal:

```bash
cd /home/runner/work/GridNel/GridNel
npx create-next-app@latest frontend
cd frontend
npm install leaflet react-leaflet axios lucide-react tailwindcss
```

If you prefer Mapbox instead of Leaflet:

```bash
npm install mapbox-gl react-map-gl
```