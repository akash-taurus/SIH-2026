import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/globals.css';
import App from './App';
import { AppProvider } from './contexts/AppContext';

// Prevent benign ResizeObserver loop warning from triggering React dev overlay
const resizeObserverErrorHandler = (e) => {
  if (
    e?.message === 'ResizeObserver loop completed with undelivered notifications.' ||
    e?.message === 'ResizeObserver loop limit exceeded' ||
    (typeof e?.message === 'string' && e.message.includes('ResizeObserver'))
  ) {
    e.stopImmediatePropagation();
  }
};
window.addEventListener('error', resizeObserverErrorHandler);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </React.StrictMode>
);
