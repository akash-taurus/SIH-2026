import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import AlertBanner from '../components/AlertBanner';

test('renders severe alert banner with dismiss action', () => {
  const onDismiss = jest.fn();
  render(
    <AlertBanner
      severity="severe"
      title="TEST SEVERE WARNING"
      message="Test evacuation message"
      onDismiss={onDismiss}
    />
  );

  expect(screen.getByText('TEST SEVERE WARNING')).toBeInTheDocument();
  expect(screen.getByText('Test evacuation message')).toBeInTheDocument();
  expect(screen.getByText(/CRITICAL SEVERE HAZARD/i)).toBeInTheDocument();

  const dismissBtn = screen.getByLabelText(/Dismiss alert/i);
  fireEvent.click(dismissBtn);
  expect(onDismiss).toHaveBeenCalledTimes(1);
  expect(screen.queryByText('TEST SEVERE WARNING')).not.toBeInTheDocument();
});

test('renders moderate alert banner styling', () => {
  render(<AlertBanner severity="moderate" language="en" />);
  expect(screen.getByText(/MODERATE WATCH/i)).toBeInTheDocument();
});
