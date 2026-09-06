import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ThreeDMapHeatmap from '../components/ThreeDMapHeatmap';

test('renders 3D Topo-Heatmap header and preset angle buttons', () => {
  render(<ThreeDMapHeatmap language="en" />);
  expect(screen.getByText(/3D TOPO-HEATMAP/i)).toBeInTheDocument();
  expect(screen.getByText(/Oblique 3D/i)).toBeInTheDocument();
  expect(screen.getByText(/Isometric 45°/i)).toBeInTheDocument();
  expect(screen.getByText(/Top-Down/i)).toBeInTheDocument();
  expect(screen.getByText(/3D Orbit/i)).toBeInTheDocument();
  expect(screen.getByText(/Fullscreen/i)).toBeInTheDocument();
  expect(screen.getByText(/Labels/i)).toBeInTheDocument();
});

test('renders elevation height legend in 3D mode', () => {
  render(<ThreeDMapHeatmap language="en" />);
  expect(screen.getByText(/Elevation & Heatmap Scale/i)).toBeInTheDocument();
  expect(screen.getByText(/1,496 m/i)).toBeInTheDocument();
  expect(screen.getByText(/1,430 m/i)).toBeInTheDocument();
  expect(screen.getByText(/Shillong Peak Ridge/i)).toBeInTheDocument();
});

test('handles camera view preset button clicks', () => {
  render(<ThreeDMapHeatmap language="en" />);
  const isoBtn = screen.getByText(/Isometric 45°/i);
  fireEvent.click(isoBtn);
  expect(isoBtn).toHaveClass('bg-black');

  const topBtn = screen.getByText(/Top-Down/i);
  fireEvent.click(topBtn);
  expect(topBtn).toHaveClass('bg-black');
});

test('handles fullscreen toggle', () => {
  render(<ThreeDMapHeatmap language="en" />);
  const fsBtn = screen.getByText(/Fullscreen/i);
  fireEvent.click(fsBtn);
  expect(screen.getByText(/Exit/i)).toBeInTheDocument();
});
