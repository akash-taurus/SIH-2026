import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TerminologyModal from '../components/TerminologyModal';

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

describe('TerminologyModal Component', () => {
  test('does not render when isOpen is false', () => {
    const { container } = render(<TerminologyModal isOpen={false} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders terminology terms in English when open', () => {
    render(<TerminologyModal isOpen={true} language="en" />);
    expect(screen.getByText(/Disaster Terminology & Science Guide/i)).toBeInTheDocument();
    expect(screen.getByText(/Factor of Safety \(FS\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Sentinel-1 InSAR & Ground Creep/i)).toBeInTheDocument();
  });

  test('renders terminology terms in Khasi (Bengali-Assamese script)', () => {
    render(<TerminologyModal isOpen={true} language="kha" />);
    expect(screen.getByText(/কা জিংবাতাই শাফাং কি ক্তিয়েন জিংমা/i)).toBeInTheDocument();
    expect(screen.getByText(/Factor of Safety/i)).toBeInTheDocument();
  });

  test('renders terminology terms in Assamese', () => {
    render(<TerminologyModal isOpen={true} language="as" />);
    expect(screen.getByText(/ভূমিস্খলন আৰু ভূ-পদাৰ্থ বিজ্ঞানৰ পৰিভাষা সহায়িকা/i)).toBeInTheDocument();
    expect(screen.getByText(/সুৰক্ষা গুণক/i)).toBeInTheDocument();
  });

  test('category tabs filter terms', () => {
    render(<TerminologyModal isOpen={true} language="en" />);
    const radarTab = screen.getByRole('button', { name: /Satellites & InSAR/i });
    fireEvent.click(radarTab);

    expect(screen.getByText(/Sentinel-1 InSAR & Ground Creep/i)).toBeInTheDocument();
  });

  test('calls onClose when close button is clicked', () => {
    const handleClose = jest.fn();
    render(<TerminologyModal isOpen={true} onClose={handleClose} language="en" />);
    const closeBtn = screen.getByRole('button', { name: /✕ Close/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
