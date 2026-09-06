import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_chat_welcome_multilingual():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test English
        res_en = await ac.get("/api/v1/chat/welcome?language=en")
        assert res_en.status_code == 200
        data_en = res_en.json()
        assert "AI Disaster & Safety Assistant" in data_en["greeting"]
        assert len(data_en["suggested_locations"]) > 0

        # Test Khasi
        res_kha = await ac.get("/api/v1/chat/welcome?language=kha")
        assert res_kha.status_code == 200
        data_kha = res_kha.json()
        assert "Khublei" in data_kha["greeting"] or "খুব্লেই" in data_kha["greeting"]

        # Test Garo
        res_grt = await ac.get("/api/v1/chat/welcome?language=grt")
        assert res_grt.status_code == 200
        data_grt = res_grt.json()
        assert "Salam" in data_grt["greeting"] or "চালাম" in data_grt["greeting"]

        # Test Hindi
        res_hi = await ac.get("/api/v1/chat/welcome?language=hi")
        assert res_hi.status_code == 200
        data_hi = res_hi.json()
        assert "नमस्ते" in data_hi["greeting"]

        # Test Assamese
        res_as = await ac.get("/api/v1/chat/welcome?language=as")
        assert res_as.status_code == 200
        data_as = res_as.json()
        assert "নমস্কাৰ" in data_as["greeting"]

@pytest.mark.asyncio
async def test_chat_ask_laitlyngkot_native_responses():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test Khasi response for Laitlyngkot
        payload_kha = {
            "query": "হতো কা শ্ঙায়িন বান সাহ হা লাইতলিংকট?",
            "location": "Laitlyngkot",
            "language": "kha"
        }
        res_kha = await ac.post("/api/v1/chat/ask", json=payload_kha)
        assert res_kha.status_code == 200
        data_kha = res_kha.json()
        assert data_kha["risk_level"] in ["High", "Moderate", "Low"]
        assert data_kha["factor_of_safety"] is not None
        assert len(data_kha["response"]) > 0

        # Test Hindi response for Laitlyngkot
        payload_hi = {
            "query": "क्या लैटलिंगकोट में भूस्खलन का खतरा है?",
            "location": "Laitlyngkot",
            "language": "hi"
        }
        res_hi = await ac.post("/api/v1/chat/ask", json=payload_hi)
        assert res_hi.status_code == 200
        data_hi = res_hi.json()
        assert len(data_hi["response"]) > 0

@pytest.mark.asyncio
async def test_chat_gps_snapping_and_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test GPS near Sohra (lat 25.27, lon 91.73)
        payload_gps = {
            "query": "Where is the nearest safe evacuation shelter?",
            "lat": 25.2711,
            "lon": 91.7312,
            "language": "en"
        }
        res = await ac.post("/api/v1/chat/ask", json=payload_gps)
        assert res.status_code == 200
        data = res.json()
        assert "Sohra" in data["location"]
        assert data["factor_of_safety"] is not None
        assert data["rainfall_24h_mm"] is not None
        assert "Sohra" in data["shelter"]
        assert "Sohra CHC" in data["hospital"]
        assert "SH-5" in data["road"]
        assert len(data["response"]) > 0

