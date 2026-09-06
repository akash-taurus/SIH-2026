import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import RiskSummaryCard from '../components/RiskSummaryCard';

const mockSummary = [
  { level: 'Low', count: 14, percentage: 35 },
  { level: 'Moderate', count: 10, percentage: 25 },
  { level: 'High', count: 12, percentage: 30 },
  { level: 'Severe', count: 4, percentage: 10 }
];

test('renders risk summary distribution bars and counts', () => {
  render(<RiskSummaryCard summary={mockSummary} language="en" />);
  expect(screen.getByText(/Regional Risk Distribution/i)).toBeInTheDocument();
  expect(screen.getByText('40')).toBeInTheDocument(); // total 14+10+12+4 = 40
  expect(screen.getByText('Severe Risk')).toBeInTheDocument();
  expect(screen.getByText('High Risk')).toBeInTheDocument();
});
