import httpx
import os
import math
import re
from typing import Dict, Any, Optional
from app.config import settings
from app.services.ingestion.weather_poller import fetch_live_meteorology
from app.services.ml.physics import PhysicsSafetyShield

# Canonical Knowledge Base for North-East India Locations & Baseline Telemetry
LOCATIONS_DB = {
    "laitlyngkot": {
        "canonical_name": "Laitlyngkot Slope Dwellings (East Khasi Hills)",
        "zone_code": "Z-SHL-01",
        "lat": 25.4485,
        "lon": 91.8385,
        "slope_deg": 38.5,
        "soil_type": "Clayey Loam on Weathered Quartzite",
        "baseline_fs": 1.14,
        "baseline_rain_24h": 125.0,
        "baseline_sat_pct": 0.78,
        "insar_creep": "-12.4 mm/yr",
        "shelter": "Laitlyngkot Community Hall",
        "hospital": "Pynursla CHC (8.5 km away)",
        "road": "SH-5 Shillong-Dawki Road",
        "road_status": "Restricted (Heavy trucks halted)",
        "diversion": "Light vehicles proceed with caution; heavy freight trucks must divert via Mawphlang-Mawsynram alternate link"
    },
    "shillong": {
        "canonical_name": "Shillong Peak Ridge & Upper Shillong",
        "zone_code": "Z-SHL-01",
        "lat": 25.5788,
        "lon": 91.8933,
        "slope_deg": 38.4,
        "soil_type": "Clayey Loam on Weathered Quartzite",
        "baseline_fs": 0.88,
        "baseline_rain_24h": 142.5,
        "baseline_sat_pct": 0.82,
        "insar_creep": "-14.2 mm/yr",
        "shelter": "Happy Valley Indoor Stadium / Nongthymmai Relief Center",
        "hospital": "Shillong Civil Hospital",
        "road": "Upper Shillong Bypass / NH-40",
        "road_status": "Blocked (Active Debris Runoff)",
        "diversion": "Blocked near Umiam dam; all traffic diverted via Umroi–Byrnihat bypass corridor"
    },
    "sohra": {
        "canonical_name": "Sohra Plateau & Cherrapunji Rim (1,430m MSL)",
        "zone_code": "Z-CHR-02",
        "lat": 25.2711,
        "lon": 91.7312,
        "slope_deg": 35.8,
        "soil_type": "Limestone Karst & Fractured Sandstone",
        "baseline_fs": 1.09,
        "baseline_rain_24h": 210.0,
        "baseline_sat_pct": 0.85,
        "insar_creep": "-18.6 mm/yr",
        "shelter": "Sohra Community Health Centre & Eco-Park Shelter",
        "hospital": "Sohra CHC",
        "road": "SH-5 Sohra-Shella Route",
        "road_status": "Restricted (Falling Boulders)",
        "diversion": "Single lane open; strictly avoid lower Shella gorge descent during heavy downpours"
    },
    "nh-6": {
        "canonical_name": "NH-6 Jorabat–Shillong Expressway (GS Road)",
        "zone_code": "Z-NONG-05",
        "lat": 25.6800,
        "lon": 91.9100,
        "slope_deg": 34.0,
        "soil_type": "Clayey Loam on Weathered Quartzite",
        "baseline_fs": 1.22,
        "baseline_rain_24h": 85.0,
        "baseline_sat_pct": 0.70,
        "insar_creep": "-8.2 mm/yr",
        "shelter": "Nongpoh Tourist Lodge & Umsning Block Office",
        "hospital": "Nongpoh District Civil Hospital",
        "road": "NH-6 Expressway (old NH-40)",
        "road_status": "Single-Lane Operational (Mudslide clearance near Umiam dam)",
        "diversion": "Light vehicles permitted with caution; heavy freight trucks must divert via Umroi–Byrnihat alternate link"
    },
    "jowai": {
        "canonical_name": "Jowai Cut-Slope Bypass Corridor (West Jaintia Hills)",
        "zone_code": "Z-JOW-04",
        "lat": 25.4412,
        "lon": 92.2033,
        "slope_deg": 27.2,
        "soil_type": "Shale and Coal-bearing Sandstone",
        "baseline_fs": 1.35,
        "baseline_rain_24h": 88.0,
        "baseline_sat_pct": 0.65,
        "insar_creep": "-6.8 mm/yr",
        "shelter": "Jowai Indoor Stadium & Ialong Community Centre",
        "hospital": "Jowai Civil Hospital (Ialong)",
        "road": "NH-6 Shillong-Jowai-Silchar Highway",
        "road_status": "At Risk (Road cave-in & debris in East Jaintia Hills stretch)",
        "diversion": "Single lane open; monitor Sonapur tunnel bypass for sudden rockfalls"
    },
    "nongpoh": {
        "canonical_name": "Nongpoh Valley Corridor (Ri-Bhoi District)",
        "zone_code": "Z-NONG-05",
        "lat": 25.9011,
        "lon": 91.8812,
        "slope_deg": 14.2,
        "soil_type": "Alluvial Valley Fill",
        "baseline_fs": 1.72,
        "baseline_rain_24h": 42.0,
        "baseline_sat_pct": 0.45,
        "insar_creep": "-2.1 mm/yr",
        "shelter": "Nongpoh Tourist Lodge & Umsning Block Office",
        "hospital": "Nongpoh District Civil Hospital",
        "road": "GS Road / NH-40 Lowland Sector",
        "road_status": "Open (Normal traffic flow)",
        "diversion": "All transit lanes fully operational"
    },
    "tura": {
        "canonical_name": "Tura Peak Forest Slope (West Garo Hills)",
        "zone_code": "Z-TURA-06",
        "lat": 25.5144,
        "lon": 90.2211,
        "slope_deg": 31.5,
        "soil_type": "Archaean Gneiss Complex",
        "baseline_fs": 1.28,
        "baseline_rain_24h": 95.0,
        "baseline_sat_pct": 0.68,
        "insar_creep": "-7.5 mm/yr",
        "shelter": "Tura Indoor Stadium & DC Office Relief Camp",
        "hospital": "Tura Civil Hospital",
        "road": "NH-217 Tura-Dalu Route",
        "road_status": "Open with Caution",
        "diversion": "Exercise extreme caution near forested slope cuttings; avoid night driving"
    },
    "mawsynram": {
        "canonical_name": "Mawsynram Deep Canyons (East Khasi Hills)",
        "zone_code": "Z-MAW-03",
        "lat": 25.2988,
        "lon": 91.5822,
        "slope_deg": 42.1,
        "soil_type": "Highly Saturated Colluvium",
        "baseline_fs": 0.93,
        "baseline_rain_24h": 265.0,
        "baseline_sat_pct": 0.92,
        "insar_creep": "-21.5 mm/yr",
        "shelter": "Mawsynram Higher Secondary School Relief Camp",
        "hospital": "Mawsynram CHC",
        "road": "Mawsynram-Balat Link Road",
        "road_status": "Blocked (Active Debris Flow at Km 14)",
        "diversion": "Traffic halted; emergency relief convoys diverted via Weiloi link"
    }
}

WELCOME_MESSAGES = {
    "en": {
        "greeting": "Hello! I am your AI Disaster & Safety Assistant.",
        "ask_location": "Please tell me your current location or tap '📍 Use My GPS Location' (e.g. Laitlyngkot, Shillong, Sohra, Jowai, Tura, Nongpoh, or NH-40 highway) so I can compute live satellite & geotechnical safety telemetry for you."
    },
    "kha": {
        "greeting": "Khublei! Nga dei u AI Disaster & Safety Assistant jong phi.",
        "ask_location": "Sngewbha pynpaw ia ka jaka ba phi don mynta lane kdup '📍 Use My GPS Location' (kum Laitlyngkot, Shillong, Sohra, Jowai, Tura, Nongpoh, lane NH-40 surok bah) khnang ban peit bniah ia ka jingshngain lyngba ka live Satellite & Geotechnical Telemetry."
    },
    "grt": {
        "greeting": "Salam! Anga AI Disaster & Safety Assistant ong·a.",
        "ask_location": "Da·o na·a songo/biyapo donga (jekai Laitlyngkot, Shillong, Sohra, Jowai, Tura, Nongpoh, ba NH-40 rama) uko on·atbo ba '📍 Use My GPS Location' click ka·bo, anga live satellite aro weather telemetry-ko nina man·gen."
    },
    "hi": {
        "greeting": "नमस्ते! मैं आपका एआई आपदा पूर्व चेतावनी एवं सुरक्षा सहायक हूँ।",
        "ask_location": "कृपया अपना वर्तमान स्थान बताएं या '📍 Use My GPS Location' पर टैप करें (जैसे लैटलिंगकोट, शिलांग, सोहरा, जोवाई, तुरा, नोंगपोह, या NH-40 राजमार्ग), ताकि मैं आपके लिए लाइव उपग्रह एवं भू-तकनीकी सुरक्षा स्थिति की गणना कर सकूं।"
    },
    "as": {
        "greeting": "নমস্কাৰ! মই আপোনাৰ AI দুৰ্যোগ আৰু সুৰক্ষা সহায়ক (NER-LEWS)।",
        "ask_location": "অনুগ্ৰহ কৰি আপোনাৰ বৰ্তমান স্থান জনাওক বা '📍 Use My GPS Location' ক্লিক কৰক (যেনে লাইতলিংকট, শ্বিলং, চোহৰা, জোৱাই, তুৰা, নংপো বা NH-40 ঘাইপথ), যাতে মই লাইভ উপগ্ৰহ আৰু ভূ-পদাৰ্থবিজ্ঞান নিৰাপত্তা পৰীক্ষা কৰিব পাৰোঁ।"
    }
}

def detect_location_key(text: str) -> Optional[str]:
    """Matches user input against known disaster sectors."""
    t = text.lower().strip()
    if t in LOCATIONS_DB:
        return t
    if "laitlyngkot" in t or "laitlyng" in t or "pynursla" in t:
        return "laitlyngkot"
    elif "shillong" in t or "upper shillong" in t or "happy valley" in t or "peak ridge" in t:
        return "shillong"
    elif "sohra" in t or "cherra" in t or "cherrapunji" in t or "shella" in t:
        return "sohra"
    elif "mawsynram" in t or "balat" in t or "weiloi" in t:
        return "mawsynram"
    elif "jowai" in t or "ialong" in t or "jaintia" in t:
        return "jowai"
    elif "nongpoh" in t or "ri-bhoi" in t or "ri bhoi" in t:
        return "nongpoh"
    elif "nh-40" in t or "nh40" in t or "nh-6" in t or "nh6" in t or "guwahati" in t or "gs road" in t or "umiam" in t or "jorabat" in t:
        return "nh-6"
    elif "tura" in t or "garo" in t:
        return "tura"
    return None

def snap_coordinates_to_sector(lat: float, lon: float) -> Optional[str]:
    """Finds the closest monitored hazard sector to given lat/lon coordinates."""
    closest_key = None
    min_dist = float("inf")
    # Roughly 1 degree of lat/lon is ~111 km. 1.0 degree is a safe threshold for "in the region".
    MAX_RADIUS_DEGREES = 1.0 
    
    for key, loc in LOCATIONS_DB.items():
        loc_lat = loc.get("lat")
        loc_lon = loc.get("lon")
        if loc_lat is not None and loc_lon is not None:
            dist = math.hypot(lat - loc_lat, lon - loc_lon)
            if dist < min_dist:
                min_dist = dist
                closest_key = key
                
    if min_dist > MAX_RADIUS_DEGREES:
        return None
        
    return closest_key

async def compute_live_geotechnical_telemetry(
    loc_data: Dict[str, Any],
    custom_lat: Optional[float] = None,
    custom_lon: Optional[float] = None
) -> Dict[str, Any]:
    """
    Fetches real-time multi-window precipitation (24h, 48h, 72h) and soil saturation from Open-Meteo,
    and dynamically solves the Infinite Slope Factor of Safety (FS) & pore pressure (u) equation.
    """
    lat = custom_lat if custom_lat is not None else loc_data["lat"]
    lon = custom_lon if custom_lon is not None else loc_data["lon"]
    slope_deg = loc_data.get("slope_deg", 35.0)
    soil_type = loc_data.get("soil_type", "default")
    
    try:
        weather_json = await fetch_live_meteorology(lat=lat, lon=lon)
        current = weather_json.get("current", {})
        hourly = weather_json.get("hourly", {})
        
        rain_1h = float(current.get("precipitation", current.get("rain", 0.0)))
        hourly_precip = hourly.get("precipitation", [0.0] * 72)
        
        rain_24h = round(sum(float(p) for p in hourly_precip[:24] if p is not None), 1)
        rain_48h = round(sum(float(p) for p in hourly_precip[:48] if p is not None), 1)
        rain_72h = round(sum(float(p) for p in hourly_precip[:72] if p is not None), 1)
        
        s0_list = hourly.get("soil_moisture_0_to_1cm", [0.35])
        s1_list = hourly.get("soil_moisture_1_to_3cm", [0.35])
        s0 = float(s0_list[0]) if s0_list and s0_list[0] is not None else 0.35
        s1 = float(s1_list[0]) if s1_list and s1_list[0] is not None else 0.35
        soil_sat_pct = min(round(((s0 + s1) / 2.0) * 100 * 2.2) / 100.0, 0.98)
    except Exception as e:
        print(f"[AI Chat] Live weather query failed, using calibrated baseline telemetry: {e}")
        rain_1h = 2.5
        rain_24h = loc_data.get("baseline_rain_24h", 65.0)
        rain_48h = round(rain_24h * 1.5, 1)
        rain_72h = round(rain_24h * 2.1, 1)
        soil_sat_pct = loc_data.get("baseline_sat_pct", 0.68)

    # Geotechnical Infinite Slope Stability calculation
    stability = PhysicsSafetyShield.calculate_factor_of_safety(
        slope_deg=slope_deg,
        soil_type=soil_type,
        soil_saturation_pct=soil_sat_pct,
        rainfall_24h_mm=rain_24h
    )

    computed_fs = stability["factor_of_safety"]
    dynamic_fs = computed_fs # Use the REAL live physics calculation, not the mock baseline
    pore_pressure_kpa = stability["pore_water_pressure_kpa"]
    failure_mode = stability["failure_mode"]

    if dynamic_fs < 1.0:
        risk_level = "Severe"
    elif dynamic_fs <= 1.15:
        risk_level = "High"
    elif dynamic_fs <= 1.40:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    return {
        "fs": dynamic_fs,
        "risk_level": risk_level,
        "pore_water_pressure_kpa": pore_pressure_kpa,
        "rainfall_1h_mm": rain_1h,
        "rainfall_24h_mm": rain_24h,
        "rainfall_48h_mm": rain_48h,
        "rainfall_72h_mm": rain_72h,
        "soil_saturation_pct": soil_sat_pct,
        "failure_mode": failure_mode,
        "lat": lat,
        "lon": lon
    }

async def query_external_llm_api(prompt: str, api_key: str) -> Optional[str]:
    """
    Connects to NVIDIA NIM / Gemini / OpenAI endpoint if API key is configured.
    """
    try:
        # NVIDIA NIM API (keys starting with nvapi-...)
        if api_key.startswith("nvapi-"):
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 400
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]

        # Google Gemini API (keys starting with AIza...)
        elif api_key.startswith("AIza"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]

        # Generic OpenAI / compatible endpoint
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 400
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[AI Chat] External LLM API query failed, using built-in emergency response engine: {e}")
    return None

def build_structured_safety_advisory(
    lang: str,
    loc_data: Dict[str, Any],
    telemetry: Dict[str, Any]
) -> str:
    """
    Generates structured Emergency Safety Advisory in 5 regional languages
    when external LLM is offline or unconfigured.
    """
    loc_name = loc_data["canonical_name"]
    fs = telemetry["fs"]
    risk = telemetry["risk_level"]
    rain24 = telemetry["rainfall_24h_mm"]
    pore_u = telemetry["pore_water_pressure_kpa"]
    creep = loc_data["insar_creep"]
    shelter = loc_data["shelter"]
    hospital = loc_data["hospital"]
    road = loc_data["road"]
    road_status = loc_data["road_status"]
    diversion = loc_data.get("diversion", "Follow traffic police advisories")

    if lang == "hi":
        if risk in ["Severe", "High"]:
            return (
                f"⚠️ आपातकालीन चेतावनी: {loc_name} में भूस्खलन का {risk.upper()} जोखिम है "
                f"(लाइव सुरक्षा गुणक FS = {fs}, 24 घंटे की संचित वर्षा: {rain24} मिमी, पोर जल दबाव: {pore_u} kPa)। "
                f"उपग्रह InSAR ने {creep} भू-विस्थापन दर्ज किया है।\n\n"
                f"🚨 तत्काल आवश्यक कदम:\n"
                f"1. 🛡️ सुरक्षित निकासी शिविर: तुरंत {shelter} में शरण लें।\n"
                f"2. 🏥 निकटतम चिकित्सालय: {hospital}।\n"
                f"3. 🚧 राजमार्ग यातायात स्थिति: {road} वर्तमान में {road_status} है। वैकल्पिक मार्ग: {diversion}।\n\n"
                f"📞 आपातकालीन हेल्पलाइन: 1077 (SDMA) | 1078 (NDRF) | 112।"
            )
        else:
            return (
                f"✅ सुरक्षा स्थिति: {loc_name} में भूस्खलन का जोखिम {risk} है (FS = {fs}, 24h वर्षा: {rain24} मिमी)।\n\n"
                f"📍 महत्वपूर्ण जानकारी:\n"
                f"- सुरक्षित राहत केंद्र: {shelter}\n"
                f"- निकटतम अस्पताल: {hospital}\n"
                f"- सड़क स्थिति: {road} खुली है ({road_status})। {diversion}।\n\n"
                f"भारी बारिश के दौरान सतर्क रहें। हेल्पलाइन: 1077 (SDMA)।"
            )

    elif lang == "kha":
        if risk in ["Severe", "High"]:
            return (
                f"⚠️ JINGMAH BA KHRAW (CRITICAL WARNING): Ka jaka {loc_name} ka don ha ka jingma ba {risk.upper()} "
                f"na ka jingtwa khyndew (Live Factor of Safety FS = {fs}, slap 24 kynta = {rain24} mm, pore pressure = {pore_u} kPa). "
                f"Satellite InSAR ka pyni ba ka khyndew ka nang khih ({creep}).\n\n"
                f"🚨 KI JINGDANG LEH MAR-MAR (Immediate Action Protocol):\n"
                f"1. 🛡️ Jaka Rieh ba Shngain (Shelter): Leit mardor sha {shelter}.\n"
                f"2. 🏥 Hospital / CHC ba Marjan: {hospital}.\n"
                f"3. 🚧 Ka Surok: {road} ka la {road_status}. Ka lynti ba pynphai (Detour): {diversion}.\n\n"
                f"📞 Helpline: 1077 (SDMA) | 1078 (NDRF) | 112."
            )
        else:
            return (
                f"✅ KA JINGSHNGAIN: Ka jaka {loc_name} ka don ha ka kyrdan jingma ba {risk} "
                f"(Live FS = {fs}, slap 24 kynta = {rain24} mm). Ym pat don jingeh ba shisha mynta.\n\n"
                f"📍 JINGTIP BA DONKAM:\n"
                f"- Jaka Rieh: {shelter}\n"
                f"- Hospital: {hospital}\n"
                f"- Surok: {road} ({road_status}). {diversion}.\n\n"
                f"Sumar bha ha kine ki sngi slap jur. SDMA Helpline: 1077."
            )

    elif lang == "grt":
        if risk in ["Severe", "High"]:
            return (
                f"⚠️ DANGER RED ALERT: {loc_name} biapo a·a be·ani dal·begipa {risk.upper()} kenani gnang "
                f"(Live Factor of Safety FS = {fs}, 24 ghantani mikka = {rain24} mm, pore pressure = {pore_u} kPa). "
                f"Satellite InSAR a·a mo·angani ({creep})-ko mesokenga.\n\n"
                f"🚨 BAKBAK DAKNA NANGGIPA KAMRANG (Immediate Actions):\n"
                f"1. 🛡️ Naljokani Shelter Camp: Ta·rake {shelter}-ona re·angbo.\n"
                f"2. 🏥 Hospital / CHC: Sepangbatgipa {hospital}.\n"
                f"3. 🚧 Rama / Highway: {road} da·o {road_status}. Gipin rama (Detour): {diversion}.\n\n"
                f"📞 Emergency Helpline: 1077 (SDMA) | 1078 (NDRF) | 112."
            )
        else:
            return (
                f"✅ NALJOKANI AVASHTHA: {loc_name} biap {risk} kenani avasthao donga "
                f"(Live FS = {fs}, mikka 24h = {rain24} mm). Da·alo maming dal·gipa kenani dongkuja.\n\n"
                f"📍 DAKCHAKANI BIAPRANG:\n"
                f"- Shelter Camp: {shelter}\n"
                f"- Hospital: {hospital}\n"
                f"- Rama: {road} ({road_status}). {diversion}.\n\n"
                f"Mikka jiminani salrango simsakbo. SDMA Helpline: 1077."
            )

    elif lang == "as":
        if risk in ["Severe", "High"]:
            return (
                f"⚠️ চৰম বিপদ সংকেত: {loc_name} অঞ্চলত ভূস্খলনৰ {risk.upper()} আশংকা "
                f"(লাইভ সুৰক্ষা গুণক FS = {fs}, ২৪ ঘণ্টাৰ বৰষুণ: {rain24} মিমি, প'ৰ প্ৰেচাৰ: {pore_u} kPa)। "
                f"উপগ্ৰহ InSAR-এ {creep} মাটিৰ সঞ্চালন ধৰা পেলাইছে।\n\n"
                f"🚨 তাৎক্ষণিক নিৰাপত্তা ব্যৱস্থা:\n"
                f"১. 🛡️ সুৰক্ষিত আশ্ৰয় শিবিৰ: অনতিপলমে {shelter}লৈ যাওক।\n"
                f"২. 🏥 নিকটৱৰ্তী চিকিৎসালয়: {hospital}।\n"
                f"৩. 🚧 ঘাইপথ অৱস্থা: {road} বৰ্তমান {road_status}। বিকল্প পথ: {diversion}।\n\n"
                f"📞 জৰুৰীকালীন হেল্পলাইন: ১০৭৭ (SDMA) | ১০৭৮ (NDRF) | ১১২।"
            )
        else:
            return (
                f"✅ নিৰাপদ অৱস্থা: {loc_name} অঞ্চলত ভূস্খলনৰ আশংকা {risk} (FS = {fs}, ২৪ ঘণ্টাৰ বৰষুণ: {rain24} মিমি)।\n\n"
                f"📍 তথ্য সংগ্ৰহ:\n"
                f"- আশ্ৰয় শিবিৰ: {shelter}\n"
                f"- চিকিৎসালয়: {hospital}\n"
                f"- ঘাইপথ: {road} মুকলি আছে ({road_status})। {diversion}।\n\n"
                f"ধাৰাসাৰ বৰষুণত সতৰ্ক থাকক। হেল্পলাইন: ১০৭৭ (SDMA)।"
            )

    # Default English
    if risk in ["Severe", "High"]:
        return (
            f"⚠️ CRITICAL EMERGENCY WARNING: {loc_name} is under {risk.upper()} landslide risk "
            f"(Live Factor of Safety FS = {fs}, 24h Rainfall: {rain24} mm, Pore Water Pressure: {pore_u} kPa). "
            f"Satellite InSAR detects active ground displacement ({creep}).\n\n"
            f"🚨 Immediate Action Protocol:\n"
            f"1. 🛡️ Safe Evacuation Shelter: Proceed immediately to {shelter}.\n"
            f"2. 🏥 Nearest Medical Hub: {hospital}.\n"
            f"3. 🚧 Highway Corridor: {road} is currently {road_status}. Alternate detour: {diversion}.\n\n"
            f"📞 Emergency Helplines: 1077 (SDMA) | 1078 (NDRF) | 112."
        )
    else:
        return (
            f"✅ GEOTECHNICALLY STABLE: {loc_name} is currently at {risk.upper()} risk "
            f"(Live Factor of Safety FS = {fs}, 24h Rainfall: {rain24} mm). No immediate slope breach detected.\n\n"
            f"📍 Emergency Reference:\n"
            f"- Designated Shelter: {shelter}\n"
            f"- Nearest Hospital: {hospital}\n"
            f"- Road Transit: {road} is open ({road_status}). {diversion}.\n\n"
            f"Maintain standard monsoon alertness. SDMA Control Room: 1077."
        )

def get_welcome_payload(language: str = "en") -> Dict[str, Any]:
    """Returns initial greeting and prompt in user's native language."""
    lang = language if language in WELCOME_MESSAGES else "en"
    msg = WELCOME_MESSAGES[lang]
    return {
        "language": lang,
        "greeting": msg["greeting"],
        "ask_location": msg["ask_location"],
        "suggested_locations": [
            {"name": "Laitlyngkot (SH-5)", "key": "laitlyngkot"},
            {"name": "Shillong Peak Ridge", "key": "shillong"},
            {"name": "Sohra / Cherrapunji", "key": "sohra"},
            {"name": "NH-6 Highway Corridor", "key": "nh-6"}
        ]
    }

async def process_disaster_chat(
    query: str,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Core AI Disaster Assistant processor.
    Dynamically fetches live telemetry (24h/48h/72h rainfall), computes Infinite Slope FS,
    evaluates road status & diversions, and formats strict emergency guidance.
    """
    lang = language if language in ["en", "kha", "grt", "hi", "as"] else "en"
    
    # 1. Detect location key or snap GPS coordinates
    loc_key = None
    if lat is not None and lon is not None:
        loc_key = snap_coordinates_to_sector(lat, lon)
    else:
        # Try to extract coordinates from text (e.g. "im at 25.5316, 91.8512")
        coord_match = re.search(r"(-?\d{1,2}\.\d{2,})[,\s]+(-?\d{1,3}\.\d{2,})", query)
        if coord_match:
            try:
                parsed_lat = float(coord_match.group(1))
                parsed_lon = float(coord_match.group(2))
                loc_key = snap_coordinates_to_sector(parsed_lat, parsed_lon)
                if loc_key:
                    lat, lon = parsed_lat, parsed_lon
            except ValueError:
                pass
                
        if not loc_key:
            loc_key = detect_location_key(location or query)
    
    # 2. Check if external AI API Key is configured
    ai_key = settings.AI_MODEL_API_KEY or os.environ.get("AI_MODEL_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    # 3. If location is completely unrecognized, try LLM for general chat or fallback
    if not loc_key:
        if ai_key:
            prompt = (
                f"You are the NER-LEWS Emergency AI Safety Officer for Meghalaya and North-East India.\n"
                f"The user has sent a message, but we could not detect a specific monitored hazard zone (like Shillong, Sohra, Tura, etc.).\n"
                f"User Message: \"{query}\"\n\n"
                f"If the user is sharing their GPS location (e.g. 'Checking live safety at my GPS location...') and it is not recognized, kindly inform them that their coordinates are outside the NER-LEWS monitoring area (which only covers Meghalaya & North-East India).\n"
                f"If the user is asking a general question about landslides, weather, or safety, answer it helpfully.\n"
                f"If the user is stating a broad region like 'Meghalaya' or just saying hello, greet them and ask them to specify their exact town, district, or highway (e.g. Shillong, Laitlyngkot, Sohra, Tura, Nongpoh, NH-40) or tap '📍 Use My GPS Location' so you can provide live geotechnical safety telemetry.\n"
                f"Keep your response concise, compassionate, and direct."
            )
            response_text = await query_external_llm_api(prompt, ai_key)
            if response_text:
                return {
                    "location": None,
                    "zone_code": None,
                    "risk_level": None,
                    "factor_of_safety": None,
                    "insar_creep": None,
                    "pore_water_pressure_kpa": None,
                    "rainfall_24h_mm": None,
                    "rainfall_48h_mm": None,
                    "rainfall_72h_mm": None,
                    "shelter": None,
                    "hospital": None,
                    "road": None,
                    "road_status": None,
                    "diversion": None,
                    "response": response_text,
                    "language": lang
                }

        out_of_coverage = {
            "en": (
                f'I could not detect a specific monitored hazard zone from "{location or query}". '
                "This system covers landslide-prone zones in Meghalaya & North-East India, including: "
                "Shillong Peak Ridge, Laitlyngkot (SH-5), Sohra/Cherrapunji, Mawsynram, Jowai, Nongpoh, Tura, and the NH-40/NH-6 Highway Corridor.\n\n"
                "Please tap '📍 Use My GPS Location' or choose a location from the buttons below. "
                "For emergencies outside this region, contact the National Disaster Helpline: 1078 (NDRF) or 112."
            ),
            "hi": (
                f'"{location or query}" हमारे निगरानी क्षेत्र में नहीं है। '
                "यह प्रणाली मेघालय और पूर्वोत्तर भारत के भूस्खलन-प्रवण क्षेत्रों को कवर करती है: "
                "शिलांग पीक रिज, लैटलिंगकोट (SH-5), सोहरा/चेरापूंजी, मौसिनराम, जोवाई, नोंगपोह, तुरा, और NH-40/NH-6 राजमार्ग।\n\n"
                "कृपया '📍 Use My GPS Location' पर क्लिक करें या नीचे दिए गए बटन में से चुनें। हेल्पलाइन: 1078 (NDRF) या 112।"
            ),
            "kha": (
                f'"{location or query}" kam don ha ka jaka ba ngi peit bniah. '
                "Kane ka system ka kynthup ia ki jaka ba jur ka jingtwa khyndew ha Meghalaya: "
                "Shillong Peak Ridge, Laitlyngkot (SH-5), Sohra, Mawsynram, Jowai, Nongpoh, Tura, bad NH-40 / NH-6.\n\n"
                "Sngewbha click '📍 Use My GPS Location' lane jied na ki button harum. Helpline: 1078 (NDRF) lane 112."
            ),
            "grt": (
                f'"{location or query}" angni nisanani biyapo dongja. '
                "Ia system Meghalaya aro North-East-ni a·a be·ani songrangko sandia: "
                "Shillong, Laitlyngkot, Sohra, Mawsynram, Jowai, Nongpoh, Tura, aro NH-40.\n\n"
                "GPS ba Quick Location buttonko click ka·bo. Helpline: 1078 (NDRF) ba 112."
            ),
            "as": (
                f'"{location or query}" আমাৰ নিৰীক্ষণ অঞ্চলৰ ভিতৰত নাই। '
                "এই প্ৰণালীয়ে মেঘালয় আৰু উত্তৰ-পূৱ ভাৰতৰ ভূমিস্খলন-প্ৰৱণ অঞ্চলসমূহ সামৰি লয়: "
                "শ্বিলং পিক ৰিজ, লাইতলিংকট, চোহৰা, মৌচিনৰাম, জোৱাই, নংপো, তুৰা, আৰু NH-40/NH-6 ঘাইপথ।\n\n"
                "অনুগ্ৰহ কৰি '📍 Use My GPS Location' বা তলৰ স্থান বুটাম বাছক। হেল্পলাইন: 1078 (NDRF) বা 112।"
            )
        }
        return {
            "location": None,
            "zone_code": None,
            "risk_level": None,
            "factor_of_safety": None,
            "insar_creep": None,
            "pore_water_pressure_kpa": None,
            "rainfall_24h_mm": None,
            "shelter": None,
            "hospital": None,
            "road": None,
            "road_status": None,
            "diversion": None,
            "response": out_of_coverage.get(lang, out_of_coverage["en"]),
            "language": lang
        }
    
    loc_data = LOCATIONS_DB.get(loc_key, LOCATIONS_DB["laitlyngkot"])
    
    # 3. Dynamic Geotechnical & Meteorological Telemetry Calculation
    telemetry = await compute_live_geotechnical_telemetry(
        loc_data=loc_data,
        custom_lat=lat,
        custom_lon=lon
    )
    
    # 4. Check if external AI API Key is configured
    ai_key = settings.AI_MODEL_API_KEY or os.environ.get("AI_MODEL_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    response_text = None
    if ai_key:
        script_guidance = {
            "en": "English (Direct, urgent emergency safety guidance)",
            "hi": "Hindi in Devanagari script (स्पष्ट, प्रामाणिक आपदा प्रबंधन हिन्दी भाषा)",
            "as": "Assamese in Assamese script (প্ৰাকৃতিক আৰু স্পষ্ট অসমীয়া ভাষা)",
            "kha": "Khasi language in standard Roman/Latin script (Ka Ktien Khasi in Roman script as standardly written in Meghalaya, e.g., 'Khublei! Ka jaka Laitlyngkot ka don ha ka jingma ba khraw... Leit mardor sha ka jaka rieh...'). Do NOT use Bengali or Devanagari script.",
            "grt": "Garo language in standard Roman/Latin script with raka (A·chik in Roman script as standardly written in Garo Hills, e.g., 'Salam! Laitlyngkot songo a·a be·ani dal·begipa kenani gnang... Ta·rake shelterona re·angbo...'). Do NOT use Bengali or Devanagari script."
        }
        target_script = script_guidance.get(lang, "English")

        prompt = (
            f"You are the NER-LEWS Emergency AI Safety Officer for Meghalaya and North-East India.\n"
            f"MISSION: Guide citizens, families, and travelers in danger with compassionate, direct, and life-saving instructions adhering strictly to Emergency Protocols.\n\n"
            f"EMERGENCY DISASTER PROTOCOLS:\n"
            f"- If Factor of Safety (FS) is <= 1.10 (High or Severe Risk): Issue an IMMEDIATE, urgent high-risk warning, name the nearest designated evacuation shelter ({loc_data['shelter']}), highlight the emergency medical hub ({loc_data['hospital']}), and state the road blockage ({loc_data['road']}: {loc_data['road_status']}) with the detour route ({loc_data.get('diversion', 'Follow police signage')}).\n"
            f"- If Factor of Safety (FS) is 1.11 to 1.35 (Moderate Risk): Issue precautionary safety advice regarding saturated cut slopes and drainage.\n"
            f"- If Factor of Safety (FS) > 1.35 (Low Risk): Reassure the citizen while recommending general monsoon precautions.\n\n"
            f"LIVE SATELLITE & GEOTECHNICAL TELEMETRY:\n"
            f"- Location: {loc_data['canonical_name']} (GPS: {telemetry['lat']}, {telemetry['lon']})\n"
            f"- Geotechnical Factor of Safety (FS): {telemetry['fs']} ({telemetry['risk_level']} Risk, Failure Mode: {telemetry['failure_mode']})\n"
            f"- Dynamic Pore Water Pressure (u): {telemetry['pore_water_pressure_kpa']} kPa\n"
            f"- Live Rainfall Accumulation: 24h = {telemetry['rainfall_24h_mm']} mm | 48h = {telemetry['rainfall_48h_mm']} mm | 72h = {telemetry['rainfall_72h_mm']} mm | Current Rain = {telemetry['rainfall_1h_mm']} mm/h\n"
            f"- Soil Moisture Saturation: {int(telemetry['soil_saturation_pct'] * 100)}%\n"
            f"- Satellite InSAR Ground Creep: {loc_data['insar_creep']}\n"
            f"- Highway Corridor: {loc_data['road']} ({loc_data['road_status']})\n"
            f"- Emergency Traffic Detour: {loc_data.get('diversion', 'Follow local signs')}\n"
            f"- Safe Community Evacuation Shelter: {loc_data['shelter']}\n"
            f"- Medical Care Centre / CHC: {loc_data['hospital']}\n\n"
            f"Citizen Query: \"{query}\"\n"
            f"Target Language: {target_script}\n\n"
            f"Formatting Rules:\n"
            f"1. Explain the danger in compassionate, direct human words for ordinary villagers and travelers.\n"
            f"2. Explicitly cite the Factor of Safety ({telemetry['fs']}) and 24h rainfall ({telemetry['rainfall_24h_mm']} mm).\n"
            f"3. Provide the exact evacuation shelter, hospital, and alternate detour route.\n"
            f"4. Output strictly in {target_script}."
        )
        response_text = await query_external_llm_api(prompt, ai_key)

    # 5. Fallback to built-in structured multi-lingual safety engine
    if not response_text:
        response_text = build_structured_safety_advisory(
            lang=lang,
            loc_data=loc_data,
            telemetry=telemetry
        )
        
    return {
        "location": loc_data["canonical_name"],
        "zone_code": loc_data["zone_code"],
        "risk_level": telemetry["risk_level"],
        "factor_of_safety": telemetry["fs"],
        "insar_creep": loc_data["insar_creep"],
        "pore_water_pressure_kpa": telemetry["pore_water_pressure_kpa"],
        "rainfall_24h_mm": telemetry["rainfall_24h_mm"],
        "rainfall_48h_mm": telemetry["rainfall_48h_mm"],
        "rainfall_72h_mm": telemetry["rainfall_72h_mm"],
        "shelter": loc_data["shelter"],
        "hospital": loc_data["hospital"],
        "road": loc_data["road"],
        "road_status": loc_data["road_status"],
        "diversion": loc_data.get("diversion", "Follow local traffic signs"),
        "response": response_text,
        "language": lang
    }
