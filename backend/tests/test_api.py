import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "NER-LEWS" in data["service"]

@pytest.mark.asyncio
async def test_risk_zones_geojson():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/risk-zones")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 6
    assert data["features"][0]["properties"]["zone_id"] == "Z-SHL-01"

@pytest.mark.asyncio
async def test_risk_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/risk-summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    levels = [item["level"] for item in data]
    assert "Severe" in levels
    assert "Low" in levels

@pytest.mark.asyncio
async def test_roads_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/roads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    assert any(r["road_id"] == "NH-40" for r in data)

@pytest.mark.asyncio
async def test_emergency_prioritization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/emergency-prioritization")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    assert data[0]["priority_rank"] == 1

@pytest.mark.asyncio
async def test_weather_forecast():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/weather/forecast?lat=25.5788&lon=91.8933")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "rainfall" in data[0]
    assert "caineThreshold" in data[0]

@pytest.mark.asyncio
async def test_predict_risk_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/predict-risk", json={
            "slope_deg": 38.0,
            "rain_1h": 40.0,
            "rain_24h": 160.0,
            "rain_7d": 300.0,
            "soil_saturation_pct": 0.90,
            "dist_to_road_m": 20.0
        })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ["High", "Severe"]
    assert data["physics_threshold_breached"] is True
    assert "top_contributing_factors" in data
    assert len(data["top_contributing_factors"]) > 0

@pytest.mark.asyncio
async def test_predict_batch_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/predict/batch", json={
            "cells": [
                {"lat": 25.5, "lon": 91.8, "slope_deg": 40.0, "rain_24h": 180.0},
                {"lat": 25.9, "lon": 91.9, "slope_deg": 10.0, "rain_24h": 15.0}
            ]
        })
    assert response.status_code == 200
    data = response.json()
    assert data["total_cells"] == 2
    assert "risk_counts" in data
    assert len(data["results"]) == 2

@pytest.mark.asyncio
async def test_alerts_and_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        alerts_res = await ac.get("/api/v1/alerts")
        auth_res = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": "secretpassword"})
    assert alerts_res.status_code == 200
    assert auth_res.status_code == 200
    assert "access_token" in auth_res.json()
