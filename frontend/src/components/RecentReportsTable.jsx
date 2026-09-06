import React, { useState, useEffect, useMemo } from 'react';
import { translations } from '../utils/translations';
import { getQueuedReports } from '../services/offlineQueue';

/**
 * RecentReportsTable: Displays verified citizen & field officer hazard reports.
 * Features:
 * - Real-time merging of server-verified reports with local offline queued reports
 * - Distinct visual Queued (Offline) amber badges
 * - Pending sync count banner and manual sync action
 * - Reactive re-rendering on 'offline-queue-changed' event
 * - 1-Click Incident Situation Report Export (.CSV)
 */
export default function RecentReportsTable({
  reports = [],
  language = 'en',
  onOpenReportModal,
  onSyncNow,
  isSyncing = false
}) {
  const t = translations[language] || translations.en;

  const [queuedReports, setQueuedReports] = useState(() => {
    try {
      return getQueuedReports() || [];
    } catch (e) {
      return [];
    }
  });

  // Reactive listener for offline queue mutations
  useEffect(() => {
    const updateQueue = () => {
      try {
        setQueuedReports(getQueuedReports() || []);
      } catch (e) {
        setQueuedReports([]);
      }
    };

    window.addEventListener('offline-queue-changed', updateQueue);
    window.addEventListener('storage', updateQueue);
    window.addEventListener('online', updateQueue);

    updateQueue();

    return () => {
      window.removeEventListener('offline-queue-changed', updateQueue);
      window.removeEventListener('storage', updateQueue);
      window.removeEventListener('online', updateQueue);
    };
  }, []);

  // Merge queued offline reports with confirmed server reports
  const mergedReports = useMemo(() => {
    const queuedIds = new Set(queuedReports.map((q) => q.id));
    const filteredServerReports = reports.filter((r) => !queuedIds.has(r.id));
    return [...queuedReports, ...filteredServerReports];
  }, [reports, queuedReports]);

  const queuedIdSet = useMemo(() => {
    return new Set(queuedReports.map((q) => q.id));
  }, [queuedReports]);

  const getSeverityBadge = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'severe':
        return <span className="bg-black text-white px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">Severe</span>;
      case 'high':
        return <span className="border border-black text-black font-bold px-2 py-0.5 text-[10px] uppercase tracking-wider">High</span>;
      case 'moderate':
        return <span className="bg-gray-200 text-gray-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider">Moderate</span>;
      default:
        return <span className="border border-gray-300 text-gray-600 px-2 py-0.5 text-[10px] font-normal uppercase tracking-wider">Low</span>;
    }
  };

  /**
   * Generates and downloads an Incident Situation Report as CSV
   */
  const handleExportCSV = () => {
    if (!mergedReports || mergedReports.length === 0) return;

    const headers = ["Report ID", "Status", "Timestamp", "Reporter", "Location", "Latitude", "Longitude", "Severity", "Observations"];
    const rows = mergedReports.map((r) => [
      `"${r.id || ''}"`,
      `"${queuedIdSet.has(r.id) || r.status === 'queued_offline' ? 'Queued Offline' : 'Telemetry Synced'}"`,
      `"${r.timestamp || ''}"`,
      `"${r.reporter || ''}"`,
      `"${r.location_name || ''}"`,
      r.latitude || '',
      r.longitude || '',
      `"${r.severity || ''}"`,
      `"${(r.note || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `NER_LEWS_Situation_Report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white border-2 border-black p-4">
      {/* Header bar with count, action button, and Situation Report export */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b-2 border-black mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-bold text-black tracking-tight">{t.recent_reports_title}</h3>
          <span className="bg-gray-100 text-black border border-black text-xs px-2 py-0.5 font-mono font-bold">
            {mergedReports.length}
          </span>
          {queuedReports.length > 0 ? (
            <span
              data-testid="queued-summary-pill"
              className="bg-amber-100 border border-amber-500 text-amber-900 text-[10px] font-mono font-bold px-2 py-0.5"
            >
               {queuedReports.length} Queued
            </span>
          ) : (
            <span className="hidden sm:inline-block bg-gray-50 border border-gray-300 text-gray-600 text-[10px] font-mono px-2 py-0.5">
              ● Telemetry Synced
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Situation Report Export Button */}
          <button
            type="button"
            onClick={handleExportCSV}
            disabled={mergedReports.length === 0}
            className="bg-white text-black hover:bg-gray-100 text-xs font-bold px-3 py-1.5 border border-black uppercase tracking-wider font-mono cursor-pointer disabled:opacity-50"
            title="Download Incident Summary for Disaster Authorities"
          >
             Export SitRep (.CSV)
          </button>

          {onOpenReportModal && (
            <button
              type="button"
              onClick={onOpenReportModal}
              className="bg-black text-white hover:bg-gray-800 text-xs font-bold px-3.5 py-1.5 border border-black uppercase tracking-wider cursor-pointer"
            >
              + {t.report_button}
            </button>
          )}
        </div>
      </div>

      {/* Pending Sync Count Banner */}
      {queuedReports.length > 0 && (
        <div
          data-testid="pending-sync-banner"
          className="mb-3 p-3 bg-amber-50 border-2 border-amber-500 flex flex-wrap items-center justify-between gap-2 animate-in fade-in"
        >
          <div className="flex items-center gap-2.5">
            <span className="text-amber-700 font-bold text-base"></span>
            <div>
              <p className="text-xs font-bold text-amber-900">
                {queuedReports.length} {queuedReports.length === 1 ? 'Report' : 'Reports'} Pending Sync
              </p>
              <p className="text-[11px] text-amber-700 font-mono">
                Stored in persistent local storage. Will automatically upload when network reconnects.
              </p>
            </div>
          </div>
          {onSyncNow && (
            <button
              type="button"
              onClick={onSyncNow}
              disabled={isSyncing}
              className="bg-amber-500 hover:bg-amber-600 text-black border border-black text-xs font-bold px-3 py-1.5 uppercase tracking-wider font-mono cursor-pointer disabled:opacity-50"
            >
              {isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
          )}
        </div>
      )}

      {/* Reports Table / List */}
      {mergedReports.length === 0 ? (
        <div className="p-8 text-center text-xs text-gray-500 font-mono">
          {t.no_reports}
        </div>
      ) : (
        <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="border-b-2 border-black bg-gray-50 text-[11px] font-bold uppercase tracking-wider text-black">
                <th className="py-2.5 px-3">{t.report_id}</th>
                <th className="py-2.5 px-3">{t.location}</th>
                <th className="py-2.5 px-3">{t.observations}</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">{t.reporter}</th>
                <th className="py-2.5 px-3 text-right">{t.timestamp}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {mergedReports.map((report) => {
                const isQueued = queuedIdSet.has(report.id) || report.status === 'queued_offline';
                return (
                  <tr
                    key={report.id}
                    className={`hover:bg-gray-50 transition-colors ${
                      isQueued ? 'bg-amber-50/40' : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-black whitespace-nowrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span>{report.id}</span>
                        {isQueued && (
                          <span
                            data-testid="queued-badge"
                            className="bg-amber-100 text-amber-900 border border-amber-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                          >
                            Queued (Offline)
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-black">{report.location_name}</div>
                      {report.latitude !== null && report.latitude !== undefined && report.longitude !== null && report.longitude !== undefined && (
                        <div className="text-[10px] text-gray-500 font-mono">
                          {Number(report.latitude).toFixed(4)}°N, {Number(report.longitude).toFixed(4)}°E
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 max-w-md text-gray-800">
                      <p className="line-clamp-2">{report.note}</p>
                      {(report.photo_url || report.photo_base64) && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-black font-semibold mt-1 underline">
                          Attached Photo Evidence (Compressed)
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {getSeverityBadge(report.severity)}
                    </td>
                    <td className="py-2.5 px-3 text-gray-700 whitespace-nowrap">
                      {report.reporter}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-500 whitespace-nowrap">
                      {report.timestamp}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
