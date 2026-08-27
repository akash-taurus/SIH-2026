import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import WeatherChart from '../components/WeatherChart';

global.ResizeObserver = class ResizeObserver {
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
};

const mockWeatherData = [
  { time: 'Day 1 00:00', rainfall: 8.2, soilMoisture: 42.1 },
  { time: 'Day 1 06:00', rainfall: 29.8, soilMoisture: 54.0 },
  { time: 'Day 1 12:00', rainfall: 62.4, soilMoisture: 81.5 },
  { time: 'Day 2 00:00', rainfall: 15.6, soilMoisture: 74.0 },
  { time: 'Day 2 12:00', rainfall: 42.0, soilMoisture: 91.0 },
];

const renderChart = (props = {}) => render(
  <div style={{ width: 400, height: 300 }}>
    <WeatherChart {...props} />
  </div>
);

test('renders chart title and subtitle', () => {
  renderChart({ data: mockWeatherData, language: "en" });
  
  expect(screen.getByText(/72-Hour Precipitation Forecast/i)).toBeInTheDocument();
  expect(screen.getByText(/Caine I-D Critical Curve/i)).toBeInTheDocument();
  expect(screen.getByText(/24-72h Lead Time/i)).toBeInTheDocument();
});

test('renders summary metrics', () => {
  renderChart({ data: mockWeatherData, language: "en" });
  
  expect(screen.getByText(/Peak Rain Rate/i)).toBeInTheDocument();
  expect(screen.getByText(/62\.4 mm\/h/i)).toBeInTheDocument();
  expect(screen.getByText(/Max Saturation/i)).toBeInTheDocument();
  expect(screen.getByText(/91\.0%/i)).toBeInTheDocument();
});

test('shows threshold breached when peak exceeds threshold', () => {
  renderChart({ data: mockWeatherData, language: "en", caineThreshold: 35.0 });
  
  expect(screen.getByText(/Threshold Breached/i)).toBeInTheDocument();
});

test('shows below critical when peak is under threshold', () => {
  const lowData = mockWeatherData.map(d => ({ ...d, rainfall: d.rainfall * 0.3 }));
  renderChart({ data: lowData, language: "en", caineThreshold: 35.0 });
  
  expect(screen.getByText(/Below Critical/i)).toBeInTheDocument();
});

test('renders empty state when no data', () => {
  renderChart({ data: [], language: "en" });
  
  expect(screen.getByText(/No forecast data available/i)).toBeInTheDocument();
  expect(screen.getByText(/0\.0 mm\/h/i)).toBeInTheDocument();
  expect(screen.getByText(/0\.0%/i)).toBeInTheDocument();
  expect(screen.getByText(/Below Critical/i)).toBeInTheDocument();
});

test('renders in Hindi language', () => {
  renderChart({ data: mockWeatherData, language: "hi" });
  
  expect(screen.getByText(/72 घंटे का वर्षा पूर्वानुमान/i)).toBeInTheDocument();
  expect(screen.getByText(/भौतिकी सीमा: केन आई-डी/i)).toBeInTheDocument();
});

test('renders in Assamese language', () => {
  renderChart({ data: mockWeatherData, language: "as" });
  
  expect(screen.getByText(/৭২ ঘণ্টাৰ বৰষুণৰ পূৰ্বাভাস/i)).toBeInTheDocument();
  expect(screen.getByText(/কেইন I-D গুৰুত্বপূৰ্ণ বক্ৰৰেখা/i)).toBeInTheDocument();
});

test('uses custom caine threshold', () => {
  const data = [{ time: 'Day 1', rainfall: 40, soilMoisture: 50 }];
  renderChart({ data, language: "en", caineThreshold: 50.0 });
  
  expect(screen.getByText(/Below Critical/i)).toBeInTheDocument();
});

test('shows threshold breached with custom threshold', () => {
  const data = [{ time: 'Day 1', rainfall: 60, soilMoisture: 50 }];
  renderChart({ data, language: "en", caineThreshold: 50.0 });
  
  expect(screen.getByText(/Threshold Breached/i)).toBeInTheDocument();
});