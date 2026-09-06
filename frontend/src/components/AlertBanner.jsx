import React, { useState } from 'react';
import { translations } from '../utils/translations';

/**
 * AlertBanner: 4-Tier High-Contrast Emergency Broadcast Banner
 */
export default function AlertBanner({
  severity = 'severe',
  title = null,
  message = null,
  language = 'en',
  onDismiss = null
}) {
  const [dismissed, setDismissed] = useState(false);
  const t = translations[language] || translations.en;

  if (dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    if (onDismiss) onDismiss();
  };

  const getVariantStyles = () => {
    switch (severity?.toLowerCase()) {
      case 'severe':
        return {
          container: 'bg-black text-white border-2 border-black',
          badge: 'bg-white text-black font-black',
          badgeText: 'CRITICAL SEVERE HAZARD',
          closeBtn: 'text-white hover:bg-gray-800 border border-white'
        };
      case 'high':
        return {
          container: 'bg-white text-black border-2 border-black',
          badge: 'bg-black text-white font-bold',
          badgeText: 'HIGH RISK AADVISORY',
          closeBtn: 'text-black hover:bg-gray-100 border border-black'
        };
      case 'moderate':
        return {
          container: 'bg-gray-100 text-gray-800 border border-gray-400',
          badge: 'bg-gray-700 text-white font-bold',
          badgeText: 'MODERATE WATCH',
          closeBtn: 'text-gray-800 hover:bg-gray-200 border border-gray-400'
        };
      default:
        return {
          container: 'bg-white text-gray-600 border border-gray-300',
          badge: 'bg-gray-200 text-gray-800 font-normal',
          badgeText: 'LOW AADVISORY',
          closeBtn: 'text-gray-600 hover:bg-gray-100 border border-gray-300'
        };
    }
  };

  const styles = getVariantStyles();
  const displayTitle = title || t.active_critical_alert || "CRITICAL HAZARD WARNING";
  const displayMessage = message || "Extreme rainfall detected in Shillong East Ridge & Mawsynram Canyon. Caine physical safety threshold breached. Soil saturation > 90%. " + (t.alert_action || "Follow Disaster Management Protocols Immediately.");

  return (
    <div className={`w-full p-3.5 mb-4 flex items-start justify-between gap-3 ${styles.container}`}>
      <div className="flex items-start gap-3">
        <span className={`text-[10px] uppercase font-mono px-2 py-0.5 tracking-wider inline-block mt-0.5 ${styles.badge}`}>
          {styles.badgeText}
        </span>
        <div>
          <h4 className="font-bold text-sm leading-tight tracking-tight uppercase">
            {displayTitle}
          </h4>
          <p className="text-xs mt-0.5 font-sans leading-relaxed opacity-95">
            {displayMessage}
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dismiss alert"
        className={`px-2 py-0.5 text-xs font-mono font-bold leading-none cursor-pointer ${styles.closeBtn}`}
      >
        
      </button>
    </div>
  );
}
