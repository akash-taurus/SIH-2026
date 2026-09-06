/**
 * speechUtils.js: High-Clarity Multilingual Voice Synthesis Engine
 * Provides natural pronunciation across English, Hindi, Assamese, Khasi, and Garo.
 * Features:
 * - Dual-layer synthesis: Direct neural server-side TTS stream with automatic Web Speech fallback
 * - Dialect phonetic adaptation & symbol/acronym expansion
 * - Sentence segmentation for zero browser timeouts
 * - Centralized audio lifecycle & cancellation management
 */

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

let cachedVoices = [];
let voiceLoadAttempted = false;
let currentAudioInstance = null;
let currentAbortController = null;

function initVoiceLoading() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  if (voiceLoadAttempted) return;
  voiceLoadAttempted = true;

  const loadVoices = () => {
    cachedVoices = window.speechSynthesis.getVoices() || [];
  };

  loadVoices();

  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }

  setTimeout(() => {
    if (cachedVoices.length === 0 && window.speechSynthesis) loadVoices();
  }, 800);
}

export function isSpeechSupported() {
  return typeof window !== 'undefined' && (!!window.speechSynthesis || typeof Audio !== 'undefined');
}

export function isVoiceLoadingComplete() {
  initVoiceLoading();
  return cachedVoices.length > 0;
}

export function getAvailableLanguages() {
  initVoiceLoading();
  const langs = new Set(cachedVoices.map(v => v.lang));
  return Array.from(langs);
}

export function getAllVoices() {
  initVoiceLoading();
  return cachedVoices;
}

function getVoiceDisplayName(voice) {
  if (!voice) return 'Unknown';
  return `${voice.name} (${voice.lang})${voice.localService ? ' [Local]' : '[Remote]'}`;
}

export function debugVoiceInfo() {
  initVoiceLoading();
  const info = {
    speechSupported: isSpeechSupported(),
    voiceCount: cachedVoices.length,
    voices: cachedVoices.map(v => getVoiceDisplayName(v)),
    recommendedVoices: {}
  };

  ['en', 'hi', 'as', 'kha', 'grt'].forEach(lang => {
    const voice = getBestVoiceForLanguage(lang);
    info.recommendedVoices[lang] = voice ? getVoiceDisplayName(voice) : null;
  });

  return info;
}

export function normalizeSpeechLanguage(lang) {
  if (!lang || typeof lang !== 'string') return 'en';
  const cleaned = lang.trim().toLowerCase().replace('_', '-');
  const base = cleaned.split('-')[0];
  if (['hi', 'en', 'as', 'kha', 'grt'].includes(base)) {
    return base;
  }
  if (cleaned === 'hi-in' || cleaned === 'hindi') {
    return 'hi';
  }
  return base || 'en';
}

export function cleanTextForSpeech(rawText, language = 'en') {
  if (!rawText || typeof rawText !== 'string') return '';
  const langKey = normalizeSpeechLanguage(language);

  let text = rawText
    .replace(/[*#_~`]/g, '')
    .replace(/[•●▪■]/g, ', ')
    .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
    .replace(/\s+/g, ' ')
    .trim();

  // Language-specific phonetic expansions
  if (langKey === 'hi') {
    const D = '[0-9\\u0966-\\u096F]';
    text = text
      .replace(/\bFS\s*[:=]\s*/gi, 'सुरक्षा गुणक ')
      .replace(/\bFS\b/gi, 'सुरक्षा गुणक')
      .replace(new RegExp(`(${D}+)\\s*mm\\/h(?:our)?`, 'gi'), '$1 मिलीमीटर प्रति घंटा')
      .replace(/mm\/h(?:our)?/gi, ' मिलीमीटर प्रति घंटा ')
      .replace(new RegExp(`(${D}+)\\s*mm\\/yr`, 'gi'), '$1 मिलीमीटर प्रति वर्ष')
      .replace(/mm\/yr/gi, ' मिलीमीटर प्रति वर्ष ')
      .replace(new RegExp(`(${D}+)\\s*mm\\b`, 'gi'), '$1 मिलीमीटर')
      .replace(new RegExp(`(${D}+)\\s*km\\/h`, 'gi'), '$1 किलोमीटर प्रति घंटा')
      .replace(new RegExp(`(${D}+)\\s*km\\b`, 'gi'), '$1 किलोमीटर')
      .replace(new RegExp(`(${D}+)\\s*kPa\\b`, 'gi'), '$1 किलोपास्कल')
      .replace(new RegExp(`(${D}+)\\s*%`, 'g'), '$1 प्रतिशत')
      .replace(new RegExp(`(${D}+)\\s*°C`, 'gi'), '$1 डिग्री सेल्सियस')
      .replace(new RegExp(`(?:\\b)SH-(${D}+)`, 'gi'), 'स्टेट हाईवे $1')
      .replace(new RegExp(`(?:\\b)NH-(${D}+)`, 'gi'), 'राष्ट्रीय राजमार्ग $1')
      .replace(/\bNHAI\b/gi, 'भारतीय राष्ट्रीय राजमार्ग प्राधिकरण')
      .replace(/\bPWD\b/gi, 'लोक निर्माण विभाग')
      .replace(/\bInSAR\b/gi, 'इनसार उपग्रह रडार')
      .replace(/\bCHC\b/gi, 'सामुदायिक स्वास्थ्य केंद्र')
      .replace(/\bSDMA\b/gi, 'एसडीएमए')
      .replace(/\bSDRF\b/gi, 'एसडीआरएफ')
      .replace(/\bNDRF\b/gi, 'एनडीआरएफ')
      .replace(/\bIMD\b/gi, 'भारत मौसम विज्ञान विभाग')
      .replace(/\bMSL\b/gi, 'समुद्र तल से ऊंचाई')
      .replace(/\bSMS\b/gi, 'एसएमएस');
  } else if (langKey === 'as' || langKey === 'kha' || langKey === 'grt') {
    const D_AS = '[0-9\\u09E6-\\u09EF]';
    text = text
      .replace(/\bFS\s*[:=]\s*/gi, 'সুৰক্ষা গুণক ')
      .replace(/\bFS\b/gi, 'সুৰক্ষা গুণক')
      .replace(/mm\/h(?:our)?/gi, ' মিলিমিটাৰ প্ৰতি ঘণ্টা ')
      .replace(/mm\/yr/gi, ' মিলিমিটাৰ প্ৰতি বছৰ ')
      .replace(new RegExp(`(${D_AS}+)\\s*mm\\b`, 'gi'), '$1 মিলিমিটাৰ')
      .replace(new RegExp(`(?:\\b)SH-(${D_AS}+)`, 'gi'), 'ষ্টেট হাইৱে $1')
      .replace(new RegExp(`(?:\\b)NH-(${D_AS}+)`, 'gi'), 'ৰাষ্ট্ৰীয় ঘাইপথ $1')
      .replace(/\bCHC\b/gi, 'চিকিৎসালয়')
      .replace(/\bSDMA\b/gi, 'এছডিএমএ')
      .replace(/\bNDRF\b/gi, 'এনডিআৰএফ');
  } else {
    text = text
      .replace(/\bFS\s*[:=]\s*/gi, ' Factor of Safety ')
      .replace(/\bMSL\b/g, 'above sea level')
      .replace(/mm\/h(?:our)?/gi, ' millimeters per hour ')
      .replace(/mm\/yr/gi, ' millimeters per year ')
      .replace(/\bSH-(\d+)\b/gi, 'State Highway $1')
      .replace(/\bNH-(\d+)\b/gi, 'National Highway $1')
      .replace(/\bInSAR\b/gi, 'InSAR satellite radar')
      .replace(/\bCHC\b/gi, 'Community Health Centre')
      .replace(/\bSDMA\b/gi, 'State Disaster Management Authority')
      .replace(/\bNDRF\b/gi, 'National Disaster Response Force');
  }

  // Sanitize punctuation spacing and duplicate commas
  text = text.replace(/\s*,\s*,+/g, ', ');

  return text.replace(/\s+/g, ' ').trim();
}

export function getBestVoiceForLanguage(langKey = 'en', gender = null) {
  initVoiceLoading();
  const currentVoices = (typeof window !== 'undefined' && window.speechSynthesis && window.speechSynthesis.getVoices)
    ? window.speechSynthesis.getVoices()
    : [];
  const voices = (currentVoices && currentVoices.length > 0) ? currentVoices : cachedVoices;
  if (voices.length === 0) return null;

  const key = normalizeSpeechLanguage(langKey);
  const targetGender = (gender || '').toLowerCase();

  if (key === 'en') {
    return (
      voices.find(v => v.lang === 'en-IN') ||
      voices.find(v => /india|neerja|prabhat|heera|zira|ravi/i.test(v.name)) ||
      voices.find(v => v.lang === 'en-GB') ||
      voices.find(v => v.lang.startsWith('en')) ||
      voices.find(v => v.default) ||
      voices[0]
    );
  }

  if (key === 'hi') {
    const hiVoices = voices.filter(v => v.lang === 'hi-IN' || v.lang.startsWith('hi') || /hindi/i.test(v.name));
    // Remove English/Narrator voices that shouldn't be used for Hindi
    const actualHiVoices = hiVoices.filter(v => !(v.lang && v.lang.startsWith('en')));
    if (actualHiVoices.length > 0) {
      if (targetGender === 'female') {
        const femaleVoice = actualHiVoices.find(v => /female|swara|kalpana/i.test(v.name));
        if (femaleVoice) return femaleVoice;
      } else if (targetGender === 'male') {
        const maleVoice = actualHiVoices.find(v => /male|madhur|hemant/i.test(v.name));
        if (maleVoice) return maleVoice;
      }
      return actualHiVoices[0];
    }
    return null;
  }

  if (key === 'as') {
    return (
      voices.find(v => v.lang === 'as-IN' || v.lang === 'as') ||
      voices.find(v => /assamese/i.test(v.name)) ||
      voices.find(v => v.lang === 'bn-IN' || v.lang === 'bn-BD') ||
      voices.find(v => /bengali|bangla|tanishaa|bashkar/i.test(v.name)) ||
      voices.find(v => v.lang === 'hi-IN') ||
      voices.find(v => v.lang.startsWith('en')) ||
      voices[0]
    );
  }

  if (key === 'kha') {
    return (
      voices.find(v => v.lang === 'kha-IN' || v.lang === 'kha') ||
      voices.find(v => /khasi/i.test(v.name)) ||
      voices.find(v => v.lang === 'bn-IN' || v.lang === 'bn-BD') ||
      voices.find(v => /bengali|bangla|tanishaa|bashkar/i.test(v.name)) ||
      voices.find(v => v.lang === 'hi-IN') ||
      voices.find(v => v.lang.startsWith('en')) ||
      voices[0]
    );
  }

  if (key === 'grt') {
    return (
      voices.find(v => v.lang === 'grt-IN' || v.lang === 'grt') ||
      voices.find(v => /garo/i.test(v.name)) ||
      voices.find(v => v.lang === 'bn-IN' || v.lang === 'bn-BD') ||
      voices.find(v => /bengali|bangla|tanishaa|bashkar/i.test(v.name)) ||
      voices.find(v => v.lang === 'hi-IN') ||
      voices.find(v => v.lang.startsWith('en')) ||
      voices[0]
    );
  }

  return voices[0];
}

function getVoiceFallbackLangAttr(language) {
  const norm = normalizeSpeechLanguage(language);
  const langMap = {
    'en': 'en-IN',
    'hi': 'hi-IN',
    'as': 'bn-IN',
    'kha': 'bn-IN',
    'grt': 'bn-IN'
  };
  return langMap[norm] || 'en-IN';
}

export function romanizeIndicText(text) {
  if (!text || typeof text !== 'string') return '';

  let str = text
    .replace(/লাইতলিংকট/g, 'Laitlyngkot')
    .replace(/লুম শিল্লং/g, 'Loom Shillong')
    .replace(/শিল্লং/g, 'Shillong')
    .replace(/শ্বিলং/g, 'Shillong')
    .replace(/চোহৰা/g, 'Sohra')
    .replace(/চেৰাপুঞ্জী/g, 'Cherrapunji')
    .replace(/মৌসিনৰাম/g, 'Mawsynram')
    .replace(/জোৱাই/g, 'Jowai')
    .replace(/নোংপোহ/g, 'Nongpoh')
    .replace(/নংপো/g, 'Nongpoh')
    .replace(/তুৰা/g, 'Tura')
    .replace(/উমিয়াম/g, 'Umiam')
    .replace(/খুব্লেই/g, 'Khublei')
    .replace(/চালাম/g, 'Salam')
    .replace(/নমস্কাৰ/g, 'Namaskar')
    .replace(/नमस्ते/g, 'Namaste')
    .replace(/কা জাকা/g, 'Ka jaka')
    .replace(/কা দন/g, 'ka don')
    .replace(/মিন্তা/g, 'minta')
    .replace(/হা কা/g, 'ha ka')
    .replace(/জিংমা/g, 'jingma')
    .replace(/খ্ৰাৱ/g, 'khraw')
    .replace(/খিন্দেউ/g, 'khindew')
    .replace(/স্লাপ/g, 'slap')
    .replace(/জুৰ/g, 'joor')
    .replace(/সুৰক/g, 'surak')
    .replace(/হস্পিতাল/g, 'hospital')
    .replace(/হাস্পাতাল/g, 'hospital')
    .replace(/আশ্ৰয়/g, 'aashray')
    .replace(/চেল্টাৰ/g, 'shelter')
    .replace(/বিকল্প/g, 'alternate')
    .replace(/লैटलिंगकोट/g, 'Laitlyngkot')
    .replace(/शिलांग पीक रिज/g, 'Shillong Peak Ridge')
    .replace(/शिलांग/g, 'Shillong')
    .replace(/सोहरा/g, 'Sohra')
    .replace(/चेरापूंजी/g, 'Cherrapunji')
    .replace(/मौसिनराम/g, 'Mawsynram')
    .replace(/जोवाई/g, 'Jowai')
    .replace(/नोंगपोह/g, 'Nongpoh')
    .replace(/तुरा/g, 'Tura')
    .replace(/उमियम/g, 'Umiam')
    .replace(/भूस्खलन/g, 'bhooskhalan')
    .replace(/चेतावनी/g, 'chetawani')
    .replace(/आपातकालीन/g, 'aapaatkaleen')
    .replace(/राहत शिविर/g, 'raahat shivir')
    .replace(/आश्रय/g, 'aashray')
    .replace(/अस्पताल/g, 'hospital')
    .replace(/सुरक्षा गुणक/g, 'Factor of Safety')
    .replace(/सुৰক্ষা গুণক/g, 'Factor of Safety');

  const charMap = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    '्': '', 'ं': 'n', 'ँ': 'n', 'ः': 'h', '़': '',
    'অ': 'o', 'আ': 'aa', 'ই': 'i', 'ঈ': 'ee', 'উ': 'u', 'ঊ': 'oo', 'এ': 'e', 'ঐ': 'oi', 'ও': 'o', 'ঔ': 'ou',
    'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'ঙ': 'ng',
    'চ': 'ch', 'ছ': 'chh', 'জ': 'j', 'ঝ': 'jh', 'ঞ': 'ny',
    'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh', 'ণ': 'n',
    'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n',
    'প': 'p', 'ফ': 'ph', 'ব': 'b', 'ভ': 'bh', 'ম': 'm',
    'য': 'y', 'ৰ': 'r', 'ল': 'l', 'ৱ': 'w', 'শ': 'sh', 'ষ': 'sh', 'স': 's', 'হ': 'h',
    'া': 'aa', 'ি': 'i', 'ী': 'ee', 'ু': 'u', 'ূ': 'oo', 'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou',
    '্': '', 'ং': 'ng', 'ঁ': 'n', 'ঃ': 'h', 'ৎ': 't',
    '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9', '০': '0',
    '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9', '०': '0'
  };

  let result = '';
  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    result += charMap[ch] !== undefined ? charMap[ch] : ch;
  }

  return result.replace(/\s+/g, ' ').trim();
}

/**
 * High-Level Multi-Lingual Speech Dispatcher
 * Streams studio-grade Microsoft Azure Indian Neural HD voices (Prabhat/Madhur/Neerja/Swara)
 * from the server with automatic fallback to browser Web Speech API with smart phonetic romanization.
 */
export async function speakDisasterAudio({
  text,
  language = 'en',
  voice_gender = 'male',
  onStart = () => {},
  onEnd = () => {},
  onError = () => {}
}) {
  stopDisasterAudio();

  const normLang = normalizeSpeechLanguage(language);
  const spokenText = cleanTextForSpeech(text, normLang);
  if (!spokenText) {
    onEnd();
    return true;
  }

  // In live browser environment, stream HD Neural Voice from backend
  if (typeof fetch !== 'undefined' && process.env.NODE_ENV !== 'test') {
    try {
      const success = await speakWithServerTTS({
        text: spokenText,
        language: normLang,
        voice_gender,
        onStart,
        onEnd
      });
      if (success) return true;
    } catch (err) {
      // Fallback to browser TTS below
    }
  }

  return speakWithBrowserTTS({
    text: spokenText,
    language: normLang,
    voice_gender,
    onStart,
    onEnd,
    onError
  });
}

/**
 * Browser Web Speech Synthesis engine with smart phonetic Romanization for English-only devices
 */
export function speakWithBrowserTTS({
  text,
  language = 'en',
  voice_gender = 'male',
  onStart = () => {},
  onEnd = () => {},
  onError = () => {}
}) {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    onError(new Error('SpeechSynthesis not supported in this browser'));
    return false;
  }

  window.speechSynthesis.cancel();
  initVoiceLoading();

  const normLang = normalizeSpeechLanguage(language);
  const voice = getBestVoiceForLanguage(normLang, voice_gender);
  const isEnglishOnlyVoice = !voice || voice.lang.startsWith('en');
  const hasIndicChars = /[\u0900-\u09FF]/.test(text);

  // If the browser only has English voice available, transliterate Indic text into Romanized phonetics
  // ONLY for non-Hindi languages. For Hindi, preserve authentic Devanagari script for native synthesis.
  let finalSpokenText = text;
  if (normLang !== 'hi' && isEnglishOnlyVoice && hasIndicChars) {
    finalSpokenText = romanizeIndicText(text);
  }

  const utterance = new SpeechSynthesisUtterance(finalSpokenText);

  if (voice) {
    utterance.voice = voice;
    utterance.lang = (normLang === 'hi') ? (voice.lang && voice.lang.startsWith('hi') ? voice.lang : 'hi-IN') : (isEnglishOnlyVoice ? 'en-IN' : voice.lang);
  } else {
    utterance.lang = getVoiceFallbackLangAttr(normLang);
  }

  // Natural pacing for emergency instructions
  utterance.rate = 0.88;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  return new Promise((resolve) => {
    utterance.onstart = () => {
      onStart();
    };
    utterance.onend = () => {
      onEnd();
      resolve(true);
    };
    utterance.onerror = (e) => {
      if (e.error !== 'canceled' && e.error !== 'interrupted') {
        console.warn('[Speech] Browser TTS error:', e.error);
        onError(e);
      }
      resolve(false);
    };

    window.speechSynthesis.speak(utterance);
  });
}

/**
 * Server-Side Neural TTS Stream Player
 */
export async function speakWithServerTTS({
  text,
  language = 'en',
  voice_gender = 'male',
  onStart = () => {},
  onEnd = () => {},
  onError = () => {}
}) {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  currentAbortController = controller;

  try {
    const fetchOptions = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, voice_gender })
    };
    if (controller) {
      fetchOptions.signal = controller.signal;
    }

    const response = await fetch(`${API_BASE_URL}/tts/speak`, fetchOptions);

    if (!response.ok) throw new Error(`Server TTS status: ${response.status}`);

    const audioBlob = await response.blob();
    if (controller?.signal?.aborted) return false;
    if (!audioBlob || audioBlob.size < 100) throw new Error('Invalid audio stream received');

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    if (controller?.signal?.aborted) {
      URL.revokeObjectURL(audioUrl);
      return false;
    }

    currentAudioInstance = audio;

    onStart();

    return new Promise((resolve) => {
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        if (currentAudioInstance === audio) currentAudioInstance = null;
        onEnd();
        resolve(true);
      };
      audio.onerror = (e) => {
        URL.revokeObjectURL(audioUrl);
        if (currentAudioInstance === audio) currentAudioInstance = null;
        onError(e);
        resolve(false);
      };
      audio.play().catch(err => {
        URL.revokeObjectURL(audioUrl);
        if (currentAudioInstance === audio) currentAudioInstance = null;
        onError(err);
        resolve(false);
      });
    });
  } catch (err) {
    if (controller?.signal?.aborted || err?.name === 'AbortError') {
      return false;
    }
    return false;
  } finally {
    if (currentAbortController === controller) {
      currentAbortController = null;
    }
  }
}

/**
 * Stops all currently active speech playback (both HTML5 audio, in-flight streaming requests, and browser speech synthesis).
 */
export function stopDisasterAudio() {
  if (currentAbortController) {
    try {
      currentAbortController.abort();
    } catch (e) {
      console.warn('[Speech] Error aborting fetch:', e);
    }
    currentAbortController = null;
  }
  if (currentAudioInstance) {
    try {
      currentAudioInstance.pause();
      currentAudioInstance.currentTime = 0;
    } catch (e) {
      console.warn('[Speech] Error pausing audio instance:', e);
    }
    currentAudioInstance = null;
  }
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

export async function testVoiceForLanguage(language = 'en') {
  const normLang = normalizeSpeechLanguage(language);
  const testTexts = {
    'en': 'This is a live test of the disaster and safety emergency warning voice system.',
    'hi': 'यह आपदा एवं सुरक्षा पूर्व चेतावनी प्रणाली का सजीव ध्वनि परीक्षण है।',
    'as': 'এইটো দুৰ্যোগ আৰু সুৰক্ষা আগতীয়া সতৰ্কবাণী প্ৰণালীৰ লাইভ অডিঅ পৰীক্ষণ।',
    'kha': 'কা জিংপাহ য়া কা জিংমা কা খিন্দেউ আৰ কা জিংয়াদা হা কা স্লাপ বা জুৰ।',
    'grt': 'আ·ব্ৰি বে·আনি আৰো নালজকানি কেনানি সম্বলিত অডিঅ নিসাহা।'
  };

  const text = testTexts[normLang] || testTexts['en'];
  return speakDisasterAudio({
    text,
    language: normLang,
    onStart: () => console.log(`[Voice Test] Started for ${normLang}`),
    onEnd: () => console.log(`[Voice Test] Finished for ${normLang}`),
    onError: (e) => console.warn(`[Voice Test] Error for ${normLang}:`, e)
  });
}

