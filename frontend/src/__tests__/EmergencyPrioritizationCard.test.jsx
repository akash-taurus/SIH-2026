import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmergencyPrioritizationCard from '../components/EmergencyPrioritizationCard';

const mockSettlements = [
  { village: 'Mawsynram Sector', district: 'East Khasi Hills', population: 1337, risk_level: 'severe', distance_km: 3.4, nearest_hospital: 'CHC', priority_rank: 1, evacuation_status: 'Evacuate' },
  { village: 'Cherrapunji', district: 'East Khasi Hills', population: 2450, risk_level: 'high', distance_km: 5.8, nearest_hospital: 'CHC', priority_rank: 2, evacuation_status: 'Standby' }
];

test('renders prioritized settlements and ranks', () => {
  render(<EmergencyPrioritizationCard settlements={mockSettlements} language="en" />);
  expect(screen.getByText(/Emergency Evacuation Prioritization/i)).toBeInTheDocument();
  expect(screen.getByText('Mawsynram Sector')).toBeInTheDocument();
  expect(screen.getByText('#1 PRIORITY')).toBeInTheDocument();
  expect(screen.getByText('#2 PRIORITY')).toBeInTheDocument();
});
