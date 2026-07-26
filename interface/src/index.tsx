/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { AppRoutes } from '@/routes/AppRoutes';
import { Mark } from '@components/brand/Mark';
import { applyTheme } from '@design/themes';
import { system } from '@services/api';
import { whenReady } from '@services/transport';
import './styles/globals.css';

/**
 * Boot gate.
 *
 * The desktop shell injects its bridge asynchronously and the kernel needs a
 * moment to start, so the UI waits for a ready status before mounting routes.
 */
function Boot() {
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState('Starting the kernel…');

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    const poll = async () => {
      const host = await whenReady();
      document.body.dataset.host = host;

      while (!cancelled) {
        try {
          const status = await system.status();
          if (status.ready) {
            if (!cancelled) setReady(true);
            return;
          }
          setMessage('Waiting for the kernel…');
        } catch {
          attempts += 1;
          setMessage(
            attempts > 6
              ? 'Cannot reach AERA. Is the kernel running?'
              : 'Connecting to the kernel…',
          );
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_50%_45%,#101827,var(--aera-bg-base)_70%)]">
        <Mark size={72} glow className="animate-pulse-slow" />
        <h1 className="text-[20px] font-semibold tracking-[0.3em]">AERA</h1>
        <p className="text-[12.5px] text-[var(--aera-text-muted)]">{message}</p>
      </div>
    );
  }

  // HashRouter: the desktop shell loads the UI from file:// where path-based
  // routing has no server to fall back on.
  return (
    <HashRouter>
      <AppRoutes />
    </HashRouter>
  );
}

applyTheme('dark');

const container = document.getElementById('root');
if (!container) throw new Error('#root is missing from index.html');

createRoot(container).render(
  <StrictMode>
    <Boot />
  </StrictMode>,
);
