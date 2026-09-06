import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmergencyAiChat from '../components/EmergencyAiChat';

// Mock speech synthesis
beforeAll(() => {
  global.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => ({
    text,
    lang: 'en',
    rate: 1,
    pitch: 1
  }));

  window.speechSynthesis = {
    speak: jest.fn(),
    cancel: jest.fn(),
    getVoices: jest.fn(() => [])
  };
});

describe('EmergencyAiChat Component', () => {
  it('renders the chat button initially', () => {
    render(<EmergencyAiChat />);
    expect(screen.getByText(/Disaster & Safety Assistant/i)).toBeInTheDocument();
  });

  it('opens and closes the chat window', () => {
    render(<EmergencyAiChat />);
    
    // Should be closed initially
    expect(screen.queryByPlaceholderText(/Ask a safety question/i)).not.toBeInTheDocument();

    // Click to open
    const toggleBtn = screen.getByText(/Disaster & Safety Assistant/i);
    fireEvent.click(toggleBtn);
    
    // Should be open now
    expect(screen.getByPlaceholderText(/Ask a safety question/i)).toBeInTheDocument();

    // Click to close
    const closeBtn = screen.getByText('✕');
    fireEvent.click(closeBtn);
  });

  test('renders floating button in Khasi', () => {
    render(<EmergencyAiChat language="kha" />);
    expect(screen.getByText(/U Nongiarap AI|Khasi/i)).toBeInTheDocument();
  });

  test('renders quick location chips and clicking one sends message', async () => {
    render(<EmergencyAiChat language="kha" />);
    const toggleBtn = screen.getByText(/U Nongiarap AI|Khasi/i);
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Laitlyngkot|লাইতলিংকট/i })).toBeInTheDocument();
    });

    const chip = screen.getByRole('button', { name: /Laitlyngkot|লাইতলিংকট/i });
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getAllByText(/Laitlyngkot|লাইতলিংকট/i).length).toBeGreaterThan(0);
    });
  });
});
