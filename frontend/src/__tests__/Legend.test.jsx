import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Legend from '../components/Legend';

test('renders Legend component with green-yellow-orange-red risk levels', () => {
  render(<Legend language="en" />);
  expect(screen.getByText(/Risk Map/i)).toBeInTheDocument();
  expect(screen.getByText(/Severe Risk/i)).toBeInTheDocument();
  expect(screen.getByText(/High Risk/i)).toBeInTheDocument();
  expect(screen.getByText(/Moderate Risk/i)).toBeInTheDocument();
  expect(screen.getByText(/Low Risk/i)).toBeInTheDocument();
});

test('renders highway status legend items', () => {
  render(<Legend language="en" />);
  expect(screen.getByText(/Open Highway/i)).toBeInTheDocument();
  expect(screen.getByText(/At Risk \/ Blocked/i)).toBeInTheDocument();
});
