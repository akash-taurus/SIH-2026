# 🎨 NER-LEWS Frontend Client (Monochrome React Dashboard)

> **Assigned Team**: **Member 3 (Frontend Lead)**, **Member 4 (UI/UX Specialist)**, **Member 5 (Analytics & i18n)**

---

## 📌 Architecture & Design Principles

* **Strictly Monochrome**: Pure black (`#000000`), white (`#FFFFFF`), and functional grayscale fills (`#EBEBEB`, `#AAAAAA`, `#444444`, `#000000`).
* **Zero-Key GIS**: Leaflet.js with CSS grayscale canvas filters for instant local running without paid Mapbox tokens.
* **Multilingual**: Instant toggle between **English**, **Hindi (हिन्दी)**, and **Assamese (অসমীয়া)**.
* **Dual API Mode**: Toggle between static mock data (`src/mockData/`) and live FastAPI backend (`/api/v1/`) via `REACT_APP_USE_MOCK`.

---

## 👥 Frontend Sub-Team Roles & Component Ownership

| Member | Sub-Domain | Core Components / Files |
|:---:|---|---|
| **Member 3 (Frontend Lead)** | **Map & State Architecture** | `MapView.jsx`, `Legend.jsx`, `AppContext.jsx`, `services/api.js`, custom hooks. |
| **Member 4 (UI/UX Specialist)** | **Design Tokens & Core UI** | `globals.css`, `Navbar.jsx`, `AlertBanner.jsx`, `RiskSummaryCard.jsx`, `RoadTable.jsx`, `EmergencyPrioritizationCard.jsx`. |
| **Member 5 (Data & i18n)** | **Charts, Localization & Mocks** | `WeatherChart.jsx`, `translations.js`, `ReportModal.jsx`, `src/mockData/*.json`. |

---

## 🚀 Getting Started

### 1. Installation
```bash
npm install
```

### 2. Environment Variables (`.env`)
```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_USE_MOCK=true
```

### 3. Run Development Server
```bash
npm start
```
Runs the app at `http://localhost:3000`.

### 4. Run Automated Component Tests
```bash
npm test
```

---

## 📁 Source Directory Structure
```
frontend/src/
├── assets/                  # Black line SVG icons
├── components/              # Presentation & GIS components
│   ├── Navbar.jsx
│   ├── AlertBanner.jsx
│   ├── MapView.jsx
│   ├── Legend.jsx
│   ├── RiskSummaryCard.jsx
│   ├── WeatherChart.jsx
│   ├── RoadTable.jsx
│   ├── EmergencyPrioritizationCard.jsx
│   └── ReportModal.jsx
├── contexts/                # React global state (AppContext.jsx)
├── hooks/                   # Custom data fetching hooks
├── mockData/                # Static JSON mock fixtures
│   ├── riskZones.json
│   ├── riskSummary.json
│   ├── weather.json
│   ├── roads.json
│   ├── emergency.json
│   └── reports.json
├── services/                # Axios / fetch client (api.js)
├── styles/                  # globals.css & Tailwind config
├── utils/                   # translations.js & date formatters
├── App.jsx                  # Main dashboard layout
└── index.js
```