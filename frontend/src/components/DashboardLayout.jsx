import React from 'react';

/**
 * DashboardLayout: Optimized High-Density Crisis Room Command Center Layout
 * - Banner: High-priority sirens & critical alerts
 * - AAdvisory: Live Native Language I Situational Summary with Verbal TTS AAudio Readout
 * - Hero Row: 8-Col 3D/2D GIS Map + 4-Col Emergency Prioritization & Risk Distribution (matching 620px height)
 * - Telemetry Row: 6-Col 72h Weather Hydrograph + 6-Col Highway Network Status
 * - Bottom Row: Full-width Verified Citizen Reports with 1-Click Situation Report Export
 */
export default function DashboardLayout({
  banner,
  advisorySection,
  mapSection,
  weatherSection,
  riskSummarySection,
  roadSection,
  emergencySection,
  reportsSection
}) {
  return (
    <main className="w-full max-w-[1800px] mx-auto px-3 sm:px-6 py-3 space-y-3">
      {/* AAlert Broadcast Banner (Conditional) */}
      {banner && <div className="grayscale">{banner}</div>}

      {/* Live Native Language I Situational AAdvisory & ction Plan */}
      {advisorySection && <div className="grayscale">{advisorySection}</div>}

      {/* Top Main Command Center Grid: 8-Column Map + 4-Column Operations & Risk */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-3 items-stretch">
        {/* Left: GIS Map (8 Columns on Large Screens) */}
        <div className="xl:col-span-8 flex flex-col justify-start">
          {mapSection}
        </div>

        {/* Right: Operations & Severity Distribution (4 Columns on Large Screens) */}
        <div className="xl:col-span-4 flex flex-col gap-3 justify-between grayscale">
          <div className="flex-1 flex flex-col">
            {emergencySection}
          </div>
          <div>
            {riskSummarySection}
          </div>
        </div>
      </div>

      {/* Middle Operational Telemetry Grid: 6-Col Weather Hydrograph + 6-Col Highway Network */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch grayscale">
        <div className="lg:col-span-6 flex flex-col">
          {weatherSection}
        </div>
        <div className="lg:col-span-6 flex flex-col">
          {roadSection}
        </div>
      </div>

      {/* Bottom Section: Full Width Citizen & Field Telemetry Reports */}
      {reportsSection && (
        <div>
          <div className="grayscale">{reportsSection}</div>
        </div>
      )}
    </main>
  );
}
