# 🏔️ NER-LEWS: North Eastern Region Landslide Early Warning System

<div align="center">

[![SIH 2026](https://img.shields.io/badge/SIH_2026-Problem_SIH26001-FF6F00?style=for-the-badge&logo=target)](https://sih.gov.in)
[![FastAPI Backend](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18 Dashboard](https://img.shields.io/badge/React_18-Dashboard-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![Three.js 3D WebGL](https://img.shields.io/badge/Three.js-3D_Topo_Heatmap-000000?style=for-the-badge&logo=three.js&logoColor=white)](https://threejs.org)
[![XGBoost Calibrated](https://img.shields.io/badge/XGBoost-V2_Spatial_Split-EB392E?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![Sentinel-1 InSAR](https://img.shields.io/badge/Sentinel--1-Radar_InSAR_LOS-003399?style=for-the-badge&logo=nasa&logoColor=white)](https://sentinels.copernicus.eu)
[![Tests Passing](https://img.shields.io/badge/Unit_&_Fuzz_Tests-366_Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](#-automated-testing--code-quality)

**An intelligent, multi-tier geotechnical & satellite radar early warning platform engineered for the high-risk mountainous corridors of Meghalaya and Assam.**

[Live Interactive 3D Demo](#-quick-start) • [Architecture](#-system-architecture) • [Key Features](#-core-capabilities) • [API Specification](#-api-reference) • [Test Verification](#-automated-testing--code-quality)

---

</div>

## 📌 Executive Summary

The North Eastern Region (NER) of India represents one of the most landslide-vulnerable landscapes in the world. During severe southwest monsoon cloudbursts, critical highway lifelines—including **NH-40 (Shillong–Dawki Road)** and **NH-6 (Guwahati–Silchar Corridor)**—experience frequent, catastrophic slope failures that strand vulnerable settlements, paralyze freight routes, and disrupt medical access.

**NER-LEWS (North Eastern Region Landslide Early Warning System)** bridges the critical gap between space-borne remote sensing and on-the-ground disaster mobilization. By fusing **European Space Agency Sentinel-1 Synthetic Aperture Radar (InSAR)** millimeter-velocity ground creep measurements, **real-time precipitation telemetry**, **Limit-Equilibrium Slope Stability physics (Factor of Safety)**, and **Platt-calibrated XGBoost machine learning with SHAP explainability**, NER-LEWS delivers hyper-local, actionable warnings with up to **72-hour forecast lead times**.

---

## ⚡ System Architecture

NER-LEWS is architected as an asynchronous, decoupled microservice ecosystem designed for mission-critical resilience, zero-token local GIS capability, and offline edge reliability:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SATELLITE & SENSOR INGESTION LAYER                     │
├───────────────────────────────┬───────────────────────────────┬────────────────────────┤
│  Sentinel-1 SAR InSAR (LOS)   │   Open-Meteo & IMD Telemetry  │   DEM / Geospatial GIS │
│  - Satellite Orbit Interferom.│   - 1h / 6h / 12h / 24h Rain  │   - Slope, Aspect, TWI │
│  - Millimeter Creep (mm/yr)   │   - 72h Forecast Cloudburst   │   - Soil Cohesion & Kh │
└───────────────┬───────────────┴───────────────┬───────────────┴────────────┬───────────┘
                │                               │                            │
                ▼                               ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  ANALYTICAL & ML ENGINE (ml/ & backend/)               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Hybrid Risk Scorer: Calibrated XGBoost V2 (Platt Scaling) + Random Forest          │
│  2. Physics Safety Shield: Factor of Safety (FS = Resisting Shear / Driving Shear)     │
│  3. Caine (1980) Critical Intensity-Duration Rainfall Threshold Curve Validation       │
│  4. Human-Interpretable SHAP Feature Attribution (Pore Pressure, Saturation, Slope)   │
└───────────────────────────────────────┬────────────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND SERVICES (backend/)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  • Geotechnical & Radar Service      • Multilingual AI Safety Assistant (LLM + Engine) │
│  • CAP Automated Alert Dispatcher    • Evacuation & Highway Detour Priority Router     │
│  • Offline Sync & Ingestion API      • SQLite / PostgreSQL Async Persistence           │
└───────────────────────────────────────┬────────────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             REACT 18 CLIENT DASHBOARD (frontend/)                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  • Three.js 3D Topographic Terrain View with Orbit & Elevation Inspector               │
│  • Zero-Key Monochrome Leaflet GIS Heatmap with Real-Time Risk Contours                │
│  • Recharts 72-Hour Precipitation & Caine Dynamic Threshold Curve                      │
│  • Multilingual Citizen Assistant: English, Hindi, Assamese, Khasi, Garo (Voice TTS)  │
│  • Offline-First Hazard Reporting with Automatic Photo Compression & Sync Queue        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Core Capabilities

### 1. 🔬 Dual-Layer Hybrid Risk Model (Physics + AI)
* **Slope Stability Physics**: Calculates real-time **Factor of Safety ($FS$)** using infinite-slope limit equilibrium mechanics incorporating soil cohesion ($c'$), internal friction angle ($\phi'$), slope inclination ($\beta$), and pore water pressure ($u$):
  $$FS = \frac{c' + (\gamma z \cos^2\beta - u)\tan\phi'}{\gamma z \sin\beta\cos\beta}$$
* **Caine (1980) Critical Rainfall Curve**: Dynamic evaluation against regional cloudburst threshold equation $I = 14.82 \cdot D^{-0.39}$.
* **Spatial ML Generalization**: XGBoost V2 trained with geographic block holdouts to prevent spatial autocorrelation leakage. Calibrated probabilities via sigmoid scaling.
* **SHAP Explainability**: Every prediction includes top contributing geotechnical and environmental risk factors in plain human language.

### 2. 🛰️ Space Radar Telemetry (Sentinel-1 InSAR)
* Ingests radar Line-of-Sight (LOS) displacement velocities (mm/year).
* Detects sub-centimeter slope deformation weeks before catastrophic tension cracks become visible to ground observers.
* Provides radar coherence quality metrics ($\gamma \ge 0.65$) for field safety reliability.

### 3. 🌐 Interactive 3D Topographic Heatmap (Three.js WebGL)
* Photorealistic 3D terrain elevation representation of East Khasi Hills and Garo Hills ridges (Shillong Peak 1,496m, Sohra Plateau 1,430m, Mawsynram 1,400m, Jowai 1,380m, Tura Peak 872m).
* Real-time camera orbital navigation, isometric 45° angle presets, elevation contour scaling, and live sector weather inspector overlay.

### 4. 🗣️ Multilingual Regional Disaster Assistant & Voice TTS
* 24/7 AI-powered conversational safety companion supporting 5 regional languages:
  * **English (EN)**
  * **हिन्दी (Hindi)**
  * **অসমীয়া (Assamese)**
  * **Ka Ktien Khasi (Khasi)**
  * **A·chik (Garo)**
* Native audio speech readout for low-literacy rural citizens.
* Automatic GPS location snapping with nearest designated community evacuation shelters and medical CHCs.

### 5. 📴 Offline-First Citizen Hazard Reporter
* LocalStorage / IndexedDB background retry queue (`offlineQueue.js`) designed for remote mountain zones with intermittent 2G/EDGE cellular connectivity.
* Client-side canvas image downsampling (max 1024px, 70% JPEG compression) to enable emergency uploads over constrained bandwidth.
* Automatic auto-flush upon browser online event detection.

### 6. 🚨 Automated Civil Defense & Evacuation Prioritization
* Standardized 4-tier risk classification:
  * 🟢 **Low Risk (FS > 1.30)**: Stable slope conditions.
  * 🟡 **Moderate Risk (FS 1.15–1.30)**: Precautionary advisory; road monitoring.
  * 🟠 **High Risk (FS 1.00–1.15)**: Stage-2 evacuation alert; heavy truck diversion.
  * 🔴 **Severe Risk (FS < 1.00)**: Red Alert; mandatory immediate evacuation.
* **Evacuation Priority Index ($EPI$)** algorithm prioritizing rescue assets based on hazard severity, population density, and road blockage vulnerability:
  $$EPI = W_{\text{risk}} \times \log_{10}(P_{\text{settlement}}) \times D_{\text{accessibility}}$$

---

## 📂 Repository Structure

```
SIH-2026/
├── backend/                             # Core FastAPI Asynchronous Microservice
│   ├── app/
│   │   ├── api/                         # REST Endpoints (alerts, chat, radar, roads, tts, weather, zones)
│   │   ├── services/                    # Domain Business Logic
│   │   │   ├── ingestion/               # Weather poller & satellite telemetry fetchers
│   │   │   ├── ml/                      # Live XGBoost inference, physics safety shield, SHAP explainer
│   │   │   ├── ai_chat_service.py       # Multilingual AI conversational engine
│   │   │   ├── alert_service.py         # Multi-tier CAP alert evaluator & dispatcher
│   │   │   ├── notification_service.py  # Twilio SMS / push notification handler
│   │   │   └── radar_service.py         # Sentinel-1 InSAR data service
│   │   ├── config.py                    # Pydantic v2 settings & environment configuration
│   │   ├── database.py                  # High-precision mock & persistent database models
│   │   └── main.py                      # FastAPI application bootstrap & CORS
│   ├── tests/                           # Pytest Suite (266 unit, fuzz, concurrency & physics tests)
│   ├── .env.example                     # Sample backend environment variables
│   └── requirements.txt                 # Backend Python dependencies
├── frontend/                            # React 18 Citizen & Command Center Dashboard
│   ├── public/                          # HTML5 index and static assets
│   ├── src/
│   │   ├── components/                  # Core React & Three.js GIS UI components
│   │   │   ├── AlertBanner.jsx          # Live emergency notification marquee
│   │   │   ├── DashboardLayout.jsx      # High-density operational cockpit
│   │   │   ├── DisasterAdvisoryCard.jsx # Actionable civil defense advisory card
│   │   │   ├── EmergencyAiChat.jsx      # Multilingual conversational assistant with voice TTS
│   │   │   ├── EmergencyPrioritizationCard.jsx # Evacuation triage ranking table
│   │   │   ├── Legend.jsx               # Monochrome map symbology & risk scale
│   │   │   ├── MapView.jsx              # Zero-token Leaflet GIS vector heatmap
│   │   │   ├── Navbar.jsx               # Navigation bar with language selector & simulation badge
│   │   │   ├── RecentReportsTable.jsx   # Citizen report feed with offline badge sync
│   │   │   ├── ReportModal.jsx          # Geotagged hazard reporting with photo compression
│   │   │   ├── RiskSummaryCard.jsx      # Aggregated sector metrics & FS distribution
│   │   │   ├── RoadTable.jsx            # Highway corridor blockages & alternate routes
│   │   │   ├── TerminologyModal.jsx     # Geotechnical science glossary with voice synthesis
│   │   │   ├── ThreeDMapHeatmap.jsx     # Three.js 3D topographic terrain visualization
│   │   │   └── WeatherChart.jsx         # 72h rainfall forecast & Caine critical threshold curve
│   │   ├── contexts/                    # Global React state (AppContext.jsx)
│   │   ├── mockData/                    # Offline GIS GeoJSON, settlements, roads, weather fixtures
│   │   ├── services/                    # API client & offline resilience queue
│   │   ├── styles/                      # Tailwind CSS & custom monochrome design tokens
│   │   ├── utils/                       # Speech synthesis engine & 5-language dictionaries
│   │   └── __tests__/                   # Jest/React Testing Library Suite (100 component tests)
│   ├── .env.example                     # Sample frontend environment variables
│   └── package.json                     # Frontend npm dependencies & scripts
├── ml/                                  # Machine Learning Training & Experimentation Pipeline
│   ├── api/                             # Dedicated ML prediction microservice
│   ├── data/                            # Training data contracts & synthetic generators
│   ├── src/                             # Feature engineering, spatial cross-validation, train/predict
│   ├── models/                          # Versioned serialized model artifacts (.pkl)
│   ├── Dockerfile                       # Container definition for ML inference
│   ├── docker-compose.yml               # Multi-container compose configuration
│   └── requirements.txt                 # ML Python dependencies
├── .gitignore                           # Production gitignore (excluding node_modules, venv, secrets)
└── README.md                            # Comprehensive system documentation
```

---

## 🚀 Quick Start

### Prerequisites
* **Node.js**: v18.x or higher
* **Python**: v3.10 to v3.14
* **Git**

---

### 1. Backend Setup (FastAPI)

```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Frontend Setup (React 18)

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
copy .env.example .env

# Launch development dashboard
npm start
```

* Dashboard UI: [http://localhost:3000](http://localhost:3000)

---

### 3. Machine Learning Pipeline (ml/)

```bash
cd ml

# Train XGBoost V2 model with spatial holdout validation
python src/train.py

# Evaluate batch predictions and SHAP factor attribution
python src/predict.py
```

---

### 4. Docker Deployment

```bash
# Launch entire backend, ML inference, and PostgreSQL stack
docker-compose up --build
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|:---:|---|---|
| `GET` | `/api/v1/zones/geojson` | Returns dynamic GeoJSON FeatureCollection of mountain risk zones with live FS |
| `GET` | `/api/v1/zones/summary` | Aggregated risk metrics, active alerts count, and critical monitoring zones |
| `POST` | `/api/v1/predict-risk` | Hybrid XGBoost + Limit-Equilibrium Slope Stability prediction with SHAP factors |
| `POST` | `/api/v1/predict/batch` | Batch inference endpoint for GIS grid raster cells |
| `GET` | `/api/v1/radar/insar` | Real-time Sentinel-1 InSAR line-of-sight ground displacement velocities |
| `GET` | `/api/v1/weather/forecast` | 72-hour precipitation forecast, saturation index, and Caine threshold curve |
| `GET` | `/api/v1/roads/status` | National & state highway blockages, landslide locations, and detours |
| `GET` | `/api/v1/emergency/prioritization` | Ranked community evacuation triage list based on Evacuation Priority Index |
| `POST` | `/api/v1/reports` | Citizen crowd-sourced landslide report intake with base64 image support |
| `GET` | `/api/v1/chat/welcome` | Multilingual conversational greeting and suggested mountain locations |
| `POST` | `/api/v1/chat/ask` | Conversational safety advice with live geotechnical telemetry and voice text |
| `POST` | `/api/v1/tts/synthesize` | Edge/cloud speech synthesis endpoint for local languages |

---

## 🧪 Automated Testing & Code Quality

Both frontend and backend include rigorous test suites verifying numerical physics stability, API fuzzing, concurrency, and UI components:

```bash
# Run all Backend Pytest Suites (266 tests)
cd backend
pytest -v

# Run all Frontend Component & Integration Suites (100 tests)
cd frontend
npm test -- --watchAll=false
```

### Test Coverage Highlights:
* **Backend (`backend/tests`)**:
  * `test_alerts_engine.py`: CAP alert triggers, cooldown mechanics, and notification dispatching.
  * `test_api.py` & `test_api_alerts_management.py`: Comprehensive REST API integration validation.
  * `test_challenger_concurrency.py` & `test_challenger_m2_concurrency_stress.py`: High-concurrency stress testing.
  * `test_challenger_m2_api_fuzzing.py`: Malformed payload resilience and edge boundary validation.
  * `test_challenger_physics_cooldown.py`: Hysteresis and rapid precipitation fluctuation dampening.
  * `test_chat.py`: Multilingual safety advisory responses in English, Hindi, Assamese, Khasi, and Garo.
  * `test_ml.py`: XGBoost prediction bounds, calibration, and SHAP factor integrity.
  * `test_tts.py`: Multi-voice synthesis audio generation.
* **Frontend (`frontend/src/__tests__`)**:
  * 15 passing test suites covering 100 tests across GIS map rendering, Three.js 3D controls, weather analytics, offline queue recovery, modal interactions, and translations.

---

## 🛡️ Built-in Security & Production Standards

* **Credential Protection**: Zero hardcoded secrets; `.gitignore` enforced to protect `.env`, virtual environments, and temporary caches.
* **Offline Resilience**: Automatic graceful degradation from live REST APIs to cached GIS fixtures when offline.
* **Zero-Token GIS**: Localized map layers rendered via Leaflet and Three.js canvas shaders without requiring paid external map tile keys.
* **Data Privacy**: Citizen field reports sanitized and stored with local timestamps and verified GPS bounds.

---

## 👥 Hackathon Attribution

* **Smart India Hackathon (SIH 2026)**
* **Problem Statement**: SIH26001 — AI/ML Landslide Early Warning & Geo-Hazard Intelligence System
* **Repository**: [https://github.com/akash-taurus/SIH-2026](https://github.com/akash-taurus/SIH-2026)

---

<div align="center">
  <b>Developed for disaster resilience and life safety in the North Eastern Region of India.</b>
</div>
