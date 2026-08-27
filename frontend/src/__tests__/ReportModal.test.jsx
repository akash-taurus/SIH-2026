import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ReportModal from '../components/ReportModal';

const mockOnSubmit = jest.fn();
const mockOnClose = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  mockOnSubmit.mockResolvedValue(undefined);
  
  // Mock geolocation globally for tests that need it
  global.navigator.geolocation = {
    getCurrentPosition: jest.fn((success) => {
      success({
        coords: { latitude: 25.5788, longitude: 91.8933, accuracy: 10 }
      });
    })
  };
  
  // Mock URL.createObjectURL for photo preview tests
  global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
  global.URL.revokeObjectURL = jest.fn();
});

test('does not render when isOpen is false', () => {
  const { container } = render(
    <ReportModal isOpen={false} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );
  expect(container.firstChild).toBeNull();
});

test('renders form elements and triggers onClose when cancel is clicked', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  expect(screen.getByText(/Submit Field Hazard Report/i)).toBeInTheDocument();
  expect(screen.getByText(/Get GPS/i)).toBeInTheDocument();

  const cancelButton = screen.getByText(/^Cancel$/i);
  fireEvent.click(cancelButton);
  expect(mockOnClose).toHaveBeenCalledTimes(1);
});

test('shows validation error when note is empty', async () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const submitButton = screen.getByText(/Submit Report/i);
  fireEvent.click(submitButton);

  await waitFor(() => {
    const errorElements = screen.getAllByText(/Description is required/i);
    expect(errorElements.length).toBeGreaterThan(0);
  });
  expect(mockOnSubmit).not.toHaveBeenCalled();
});

test('shows validation error when note is too short', async () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const textarea = screen.getByPlaceholderText(/Describe visible cracks/i);
  fireEvent.change(textarea, { target: { value: 'Short' } });

  const submitButton = screen.getByText(/Submit Report/i);
  fireEvent.click(submitButton);

  await waitFor(() => {
    const errorElements = screen.getAllByText(/at least 10 characters/i);
    expect(errorElements.length).toBeGreaterThan(0);
  });
});

test('submits form with note, coordinates, and photo', async () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const textarea = screen.getByPlaceholderText(/Describe visible cracks/i);
  fireEvent.change(textarea, { target: { value: 'Fresh tension crack observed on slope.' } });

  const gpsButton = screen.getByText(/Get GPS/i);
  fireEvent.click(gpsButton);

  await waitFor(() => {
    expect(screen.getByDisplayValue(/25\.57880° N, 91\.89330° E/)).toBeInTheDocument();
  });

  const submitButton = screen.getByText(/Submit Report/i);
  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        note: 'Fresh tension crack observed on slope.',
        latitude: 25.5788,
        longitude: 91.8933,
        photo: null
      })
    );
  });
});

test('renders in Hindi language', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="hi" />
  );

  expect(screen.getByText(/मैदानी खतरे की रिपोर्ट सबमिट करें/i)).toBeInTheDocument();
  expect(screen.getByText(/विवरण \/ टिप्पणियां/i)).toBeInTheDocument();
  expect(screen.getByText(/जीपीएस प्राप्त करें/i)).toBeInTheDocument();
});

test('renders in Assamese language', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="as" />
  );

  expect(screen.getByText(/মাটিৰ ফাট বা স্খলনৰ তথ্য দিয়ক/i)).toBeInTheDocument();
  expect(screen.getByText(/বিৱৰণ \/ টোকা/i)).toBeInTheDocument();
  expect(screen.getByText(/GPS লওক/i)).toBeInTheDocument();
});

test('handles photo attachment and removal', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const fileInput = screen.getByTestId('photo-input');
  const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
  
  fireEvent.change(fileInput, { target: { files: [mockFile] } });

  expect(screen.getByText(/test\.jpg/i)).toBeInTheDocument();
  expect(screen.getByText(/Remove/i)).toBeInTheDocument();

  fireEvent.click(screen.getByText(/Remove/i));
  expect(screen.queryByText(/test\.jpg/i)).not.toBeInTheDocument();
});

test('shows error for invalid photo file type', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const fileInput = screen.getByTestId('photo-input');
  const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
  
  fireEvent.change(fileInput, { target: { files: [mockFile] } });

  expect(screen.getByText(/Invalid file type/i)).toBeInTheDocument();
});

test('shows error for oversized photo', () => {
  render(
    <ReportModal isOpen={true} onClose={mockOnClose} onSubmit={mockOnSubmit} language="en" />
  );

  const fileInput = screen.getByTestId('photo-input');
  const largeFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large.jpg', { type: 'image/jpeg' });
  
  fireEvent.change(fileInput, { target: { files: [largeFile] } });

  expect(screen.getByText(/File too large/i)).toBeInTheDocument();
});
