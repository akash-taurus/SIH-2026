import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import RecentReportsTable from '../components/RecentReportsTable';

const mockReports = [
  {
    id: 'REP-2026-081',
    reporter: 'Field Officer K. Sangma',
    location_name: 'Umiam Viewpoint, NH-40',
    latitude: 25.6612,
    longitude: 91.9024,
    note: 'Fresh tension crack measuring ~15 meters observed across upper embankment.',
    severity: 'severe',
    status: 'verified',
    timestamp: '18 mins ago',
    photo_url: null
  },
  {
    id: 'REP-2026-079',
    reporter: 'Citizen Responder D. Roy',
    location_name: 'Nongthymmai Road',
    latitude: 25.5641,
    longitude: 91.8955,
    note: 'Small pebble detachment and muddy runoff over drainage culvert.',
    severity: 'moderate',
    status: 'verified',
    timestamp: '1 hour ago',
    photo_url: null
  }
];

const mockOnOpenReportModal = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
});

test('renders report count and title', () => {
  render(<RecentReportsTable reports={mockReports} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText(/Verified Community Field Reports/i)).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument();
});

test('renders report button when onOpenReportModal provided', () => {
  render(<RecentReportsTable reports={mockReports} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  const button = screen.getByText(/Report Hazard/i);
  expect(button).toBeInTheDocument();
  
  fireEvent.click(button);
  expect(mockOnOpenReportModal).toHaveBeenCalledTimes(1);
});

test('does not render report button when onOpenReportModal not provided', () => {
  render(<RecentReportsTable reports={mockReports} language="en" />);
  
  expect(screen.queryByText(/Report Hazard/i)).not.toBeInTheDocument();
});

test('renders empty state when no reports', () => {
  render(<RecentReportsTable reports={[]} language="en" />);
  
  expect(screen.getByText(/No community reports submitted/i)).toBeInTheDocument();
});

test('renders table with correct columns', () => {
  render(<RecentReportsTable reports={mockReports} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  const idElements = screen.getAllByText(/ID/i);
  expect(idElements.length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/Location/i)).toBeInTheDocument();
  expect(screen.getByText(/Observations/i)).toBeInTheDocument();
  expect(screen.getByText(/Severity/i)).toBeInTheDocument();
  expect(screen.getByText(/Reporter/i)).toBeInTheDocument();
  expect(screen.getByText(/Time/i)).toBeInTheDocument();
});

test('renders report data correctly', () => {
  render(<RecentReportsTable reports={mockReports} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText('REP-2026-081')).toBeInTheDocument();
  expect(screen.getByText('Umiam Viewpoint, NH-40')).toBeInTheDocument();
  expect(screen.getByText('25.6612°N, 91.9024°E')).toBeInTheDocument();
  expect(screen.getByText(/Fresh tension crack measuring/)).toBeInTheDocument();
  expect(screen.getByText('Field Officer K. Sangma')).toBeInTheDocument();
  expect(screen.getByText('18 mins ago')).toBeInTheDocument();
});

test('renders severity badges correctly', () => {
  render(<RecentReportsTable reports={mockReports} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText('Severe')).toBeInTheDocument();
  expect(screen.getByText('Moderate')).toBeInTheDocument();
});

test('shows photo evidence indicator when photo_url present', () => {
  const reportsWithPhoto = [{ ...mockReports[0], photo_url: 'http://example.com/photo.jpg' }];
  render(<RecentReportsTable reports={reportsWithPhoto} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText(/Attached Photo Evidence/i)).toBeInTheDocument();
});

test('renders in Hindi language', () => {
  render(<RecentReportsTable reports={mockReports} language="hi" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText(/सत्यापित सामुदायिक मैदानी रिपोर्ट/i)).toBeInTheDocument();
  expect(screen.getByText(/खतरे की रिपोर्ट करें/i)).toBeInTheDocument();
});

test('renders in Assamese language', () => {
  render(<RecentReportsTable reports={mockReports} language="as" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.getByText(/পৰীক্ষিত সামূহিক মাটিকেন্দ্রীক প্ৰতিবেদন/i)).toBeInTheDocument();
  expect(screen.getByText(/বিপদৰ প্ৰতিবেদন দাখিল কৰক/i)).toBeInTheDocument();
});

test('handles reports without coordinates', () => {
  const reportsNoCoords = [{ ...mockReports[0], latitude: null, longitude: null }];
  render(<RecentReportsTable reports={reportsNoCoords} language="en" onOpenReportModal={mockOnOpenReportModal} />);
  
  expect(screen.queryByText(/°N,.*°E/)).not.toBeInTheDocument();
});