import React from 'react';
import { translations } from '../utils/translations';

export default function Navbar({
  language = 'en',
  onLanguageChange,
  isSimulating = false,
  onOpenReportModal,
  onOpenTerminologyModal
}) {
  const t = translations[language] || translations.en;

  const languages = [
    { code: 'en', label: 'English (EN)' },
    { code: 'hi', label: 'हिन्दी (HI)' },
    { code: 'as', label: 'অসমীয়া (AS)' },
    { code: 'kha', label: 'খাসী (Khasi)' },
    { code: 'grt', label: 'গাৰো (A·chik)' }
  ];

  return (
    <header className="bg-black text-white border-b-4 border-black px-3 sm:px-6 py-2.5 sticky top-0 z-40">
      <div className="w-full max-w-[1800px] mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-black tracking-tight uppercase leading-none text-white">
                {t.title || "NER Landslide Early Warning System"}
              </h1>
              <span className="hidden md:inline-block bg-white text-black text-[10px] font-mono font-bold px-1.5 py-0.5 tracking-wider uppercase">
                v1.0-MVP
              </span>
            </div>
            <p className="text-[11px] text-gray-300 font-mono mt-0.5">
              {t.subtitle || "Real-Time Geo-Hazard & Rainfall Monitoring"} • Meghalaya & Assam Sector
            </p>
          </div>
        </div>

        {/* Right: Controls & Status Indicators */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
          {/* Live Sync Status */}
          <div className="hidden lg:flex items-center gap-1.5 bg-gray-900 border border-gray-700 px-2.5 py-1 text-gray-300 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-white inline-block animate-ping"></span>
            <span>{t.system_status || "SYSTEM ACTIVE"}</span>
            <span className="text-gray-500">|</span>
            <span className="text-gray-400">{t.refresh_rate || "Sync: 15m"}</span>
          </div>

          {/* Cloudburst Simulation Flag */}
          {isSimulating && (
            <span className="bg-white text-black font-mono font-black text-[11px] px-2 py-1 uppercase tracking-wider animate-pulse rounded-sm">
              STORM SIMULATION
            </span>
          )}

          {/* Language Selector */}
          <div className="flex items-center gap-1 bg-gray-900 border border-gray-700 p-1">
            <span className="text-[10px] text-gray-400 font-mono px-1">LNG:</span>
            <select
              value={language}
              onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
              className="bg-black text-white text-xs font-bold border-none outline-none cursor-pointer pr-1"
            >
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code} className="bg-black text-white">
                  {lang.label}
                </option>
              ))}
            </select>
          </div>

          {/* Terminology Help Trigger */}
          {onOpenTerminologyModal && (
            <button
              type="button"
              onClick={onOpenTerminologyModal}
              className="bg-transparent hover:bg-gray-800 text-white text-xs font-mono font-bold px-2.5 py-1.5 border border-gray-600 hover:border-white uppercase tracking-wider transition-colors cursor-pointer flex items-center gap-1.5"
              title="Open terminology & science help guide"
            >
              <span></span>
              <span>{language === 'hi' ? 'शब्दावली' : language === 'as' ? 'পৰিভাষা সহায়িকা' : language === 'kha' ? 'জিংবাতাই ক্তিয়েন' : language === 'grt' ? 'Skiani' : 'Terminology'}</span>
            </button>
          )}

          {/* Report Hazard Modal Trigger */}
          {onOpenReportModal && (
            <button
              type="button"
              onClick={onOpenReportModal}
              className="bg-white text-black hover:bg-gray-200 text-xs font-black px-3 py-1.5 border-2 border-white uppercase tracking-wider transition-colors cursor-pointer"
            >
              + {t.report_button || "Report Hazard"}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
