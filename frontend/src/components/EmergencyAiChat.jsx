import React, { useState, useEffect, useRef } from 'react';
import { fetchChatWelcome, sendEmergencyChatMessage } from '../services/api';
import { speakDisasterAudio, stopDisasterAudio } from '../utils/speechUtils';

/**
 * EmergencyAiChat: Compassionate Multilingual Conversational AI Disaster Companion
 * Guides citizens, families, and travelers in simple, direct terms with high-clarity voice readout.
 */
export default function EmergencyAiChat({ language = 'en' }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [suggestedLocations, setSuggestedLocations] = useState([]);
  const [playingMessageIdx, setPlayingMessageIdx] = useState(null);

  const messagesEndRef = useRef(null);

  // Stop audio on unmount or language change
  useEffect(() => {
    return () => stopDisasterAudio();
  }, [language]);

  // Load contextual welcome greetings when language changes
  useEffect(() => {
    let isMounted = true;
    async function loadWelcome() {
      const data = await fetchChatWelcome(language);
      if (isMounted && data) {
        setMessages([
          {
            id: `bot-welcome-${Date.now()}`,
            sender: 'bot',
            text: `${data.greeting}\n\n${data.ask_location}`
          }
        ]);
        setSuggestedLocations(data.suggested_locations || []);
      }
    }
    loadWelcome();
    return () => {
      isMounted = false;
      stopDisasterAudio();
    };
  }, [language]);

  useEffect(() => {
    if (isOpen && typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isTyping]);

  const handleSendMessage = async (queryText = null, locOverride = null, lat = null, lon = null) => {
    const textToSend = (queryText || inputQuery).trim();
    if (!textToSend || isTyping) return;

    // dd user message to thread
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsTyping(true);

    try {
      const response = await sendEmergencyChatMessage(textToSend, locOverride, language, lat, lon);
      const botMsg = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: response.response,
        location: response.location,
        risk_level: response.risk_level,
        factor_of_safety: response.factor_of_safety,
        pore_water_pressure_kpa: response.pore_water_pressure_kpa,
        rainfall_24h_mm: response.rainfall_24h_mm,
        shelter: response.shelter,
        hospital: response.hospital,
        road: response.road,
        road_status: response.road_status,
        diversion: response.diversion
      };
      setMessages((prev) => [...prev, botMsg]);

      // Trigger Web Push Notification if Factor of Safety <= 1.10 or Risk is Severe/High
      if (response.factor_of_safety && response.factor_of_safety <= 1.15) {
        triggerWebNotification(
          ` Landslide Crisis Alert: ${response.location || 'Your Sector'}`,
          `Factor of Safety FS=${response.factor_of_safety}. Shelter at ${response.shelter || 'Relief Camp'}. Highway: ${response.road_status || 'Restricted'}.`
        );
      }
    } catch (err) {
      console.warn('[I Chat] Failed to get response:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: 'bot',
          text: "I am having temporary trouble contacting the satellite radar. If you are in immediate danger, please call Emergency Helpline: 1077 (SDM) or 1078 (NDRF)."
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const triggerWebNotification = (title, body) => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        try {
          new Notification(title, { body, icon: '/favicon.ico' });
        } catch (e) {
          console.warn('[Notification] Trigger failed:', e);
        }
      } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then((permission) => {
          if (permission === 'granted') {
            try {
              new Notification(title, { body, icon: '/favicon.ico' });
            } catch (e) {
              console.warn('[Notification] Request trigger failed:', e);
            }
          }
        });
      }
    }
  };

  const handleUseGpsLocation = () => {
    if (isTyping) return;
    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      setIsTyping(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          handleSendMessage(
            ` Checking live safety at my GPS location (${latitude.toFixed(3)}, ${longitude.toFixed(3)})`,
            null,
            latitude,
            longitude
          );
        },
        (err) => {
          console.warn('[GPS] Geolocation failed:', err.message);
          handleSendMessage("Check real-time landslide safety for my current position");
        },
        { timeout: 6000, enableHighAccuracy: true }
      );
    } else {
      handleSendMessage("Check real-time landslide safety for my current position");
    }
  };

  const handleSpeakText = (text, idx) => {
    if (playingMessageIdx === idx) {
      stopDisasterAudio();
      setPlayingMessageIdx(null);
      return;
    }

    stopDisasterAudio();

    speakDisasterAudio({
      text,
      language,
      voice_gender: 'male',
      onStart: () => setPlayingMessageIdx(idx),
      onEnd: () => setPlayingMessageIdx(null),
      onError: (e) => {
        console.warn('[Speech] Error:', e);
        setPlayingMessageIdx(null);
      }
    });
  };

  const getChatHeaderTitle = () => {
    switch (language) {
      case 'kha': return "U Nongiarap AI (Khasi)";
      case 'grt': return "AI Dakchakgipa (A·chik)";
      case 'hi': return "आपदा सहायक (हिन्दी)";
      case 'as': return "আপদকালীন সহায়ক (অসমীয়া)";
      default: return "Disaster & Safety Assistant";
    }
  };

  const getPlaceholderText = () => {
    switch (language) {
      case 'kha': return "Thoh ia ka jaka ne kyli jingkylli (kum Laitlyngkot)...";
      case 'grt': return "Na·ani songko sebo ba sing·bo (jekai Laitlyngkot)...";
      case 'hi': return "अपना स्थान लिखें या प्रश्न पूछें (जैसे लैटलिंगकोट)...";
      case 'as': return "আপোনাৰ স্থান লিখক বা প্ৰশ্ন সোধক (যেনে লাইতলিংকট)...";
      default: return "Ask a safety question or type your location...";
    }
  };

  const getGpsButtonLabel = () => {
    switch (language) {
      case 'kha': return " Ka Jaka GPS Jong Nga";
      case 'grt': return " Angni GPS Biyap";
      case 'hi': return " मेरा GPS स्थान";
      case 'as': return " মোৰ GPS স্থান";
      default: return " Use My GPS Location";
    }
  };

  return (
    <aside aria-label="Disaster Assistant" className="fixed bottom-4 right-4 z-50 select-none">
      {/* Floating Toggle Button */}
      {!isOpen ? (
        <button
          type="button"
          onClick={() => {
            setIsOpen(true);
            if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
              Notification.requestPermission();
            }
          }}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-xl px-4 py-2.5 rounded-full flex items-center gap-2 text-sm font-medium cursor-pointer transition-transform hover:scale-105"
        >
          <span> {getChatHeaderTitle()}</span>
        </button>
      ) : (
        /* Expanded Chat Window */
        <div className="w-[360px] sm:w-[420px] h-[550px] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col font-sans overflow-hidden animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="bg-blue-600 text-white p-3 flex items-center justify-between border-b border-blue-700 shrink-0">
            <div className="flex items-center gap-2">
              <div>
                <h3 className="font-semibold text-sm tracking-tight flex items-center gap-1.5">
                  <span>{getChatHeaderTitle()}</span>
                </h3>
                <p className="text-xs text-blue-100 opacity-90">24/7 Live Geotechnical & Satellite Guide</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => {
                  stopDisasterAudio();
                  setPlayingMessageIdx(null);
                  setIsOpen(false);
                }}
                className="hover:bg-gray-800 text-white font-bold px-2 py-0.5 text-xs cursor-pointer"
                title="Minimize chat"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Message List */}
          <div className="flex-1 p-3 overflow-y-auto space-y-3 bg-[#F8FAFC]">
            {messages.map((msg, idx) => (
              <div
                key={msg.id || `msg-${idx}`}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`p-3 max-w-[92%] text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-black text-white rounded-tl-lg rounded-tr-lg rounded-bl-lg font-mono'
                      : 'bg-white text-black border border-black rounded-tr-lg rounded-br-lg rounded-bl-lg shadow-xs'
                  }`}
                >
                  <p className="whitespace-pre-line leading-relaxed font-sans">{msg.text}</p>

                  {/* Geotechnical Quick Safety Badges */}
                  {msg.location && (
                    <div className="mt-2.5 pt-2 border-t border-gray-200 text-[11px] font-mono space-y-1.5">
                      <div className="flex items-center justify-between gap-1 flex-wrap">
                        <span className="font-bold text-black"> {msg.location}</span>
                        <span
                          className={`px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-xs ${
                            msg.risk_level === 'Severe'
                              ? 'bg-red-600 text-white'
                              : msg.risk_level === 'High'
                              ? 'bg-orange-500 text-white'
                              : msg.risk_level === 'Moderate'
                              ? 'bg-yellow-500 text-black'
                              : 'bg-green-600 text-white'
                          }`}
                        >
                          {msg.risk_level || 'Monitored'} {msg.factor_of_safety ? `(FS: ${msg.factor_of_safety})` : ''}
                        </span>
                      </div>

                      {/* Live Multi-Window Rainfall & Pore Pressure Badge */}
                      {msg.rainfall_24h_mm !== undefined && msg.rainfall_24h_mm !== null && (
                        <div className="text-[10px] text-gray-700 bg-blue-50/80 p-1 border border-blue-200 rounded-xs flex items-center justify-between">
                          <span>️ <b>24h Rain:</b> {msg.rainfall_24h_mm} mm</span>
                          {msg.pore_water_pressure_kpa !== undefined && (
                            <span> <b>Pore Pressure (u):</b> {msg.pore_water_pressure_kpa} kPa</span>
                          )}
                        </div>
                      )}

                      {/* Evacuation Shelter & Hospital */}
                      {msg.shelter && (
                        <div className="text-gray-900 bg-green-50 p-1 border border-green-300 rounded-xs">
                          <b>️ Safe Shelter:</b> {msg.shelter}
                        </div>
                      )}
                      {msg.hospital && (
                        <div className="text-gray-900 bg-emerald-50 p-1 border border-emerald-200 rounded-xs">
                          <b> Nearest Hospital:</b> {msg.hospital}
                        </div>
                      )}

                      {/* Road Status & Diversion */}
                      {msg.road_status && (
                        <div className="text-gray-900 bg-amber-50 p-1 border border-amber-200 rounded-xs text-[10px]">
                          <b> Highway Status:</b> {msg.road ? `${msg.road} — ` : ''}{msg.road_status}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* High-Clarity Voice Readout Button for Bot Messages (hidden for Khasi/Garo - no native TTS) */}
                {msg.sender === 'bot' && !['kha', 'grt'].includes(language) && (
                  <button
                    type="button"
                    onClick={() => handleSpeakText(msg.text, idx)}
                    className={`mt-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border transition-all flex items-center gap-1.5 cursor-pointer ${
                      playingMessageIdx === idx
                        ? 'bg-red-600 text-white border-red-700 animate-pulse'
                        : 'bg-white hover:bg-gray-100 text-gray-700 border-gray-300'
                    }`}
                    title="Listen to crystal-clear voice alert in local dialect"
                  >
                    {playingMessageIdx === idx ? (
                      <>
                        <span className="w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>
                        <span> Stop Voice</span>
                      </>
                    ) : (
                      <>
                        <span></span>
                        <span>Listen Voice AAudio</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div className="flex items-center gap-2 text-xs text-gray-700 font-mono bg-white p-2 border border-gray-300 w-fit rounded-xs shadow-xs">
                <span className="w-2 h-2 bg-black rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-black rounded-full animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-2 h-2 bg-black rounded-full animate-bounce [animation-delay:0.4s]"></span>
                <span>Calculating live geotechnical physics & satellite telemetry...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Bar: GPS Location + Sector Chips */}
          <div className="p-2 bg-gray-50 border-t border-gray-200 flex flex-wrap items-center gap-1.5 shrink-0">
            {/* GPS Auto-Detect Button */}
            <button
              type="button"
              onClick={handleUseGpsLocation}
              disabled={isTyping}
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-md px-2.5 py-1 text-xs font-medium cursor-pointer transition-colors shadow-sm"
            >
              {getGpsButtonLabel()}
            </button>

            {suggestedLocations.map((loc) => (
              <button
                key={loc.key}
                type="button"
                onClick={() => handleSendMessage(loc.name, loc.key)}
                className="bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 rounded-md px-2 py-1 text-xs font-medium cursor-pointer transition-colors shadow-sm"
              >
                 {loc.name}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3 bg-white flex items-center gap-2 shrink-0 border-t border-gray-100"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder={getPlaceholderText()}
              className="flex-1 bg-gray-100 border border-transparent rounded-full px-4 py-2 text-sm focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isTyping}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-full px-4 py-2 text-sm shadow-sm cursor-pointer transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </aside>
  );
}
