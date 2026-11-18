import React from 'react';
import { createRoot } from 'react-dom/client';
import { analytics } from '@heycatch/sdk';
import './styles.css';
import App from './App';

analytics.init({
  projectKey: 'hck_pk_Ok4IUNOnuc7mFJaal473FDx15VHFHrHE',
  install: { framework: 'react', frameworkVersion: '18', agent: 'other' },
});

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);
