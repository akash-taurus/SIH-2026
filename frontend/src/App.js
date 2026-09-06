import React from 'react';
import { useAppState } from './contexts/AppContext';
import Navbar from './components/Navbar';
import AlertBanner from './components/AlertBanner';
import DashboardLayout from './components/DashboardLayout';
import MapView from './components/MapView';
import WeatherChart from './components/WeatherChart';
import RiskSummaryCard from './components/RiskSummaryCard';
import RoadTable from './components/RoadTable';
import EmergencyPrioritizationCard from './components/EmergencyPrioritizationCard';
import RecentReportsTable from './components/RecentReportsTable';
import ReportModal from './components/ReportModal';
import DisasterAdvisoryCard from './components/DisasterAdvisoryCard';
import EmergencyAiChat from './components/EmergencyAiChat';
import TerminologyModal from './components/TerminologyModal';
import { getSimulationState, toggleCloudburstSimulation } from './services/api';

export default function App() {
  const [isTerminologyModalOpen, setIsTerminologyModalOpen] = React.useState(false);
  const {
    language,
    setLanguage,
    selectedZone,
    setSelectedZone,
    riskZones,
    riskSummary,
    roads,
    settlements,
    weatherData,
    reports,
    isReportModalOpen,
    setIsReportModalOpen,
    submitReport,
    refreshWeather
  } = useAppState();

  const isSimulating = getSimulationState();

  const handleToggleSimulation = (enabled) => {
    toggleCloudburstSimulation(enabled);
    refreshWeather();
  };

  return (
    <div className="min-h-screen bg-[#FFFFFF] text-black font-sans selection:bg-black selection:text-white pb-12">
      {/* Top Navbar */}
      <Navbar
        language={language}
        onLanguageChange={setLanguage}
        isSimulating={isSimulating}
        onToggleSimulation={handleToggleSimulation}
        onOpenReportModal={() => setIsReportModalOpen(true)}
        onOpenTerminologyModal={() => setIsTerminologyModalOpen(true)}
      />

      {/* Main Crisis Room Grid Dashboard */}
      <DashboardLayout
        banner={
          <AlertBanner
            severity="severe"
            language={language}
          />
        }
        advisorySection={
          <DisasterAdvisoryCard
            selectedZone={selectedZone}
            language={language}
          />
        }
        mapSection={
          <MapView
            riskZonesGeoJSON={riskZones}
            roads={roads}
            settlements={settlements}
            selectedZone={selectedZone}
            language={language}
            isSimulating={isSimulating}
            onSelectZone={setSelectedZone}
          />
        }
        weatherSection={
          <WeatherChart
            data={weatherData}
            language={language}
            selectedZone={selectedZone}
            caineThreshold={selectedZone?.criticalRainThreshold || 35.0}
            onRefresh={refreshWeather}
          />
        }
        riskSummarySection={
          <RiskSummaryCard
            summary={riskSummary}
            language={language}
            onSelectFilter={(level) => console.log('Filter by risk level:', level)}
          />
        }
        roadSection={
          <RoadTable
            roads={roads}
            language={language}
            onSelectRoad={(road) => console.log('Selected road:', road)}
          />
        }
        emergencySection={
          <EmergencyPrioritizationCard
            settlements={settlements}
            language={language}
            onSelectSettlement={(settlement) => console.log('Selected settlement:', settlement)}
          />
        }
        reportsSection={
          <RecentReportsTable
            reports={reports}
            language={language}
            onOpenReportModal={() => setIsReportModalOpen(true)}
          />
        }
      />

      {/* Citizen Hazard Reporting Modal */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={submitReport}
        language={language}
      />

      {/* Scientific Terminology Help Guide Modal */}
      <TerminologyModal
        isOpen={isTerminologyModalOpen}
        onClose={() => setIsTerminologyModalOpen(false)}
        language={language}
      />

      {/* Floating Multilingual AI Disaster Assistant Chatbot */}
      <EmergencyAiChat
        language={language}
        onSelectZone={setSelectedZone}
      />
    </div>
  );
}
