import {
  cleanTextForSpeech,
  getBestVoiceForLanguage,
  speakDisasterAudio,
  speakWithServerTTS,
  stopDisasterAudio,
  testVoiceForLanguage
} from '../utils/speechUtils';

describe('speechUtils - Multilingual Speech Synthesis Engine', () => {
  beforeEach(() => {
    global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => ({
      text,
      lang: 'en',
      rate: 1,
      pitch: 1,
      onstart: null,
      onend: null,
      onerror: null
    }));

    window.speechSynthesis = {
      speak: jest.fn((utt) => {
        if (utt && typeof utt.onstart === 'function') utt.onstart();
      }),
      cancel: jest.fn(),
      getVoices: jest.fn(() => [
        { name: 'Google हिन्दी', lang: 'hi-IN' },
        { name: 'Google বাংলা', lang: 'bn-IN' },
        { name: 'Microsoft Neerja Online (Natural) - English (India)', lang: 'en-IN' }
      ])
    };
  });

  test('cleanTextForSpeech strips markdown and emojis while expanding abbreviations', () => {
    const raw = '**CRITICAL RED ALERT**: 🛰️ Satellite InSAR reports FS = 1.14 with 25 mm/h rain at SH-5 • Immediate evacuation!';
    const cleaned = cleanTextForSpeech(raw);

    expect(cleaned).not.toContain('**');
    expect(cleaned).not.toContain('🛰️');
    expect(cleaned).not.toContain('•');
    expect(cleaned).toContain('Factor of Safety 1.14');
    expect(cleaned).toContain('millimeters per hour');
    expect(cleaned).toContain('State Highway 5');
  });

  test('getBestVoiceForLanguage matches authentic regional voice engines', () => {
    const hiVoice = getBestVoiceForLanguage('hi');
    expect(hiVoice).toBeDefined();
    expect(hiVoice.lang).toBe('hi-IN');

    const asVoice = getBestVoiceForLanguage('as');
    expect(asVoice).toBeDefined();
    expect(asVoice.lang).toBe('bn-IN');

    const khaVoice = getBestVoiceForLanguage('kha');
    expect(khaVoice).toBeDefined();
    expect(khaVoice.lang).toBe('bn-IN');

    const enVoice = getBestVoiceForLanguage('en');
    expect(enVoice).toBeDefined();
    expect(enVoice.lang).toBe('en-IN');
  });

  test('speakDisasterAudio cancels existing audio and triggers speak', () => {
    const onStart = jest.fn();
    speakDisasterAudio({
      text: 'Laitlyngkot evacuation alert',
      language: 'en',
      onStart
    });

    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
    expect(window.speechSynthesis.speak).toHaveBeenCalled();
    expect(onStart).toHaveBeenCalled();
  });

  test('stopDisasterAudio calls speechSynthesis.cancel', () => {
    stopDisasterAudio();
    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
  });

  test('cleanTextForSpeech expands Hindi domain terms and preserves Devanagari', () => {
    const raw = 'चेतावनी: FS = 1.08, बारिश 40 mm/h, SH-2 पर खतरा!';
    const cleaned = cleanTextForSpeech(raw, 'hi');

    expect(cleaned).toContain('सुरक्षा गुणक 1.08');
    expect(cleaned).toContain('मिलीमीटर प्रति घंटा');
    expect(cleaned).toContain('स्टेट हाईवे 2');
    expect(cleaned).toContain('चेतावनी');
  });

  test('getBestVoiceForLanguage selects gender-specific Hindi voices when available', () => {
    window.speechSynthesis.getVoices = jest.fn(() => [
      { name: 'Microsoft Madhur Online (Natural) - Hindi (India)', lang: 'hi-IN' },
      { name: 'Microsoft Swara Online (Natural) - Hindi (India)', lang: 'hi-IN' },
      { name: 'Microsoft Neerja Online (Natural) - English (India)', lang: 'en-IN' }
    ]);

    const maleVoice = getBestVoiceForLanguage('hi', 'male');
    expect(maleVoice).toBeDefined();
    expect(maleVoice.name).toContain('Madhur');
    expect(maleVoice.lang).toBe('hi-IN');

    const femaleVoice = getBestVoiceForLanguage('hi', 'female');
    expect(femaleVoice).toBeDefined();
    expect(femaleVoice.name).toContain('Swara');
    expect(femaleVoice.lang).toBe('hi-IN');
  });

  test('speakDisasterAudio with Hindi routes to hi-IN and preserves native Devanagari script', () => {
    const hindiText = 'भूस्खलन की चेतावनी। तुरंत सुरक्षित स्थान पर पहुंचे।';
    let passedUtterance = null;
    global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => {
      passedUtterance = { text, lang: 'en' };
      return passedUtterance;
    });

    speakDisasterAudio({
      text: hindiText,
      language: 'hi',
      voice_gender: 'female'
    });

    expect(passedUtterance).not.toBeNull();
    expect(passedUtterance.lang).toBe('hi-IN');
    // Native Devanagari script must be preserved and NOT transliterated to Roman text
    expect(passedUtterance.text).toContain('भूस्खलन');
    expect(passedUtterance.text).toContain('चेतावनी');
    expect(passedUtterance.text).not.toContain('bhooskhalan');
    expect(passedUtterance.text).not.toContain('chetawani');
  });

  test('fallback Web Speech API preserves Devanagari for Hindi even on English-only systems, no Narrator fallback', () => {
    // Simulate system with only Windows Narrator English voices
    window.speechSynthesis.getVoices = jest.fn(() => [
      { name: 'Microsoft David Desktop - English (United States)', lang: 'en-US' },
      { name: 'Microsoft Zira Desktop - English (United States)', lang: 'en-US' }
    ]);

    // getBestVoiceForLanguage should return null instead of falling back to the Narrator English voice
    const hiVoice = getBestVoiceForLanguage('hi');
    expect(hiVoice).toBeNull();

    let captured = null;
    global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => {
      captured = { text, lang: '' };
      return captured;
    });

    speakDisasterAudio({
      text: 'भूस्खलन की चेतावनी।',
      language: 'hi'
    });

    expect(captured).not.toBeNull();
    expect(captured.lang).toBe('hi-IN');
    // Must preserve Devanagari and NOT force Roman transliteration
    expect(captured.text).toContain('भूस्खलन');
    expect(captured.text).not.toContain('bhooskhalan');
  });

  test('cleanTextForSpeech handles hi-IN locale and expands technical acronyms to Devanagari', () => {
    const raw = 'चेतावनी: FS = 1.05, 45 mm वर्षा, 25 kPa दाब, 90% आर्द्रता, SH-4 पर NHAI और SDRF सतर्क। InSAR डेटा प्राप्त।';
    const cleaned = cleanTextForSpeech(raw, 'hi-IN');

    expect(cleaned).toContain('सुरक्षा गुणक 1.05');
    expect(cleaned).toContain('45 मिलीमीटर');
    expect(cleaned).toContain('25 किलोपास्कल');
    expect(cleaned).toContain('90 प्रतिशत');
    expect(cleaned).toContain('स्टेट हाईवे 4');
    expect(cleaned).toContain('भारतीय राष्ट्रीय राजमार्ग प्राधिकरण');
    expect(cleaned).toContain('एसडीआरएफ');
    expect(cleaned).toContain('इनसार उपग्रह रडार');
    expect(cleaned).toContain('चेतावनी');
  });

  test('getBestVoiceForLanguage resolves hi-IN locale with male and female voice selection', () => {
    window.speechSynthesis.getVoices = jest.fn(() => [
      { name: 'Microsoft David Desktop - English (United States)', lang: 'en-US' },
      { name: 'Microsoft Madhur Online (Natural) - Hindi (India)', lang: 'hi-IN' },
      { name: 'Microsoft Swara Online (Natural) - Hindi (India)', lang: 'hi-IN' }
    ]);

    const femaleVoice = getBestVoiceForLanguage('hi-IN', 'female');
    expect(femaleVoice).toBeDefined();
    expect(femaleVoice.name).toContain('Swara');
    expect(femaleVoice.lang).toBe('hi-IN');

    const maleVoice = getBestVoiceForLanguage('hi-IN', 'male');
    expect(maleVoice).toBeDefined();
    expect(maleVoice.name).toContain('Madhur');
    expect(maleVoice.lang).toBe('hi-IN');
  });

  test('speakDisasterAudio with hi-IN routes to hi-IN and preserves native Devanagari script', () => {
    let captured = null;
    global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => {
      captured = { text, lang: '' };
      return captured;
    });

    speakDisasterAudio({
      text: 'भूस्खलन की चेतावनी।',
      language: 'hi-IN'
    });

    expect(captured).not.toBeNull();
    expect(captured.lang).toBe('hi-IN');
    expect(captured.text).toContain('भूस्खलन');
    expect(captured.text).not.toContain('bhooskhalan');
  });

  test('testVoiceForLanguage with hi-IN plays authentic Hindi test text', () => {
    let captured = null;
    global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => {
      captured = { text, lang: '' };
      return captured;
    });

    testVoiceForLanguage('hi-IN');

    expect(captured).not.toBeNull();
    expect(captured.lang).toBe('hi-IN');
    expect(captured.text).toContain('आपदा');
    expect(captured.text).not.toContain('live test');
  });

  test('cleanTextForSpeech expands Devanagari numerals, Celsius units, and colon FS syntax', () => {
    const raw = 'चेतावनी: SH-४ पर NH-४४ बंद है। ४५ mm वर्षा, २५ kPa दाब, ८०% आर्द्रता, ३२ °C तापमान। (FS: १.१२)।';
    const cleaned = cleanTextForSpeech(raw, 'hi');

    expect(cleaned).toContain('स्टेट हाईवे ४');
    expect(cleaned).toContain('राष्ट्रीय राजमार्ग ४४');
    expect(cleaned).toContain('४५ मिलीमीटर');
    expect(cleaned).toContain('२५ किलोपास्कल');
    expect(cleaned).toContain('८० प्रतिशत');
    expect(cleaned).toContain('३२ डिग्री सेल्सियस');
    expect(cleaned).toContain('सुरक्षा गुणक १.१२');
    expect(cleaned).not.toContain(',,');
  });

  test('stopDisasterAudio aborts in-flight server streaming fetch in speakWithServerTTS', async () => {
    let capturedSignal = null;
    global.fetch = jest.fn().mockImplementation((url, options) => {
      capturedSignal = options?.signal;
      return new Promise((resolve) => {
        if (capturedSignal) {
          capturedSignal.addEventListener('abort', () => {
            const err = new Error('The user aborted a request.');
            err.name = 'AbortError';
            resolve({ ok: false, status: 0 });
          });
        }
      });
    });

    const onStart = jest.fn();
    const promise = speakWithServerTTS({
      text: 'शिलांग में भूस्खलन',
      language: 'hi',
      onStart
    });

    // Cancel while request is in-flight
    stopDisasterAudio();

    const result = await promise;
    expect(result).toBe(false);
    expect(capturedSignal).not.toBeNull();
    expect(capturedSignal.aborted).toBe(true);
    expect(onStart).not.toHaveBeenCalled();
  });
});
