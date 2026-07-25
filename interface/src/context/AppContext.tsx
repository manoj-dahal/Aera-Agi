import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { detectHost, type HostKind } from '@services/transport';

interface AppContextValue {
  /** Whether the UI is embedded in the desktop shell or served over HTTP. */
  host: HostKind;
  isDesktop: boolean;
}

const AppContext = createContext<AppContextValue>({ host: 'http', isDesktop: false });

export function AppProvider({ children }: { children: ReactNode }) {
  const value = useMemo<AppContextValue>(() => {
    const host = detectHost();
    return { host, isDesktop: host === 'desktop' };
  }, []);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  return useContext(AppContext);
}
