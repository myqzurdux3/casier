/**
 * Fournisseur de langue.
 *
 * Le catalogue et la fonction de traduction vivent dans `messages.ts`, sans
 * JSX, pour rester testables sous Node. Ici, seulement le contexte React : ce
 * qui déclenche un rendu quand la langue change.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as SecureStore from 'expo-secure-store';

import * as api from './api';
import { detectLang, translate, type Lang, type LangPref } from './messages';

export { detectLang, translate, MESSAGES } from './messages';
export type { Lang, LangPref } from './messages';

const PREF_KEY = 'casier_language';

export type Traduire = (cle: string, params?: Record<string, string | number>) => string;

interface Contexte {
  t: Traduire;
  lang: Lang;
  pref: LangPref;
  setPref: (pref: LangPref) => void;
}

const I18nContext = createContext<Contexte | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [pref, setPrefState] = useState<LangPref>('auto');

  useEffect(() => {
    let vivant = true;
    SecureStore.getItemAsync(PREF_KEY)
      .then((stocke) => {
        if (vivant && (stocke === 'fr' || stocke === 'en' || stocke === 'auto')) {
          setPrefState(stocke);
        }
      })
      // Un préréglage illisible n'est pas une panne : on reste sur `auto`.
      .catch(() => undefined);
    return () => {
      vivant = false;
    };
  }, []);

  const lang: Lang = pref === 'auto' ? detectLang() : pref;

  // Le serveur traduit ses propres messages d'après cet en-tête.
  useEffect(() => {
    api.configure({ language: lang });
  }, [lang]);

  const setPref = useCallback((suivant: LangPref) => {
    setPrefState(suivant);
    void SecureStore.setItemAsync(PREF_KEY, suivant).catch(() => undefined);
  }, []);

  const t = useCallback<Traduire>((cle, params) => translate(cle, lang, params), [lang]);

  const valeur = useMemo(() => ({ t, lang, pref, setPref }), [t, lang, pref, setPref]);
  return <I18nContext.Provider value={valeur}>{children}</I18nContext.Provider>;
}

export function useI18n(): Contexte {
  const contexte = useContext(I18nContext);
  if (!contexte) throw new Error('useI18n hors de I18nProvider');
  return contexte;
}
