/**
 * État d'authentification partagé.
 *
 * Vit dans un contexte plutôt que dans la racine de navigation : celle-ci doit
 * rendre un navigateur dès le premier rendu, sans jamais le démonter. Rendre
 * un écran d'attente à sa place fait boucler React sur « Maximum update depth
 * exceeded ».
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import * as api from './api';
import * as session from './session';

interface AuthState {
  /** Faux tant que le jeton stocké n'a pas été relu. */
  ready: boolean;
  signedIn: boolean;
  baseUrl: string;
  signIn: (baseUrl: string, token: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [baseUrl, setBaseUrl] = useState(session.defaultBaseUrl);

  useEffect(() => {
    let alive = true;

    // Un 401 quelconque doit ramener à la connexion. On ne navigue pas d'ici :
    // on change l'état, et l'écran monté s'en charge par un <Redirect>.
    api.configure({ onUnauthorized: () => alive && setSignedIn(false) });

    session
      .load()
      .then((restored) => {
        if (!alive) return;
        setSignedIn(Boolean(restored));
        if (restored) setBaseUrl(restored.baseUrl);
      })
      .catch(() => alive && setSignedIn(false))
      .finally(() => alive && setReady(true));

    return () => {
      alive = false;
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      ready,
      signedIn,
      baseUrl,
      async signIn(url, token) {
        await session.save(url, token);
        setBaseUrl(url);
        setSignedIn(true);
      },
      async signOut() {
        await session.clear();
        setSignedIn(false);
      },
    }),
    [ready, signedIn, baseUrl]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>.');
  return context;
}
