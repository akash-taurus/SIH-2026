import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Navbar from '../components/Navbar';

test('renders brand title and version tag in Navbar', () => {
  render(<Navbar language="en" />);
  expect(screen.getByText(/NER Landslide Early Warning System/i)).toBeInTheDocument();
  expect(screen.getByText(/v1.0-MVP/i)).toBeInTheDocument();
  expect(screen.getByText(/SYSTEM ACTIVE/i)).toBeInTheDocument();
});

test('handles language change in Navbar', () => {
  const onLanguageChange = jest.fn();
  render(<Navbar language="en" onLanguageChange={onLanguageChange} />);
  
  const select = screen.getByRole('combobox');
  fireEvent.change(select, { target: { value: 'hi' } });
  expect(onLanguageChange).toHaveBeenCalledWith('hi');
});

test('shows simulation badge when isSimulating is true', () => {
  render(<Navbar language="en" isSimulating={true} />);
  expect(screen.getByText(/STORM SIMULATION/i)).toBeInTheDocument();
});
