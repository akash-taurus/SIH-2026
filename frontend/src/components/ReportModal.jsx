import React, { useState } from 'react';
import { translations } from '../utils/translations';

/**
 * ReportModal: Citizen Field Hazard Reporting Component
 * Features HTML5 GPS acquisition, photo attachment preview, severity tagging, and multilingual text.
 */
export default function ReportModal({ isOpen, onClose, onSubmit, language = 'en' }) {
  const t = translations[language] || translations.en;

  const [note, setNote] = useState('');
  const [severity, setSeverity] = useState('high');
  const [coords, setCoords] = useState({ lat: null, lon: null, accuracy: null });
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser.');
      return;
    }
    setLocating(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        });
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        setLocationError(err.message || 'Unable to acquire real GPS location.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
  };

  const handleRemovePhoto = () => {
    setPhoto(null);
    setPhotoPreview(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        note,
        severity,
        latitude: coords.lat,
        longitude: coords.lon,
        photo
      });
      // Reset form state
      setNote('');
      setSeverity('high');
      setCoords({ lat: null, lon: null, accuracy: null });
      setPhoto(null);
      setPhotoPreview(null);
      onClose();
    } catch (err) {
      console.error('Failed to submit report:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4"
    >
      <div className="bg-white border-2 border-black rounded-none max-w-lg w-full p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b-2 border-black mb-4">
          <div>
            <h3 className="text-lg font-bold text-black uppercase tracking-tight">
              {t.report_modal_title}
            </h3>
            <p className="text-xs text-gray-600 font-mono">
              Live ground telemetry & verified observation portal
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-black hover:bg-gray-100 border border-black px-2.5 py-1 text-sm font-bold leading-none cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-sm font-sans">
          {/* Notes / Description */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-black mb-1">
              {t.report_desc_label} <span className="text-black font-normal">*</span>
            </label>
            <textarea
              className="w-full border border-black p-2.5 text-xs text-black placeholder:text-gray-400 focus:outline-hidden focus:ring-1 focus:ring-black"
              rows={3}
              placeholder={t.report_note_placeholder}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              required
            />
          </div>

          {/* Observed Severity Tier */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-black mb-1">
              Observed Hazard Severity
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full border border-black p-2 text-xs text-black bg-white font-medium focus:outline-hidden"
            >
              <option value="severe">🔴 Severe (Active Mudslide / Road Blocked / Structural Damage)</option>
              <option value="high">🟠 High (Tension Cracks / Rapid Soil Seepage)</option>
              <option value="moderate">🟡 Moderate (Pebble Detachment / Minor Erosion)</option>
              <option value="low">⚪ Low (Slope Surface Runoff)</option>
            </select>
          </div>

          {/* GPS Coordinates Section */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-black mb-1">
              {t.gps_label}
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={
                  coords.lat
                    ? `${coords.lat.toFixed(5)}° N, ${coords.lon.toFixed(5)}° E (±${Math.round(coords.accuracy || 0)}m accuracy)`
                    : "Real-time coordinates pending capture..."
                }
                className="flex-1 border border-gray-300 bg-gray-50 p-2 text-xs font-mono text-gray-800"
              />
              <button
                type="button"
                onClick={handleGetLocation}
                disabled={locating}
                className="bg-black text-white hover:bg-gray-800 text-xs font-bold px-3 py-2 border border-black transition-colors cursor-pointer disabled:opacity-50"
              >
                {locating ? t.acquiring_gps : t.get_gps}
              </button>
            </div>
            {locationError && (
              <p className="text-[11px] text-gray-600 mt-1 font-mono">⚠️ {locationError}</p>
            )}
          </div>

          {/* Photo Evidence Attachment */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-black mb-1">
              {t.photo_label}
            </label>
            {photoPreview ? (
              <div className="relative border border-black p-2 flex items-center gap-3 bg-gray-50">
                <img
                  src={photoPreview}
                  alt="Hazard evidence preview"
                  className="w-14 h-14 object-cover border border-gray-400"
                />
                <div className="flex-1 min-w-0 text-xs">
                  <p className="font-semibold text-black truncate">{photo.name}</p>
                  <p className="text-gray-500 font-mono">{(photo.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  type="button"
                  onClick={handleRemovePhoto}
                  className="text-xs text-black border border-black px-2 py-1 hover:bg-gray-200 cursor-pointer"
                >
                  Remove
                </button>
              </div>
            ) : (
              <label className="border border-dashed border-black hover:bg-gray-50 flex items-center justify-center p-3 text-xs cursor-pointer text-center">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  className="hidden"
                />
                <span className="font-semibold text-black">+ {t.take_photo}</span>
              </label>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="border border-black text-black hover:bg-gray-100 px-4 py-2 text-xs font-bold uppercase tracking-wider cursor-pointer"
            >
              {t.cancel}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-black text-white hover:bg-gray-800 px-5 py-2 text-xs font-bold uppercase tracking-wider border border-black cursor-pointer disabled:opacity-50"
            >
              {submitting ? t.submitting : t.submit}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
