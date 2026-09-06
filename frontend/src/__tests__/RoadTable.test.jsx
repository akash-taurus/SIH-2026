import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import RoadTable from '../components/RoadTable';

const mockRoads = [
  { road_id: 'NH-40', name: 'Shillong Expressway', status: 'blocked', blockage_reason: 'Mudslide', last_updated: '5m ago' },
  { road_id: 'SH-5', name: 'Sohra Highway', status: 'open', blockage_reason: null, last_updated: '20m ago' }
];

test('renders road status table and badges', () => {
  render(<RoadTable roads={mockRoads} language="en" />);
  expect(screen.getByText(/Highway Connectivity Status/i)).toBeInTheDocument();
  expect(screen.getByText('NH-40')).toBeInTheDocument();
  expect(screen.getByText('SH-5')).toBeInTheDocument();
  expect(screen.getByText(/Blocked/i)).toBeInTheDocument();
  expect(screen.getByText(/Open/i)).toBeInTheDocument();
});
