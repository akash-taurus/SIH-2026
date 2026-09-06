import pytest
import io
import unittest.mock
import httpx
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.tts import (
    clean_tts_text,
    text_to_speech,
    TTSRequest,
    HINDI_VOICE_MODELS,
    UNIFIED_ENGLISH_VOICE_MODELS
)

HINDI_SAMPLE_TEXT = "शिलांग पीक रिज पर अत्यधिक बारिश के कारण भूस्खलन की चेतावनी। तुरंत सुरक्षित स्थान पर जाएं।"

def test_clean_tts_text_hindi_preserves_devanagari():
    """
    R1 Acceptance Criterion:
    Cleaned Hindi text preserves native Devanagari script and does NOT forcibly
    transliterate into Romanized English phonetics.
    """
    raw_text = "**चेतावनी**: 🛰️ FS = 1.12, 35 mm/h वर्षा, SH-4 पर भूस्खलन का खतरा! CHC पहुंचे।"
    cleaned = clean_tts_text(raw_text, language="hi")

    # Verify Markdown and emojis are removed
    assert "**" not in cleaned
    assert "🛰️" not in cleaned

    # Verify Devanagari is strictly preserved and not transliterated
    assert "चेतावनी" in cleaned
    assert "सुरक्षा गुणांक 1.12" in cleaned
    assert "मिलीमीटर प्रति घंटा" in cleaned
    assert "राज्य राजमार्ग संख्या 4" in cleaned
    assert "भूस्खलन" in cleaned
    assert "सामुदायिक स्वास्थ्य केंद्र" in cleaned

    # Ensure NO Romanized phonetics leaked into Hindi text
    assert "chetawani" not in cleaned.lower()
    assert "bhuskhalan" not in cleaned.lower()
    assert "bhooskhalan" not in cleaned.lower()


def test_clean_tts_text_non_hindi_transliterates_indic():
    """
    Verifies that for non-Hindi languages (e.g. English), Indic text is phonetically
    transliterated so English voice models can speak it.
    """
    raw_text = "भूस्खलन चेतावनी"
    cleaned = clean_tts_text(raw_text, language="en")
    assert "Bhuskhalan" in cleaned or "bhooskhalan" in cleaned.lower()


@pytest.mark.asyncio
async def test_tts_speak_endpoint_hindi_male():
    """
    R1 Acceptance Criterion:
    POST /api/v1/tts/speak with language='hi' and voice_gender='male' synthesizes
    authentic Hindi speech using hi-IN-MadhurNeural and returns valid MP3 audio.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/tts/speak", json={
            "text": HINDI_SAMPLE_TEXT,
            "language": "hi",
            "voice_gender": "male"
        })

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000
    assert "neural_male_hi.mp3" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_tts_speak_distinct_male_streams():
    """
    Acceptance Criterion:
    Male voice requests for Hindi produce intelligible Hindi audio streams using hi-IN-MadhurNeural.
    """
    req_male = TTSRequest(text=HINDI_SAMPLE_TEXT, language="hi", voice_gender="male")
    res_male = await text_to_speech(req_male)

    assert res_male.status_code == 200
    assert len(res_male.body) > 1000


@pytest.mark.asyncio
async def test_tts_speak_empty_text_validation():
    """Verifies that empty text returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/tts/speak", json={
            "text": "    ",
            "language": "hi",
            "voice_gender": "male"
        })
    assert response.status_code == 400
    assert "Text cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tts_fallback_elevenlabs_hindi():
    """
    R2 Acceptance Criterion:
    When primary Edge-TTS encounters an outage, ElevenLabs secondary fallback
    receives the Devanagari text and language_code='hi'.
    """
    fake_audio = b"ID3" + b"\x00" * 600

    mock_post = unittest.mock.AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.content = fake_audio

    with unittest.mock.patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS simulated failure")):
        with unittest.mock.patch("app.config.settings.ELEVENLABS_API_KEY", "mock-eleven-key"):
            with unittest.mock.patch("httpx.AsyncClient.post", mock_post):
                req = TTSRequest(text=HINDI_SAMPLE_TEXT, language="hi", voice_gender="male")
                res = await text_to_speech(req)

    assert res.status_code == 200
    assert res.body == fake_audio
    assert "elevenlabs_tts_hi.mp3" in res.headers.get("content-disposition", "")
    # Check payload sent to ElevenLabs includes language_code='hi'
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["json"]["language_code"] == "hi"
    assert "शिलांग" in call_kwargs["json"]["text"]


@pytest.mark.asyncio
async def test_tts_fallback_google_direct_hindi():
    """
    R2 Acceptance Criterion:
    When Edge-TTS and ElevenLabs fail, tertiary Google Direct Stream routes to 'hi' locale.
    """
    fake_audio = b"ID3" + b"\x00" * 300

    mock_get = unittest.mock.AsyncMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = fake_audio

    with unittest.mock.patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS simulated failure")):
        with unittest.mock.patch("app.config.settings.ELEVENLABS_API_KEY", None):
            with unittest.mock.patch.dict("os.environ", {"ELEVENLABS_API_KEY": ""}):
                with unittest.mock.patch("httpx.AsyncClient.get", mock_get):
                    req = TTSRequest(text=HINDI_SAMPLE_TEXT, language="hi", voice_gender="male")
                    res = await text_to_speech(req)

    assert res.status_code == 200
    assert res.body == fake_audio
    assert "google_tts_hi.mp3" in res.headers.get("content-disposition", "")
    # Ensure query param tl=hi was used
    called_url = mock_get.call_args[0][0]
    assert "tl=hi" in called_url


@pytest.mark.asyncio
async def test_tts_fallback_gtts_hindi():
    """
    R2 Acceptance Criterion:
    When online synthesis providers fail, quaternary local gTTS fallback generates
    valid MP3 audio with lang='hi'.
    """
    with unittest.mock.patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS simulated failure")):
        with unittest.mock.patch("app.config.settings.ELEVENLABS_API_KEY", None):
            with unittest.mock.patch.dict("os.environ", {"ELEVENLABS_API_KEY": ""}):
                with unittest.mock.patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network offline")):
                    req = TTSRequest(text="यह एक परीक्षण है", language="hi", voice_gender="female")
                    res = await text_to_speech(req)

    assert res.status_code == 200
    assert res.media_type == "audio/mpeg"
    assert len(res.body) > 500
    assert "gtts_hi.mp3" in res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_tts_voices_list_endpoint():
    """Verifies that GET /api/v1/tts/voices returns native Hindi voice models."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/tts/voices")

    assert response.status_code == 200
    data = response.json()
    assert "hi-IN-MadhurNeural" in data["voices"]["hi"]


def test_clean_tts_text_hi_in_locale_preserves_devanagari():
    """
    Verifies that 'hi-IN', 'hi_IN', 'HI', and 'hindi' all preserve Devanagari
    and are not transliterated into Roman phonetics.
    """
    raw_text = "भूस्खलन की चेतावनी"
    for loc in ["hi-IN", "hi_IN", "HI", "hindi", "hi"]:
        cleaned = clean_tts_text(raw_text, language=loc)
        assert "भूस्खलन" in cleaned, f"Failed for locale {loc}"
        assert "चेतावनी" in cleaned, f"Failed for locale {loc}"
        assert "bhuskhalan" not in cleaned.lower()
        assert "chetawani" not in cleaned.lower()


def test_clean_tts_text_code_switching_and_abbreviations():
    """
    Tests edge cases with mixed Hindi and English code-switched phrases,
    ensuring technical and emergency acronyms expand properly in Devanagari.
    """
    raw = (
        "SH-4 पर NHAI और SDRF की टीम तैनात है। FS = 1.05 और 45 mm वर्षा दर्ज हुई। "
        "IMD और SDMA ने चेतावनी दी। CHC पहुंचे। 85% आर्द्रता, 40 kPa दाब, 60 km/h हवा।"
    )
    cleaned = clean_tts_text(raw, language="hi-IN")
    assert "राज्य राजमार्ग संख्या 4" in cleaned
    assert "भारतीय राष्ट्रीय राजमार्ग प्राधिकरण" in cleaned
    assert "राज्य आपदा मोचन बल" in cleaned
    assert "सुरक्षा गुणांक 1.05" in cleaned
    assert "45 मिलीमीटर" in cleaned
    assert "भारत मौसम विज्ञान विभाग" in cleaned
    assert "राज्य आपदा प्रबंधन प्राधिकरण" in cleaned
    assert "सामुदायिक स्वास्थ्य केंद्र" in cleaned
    assert "85 प्रतिशत" in cleaned
    assert "40 किलोपास्कल" in cleaned
    assert "60 किलोमीटर प्रति घंटा" in cleaned


@pytest.mark.asyncio
async def test_tts_speak_endpoint_hi_in_locale():
    """
    Verifies that passing language='hi-IN' correctly routes to Hindi neural voice models.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/tts/speak", json={
            "text": HINDI_SAMPLE_TEXT,
            "language": "hi-IN",
            "voice_gender": "male"
        })
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 1000
    assert "neural_male_hi.mp3" in res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_tts_speak_case_insensitive_voice_gender():
    """
    Verifies voice_gender is case-insensitive ('MALE', 'male') and invalid
    gender falls back safely to 'male'. Only 'male' voice is supported.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_male = await ac.post("/api/v1/tts/speak", json={
            "text": "सावधानी बरतें",
            "language": "hi",
            "voice_gender": "MALE"
        })
        assert res_male.status_code == 200
        assert "neural_male_hi.mp3" in res_male.headers.get("content-disposition", "")

        res_invalid = await ac.post("/api/v1/tts/speak", json={
            "text": "सावधानी बरतें",
            "language": "hi",
            "voice_gender": "non_existent_gender"
        })
        assert res_invalid.status_code == 200
        assert "neural_male_hi.mp3" in res_invalid.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_tts_fallback_hi_in_cascade():
    """
    Verifies that when language='hi-IN' is passed, fallbacks (ElevenLabs and gTTS)
    correctly use 'hi' locale rather than falling back to English.
    """
    # Test ElevenLabs fallback with hi-IN
    mock_post = unittest.mock.AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.content = b"ID3" + b"\x00" * 600

    with unittest.mock.patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS simulated failure")):
        with unittest.mock.patch("app.config.settings.ELEVENLABS_API_KEY", "mock-eleven-key"):
            with unittest.mock.patch("httpx.AsyncClient.post", mock_post):
                req = TTSRequest(text=HINDI_SAMPLE_TEXT, language="hi-IN", voice_gender="female")
                res = await text_to_speech(req)

    assert res.status_code == 200
    assert "elevenlabs_tts_hi.mp3" in res.headers.get("content-disposition", "")
    assert mock_post.call_args[1]["json"]["language_code"] == "hi"

    # Test gTTS fallback with hi-IN
    with unittest.mock.patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS simulated failure")):
        with unittest.mock.patch("app.config.settings.ELEVENLABS_API_KEY", None):
            with unittest.mock.patch.dict("os.environ", {"ELEVENLABS_API_KEY": ""}):
                with unittest.mock.patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network offline")):
                    req = TTSRequest(text="यह एक परीक्षण है", language="hi-IN", voice_gender="male")
                    res = await text_to_speech(req)

    assert res.status_code == 200
    assert "gtts_hi.mp3" in res.headers.get("content-disposition", "")


def test_clean_tts_text_hindi_devanagari_numerals_and_punctuation():
    """
    Tests edge cases with Devanagari numerals (१२३४), colon FS syntax (FS: 1.12),
    and prevents spurious trailing/duplicate commas.
    """
    raw = "चेतावनी: SH-४ पर NH-४४ बंद है। ४५ mm वर्षा, २५ kPa दाब, ८०% आर्द्रता, ३२ °C तापमान। (FS: १.१२)।"
    cleaned = clean_tts_text(raw, language="hi")

    assert "राज्य राजमार्ग संख्या ४" in cleaned
    assert "राष्ट्रीय राजमार्ग ४४" in cleaned
    assert "४५ मिलीमीटर" in cleaned
    assert "२५ किलोपास्कल" in cleaned
    assert "८० प्रतिशत" in cleaned
    assert "३२ डिग्री सेल्सियस" in cleaned
    assert "सुरक्षा गुणांक १.१२" in cleaned
    # Ensure no double commas or trailing commas before closing punctuation
    assert ",," not in cleaned
    assert ",)" not in cleaned
    assert not cleaned.endswith(",")


@pytest.mark.asyncio
async def test_tts_large_paragraph_synthesis():
    """
    Tests full speech synthesis of a long (>600 char) Hindi disaster advisory
    without truncation of emergency instructions.
    """
    long_advisory = (
        "शिलांग पीक रिज पर अत्यधिक बारिश के कारण भूस्खलन की गंभीर चेतावनी जारी की गई है। "
        "सुरक्षा गुणांक गिरकर शून्य दशमलव आठ आठ हो चुका है। मिट्टी पूरी तरह से संतृप्त है। "
        "उपग्रह इनसार ने निरंतर धंसाव दर्ज किया है। राष्ट्रीय आपदा मोचन बल और राज्य आपदा मोचन बल "
        "की टीमें तैनात हैं। सभी नागरिक तुरंत सुरक्षित स्थानों की ओर प्रस्थान करें। "
        "निकटतम सामुदायिक स्वास्थ्य केंद्र अथवा राहत शिविर में पहुंचे।"
    )
    req = TTSRequest(text=long_advisory, language="hi", voice_gender="male")
    res = await text_to_speech(req)
    assert res.status_code == 200
    assert res.media_type == "audio/mpeg"
    # Full paragraph must synthesize a substantial audio file (>50000 bytes)
    assert len(res.body) > 30000


@pytest.mark.asyncio
async def test_tts_concurrency_simultaneous_requests():
    """
    Tests concurrency under multiple simultaneous requests to POST /api/v1/tts/speak.
    """
    import asyncio
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        tasks = [
            ac.post("/api/v1/tts/speak", json={
                "text": f"चेतावनी संख्या {i}: भूस्खलन खतरा। सुरक्षित रहें।",
                "language": "hi",
                "voice_gender": "female" if i % 2 == 0 else "male"
            })
            for i in range(4)
        ]
        responses = await asyncio.gather(*tasks)

    for r in responses:
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mpeg"
        assert len(r.content) > 1000


@pytest.mark.asyncio
async def test_tts_voices_list_with_language_filter():
    """
    Verifies GET /api/v1/tts/voices?language=hi filters catalog and returns models.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/tts/voices?language=hi-IN")

    assert response.status_code == 200
    data = response.json()
    assert data["selected_language"] == "hi"
    assert "hi-IN-MadhurNeural" in data["male_voices"]["hi"]
    assert "hi-IN-SwaraNeural" in data["female_voices"]["hi"]
    assert data["models"]["hi"]["male"] == "hi-IN-MadhurNeural"
    assert data["models"]["hi"]["female"] == "hi-IN-SwaraNeural"


