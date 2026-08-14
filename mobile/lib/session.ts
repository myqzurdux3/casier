/**
 * Session persistée : adresse du serveur et jeton porteur.
 *
 * Le jeton va dans SecureStore, adossé au keystore matériel Android, et non
 * dans AsyncStorage qui est un simple fichier lisible sur un appareil rooté.
 * L'adresse du serveur n'est pas un secret et reste à côté par commodité.
 */

import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';

import * as api from './api';

const TOKEN_KEY = 'spotify_sort_token';
const URL_KEY = 'spotify_sort_base_url';

export const defaultBaseUrl: string =
  (Constants.expoConfig?.extra?.defaultBaseUrl as string) ?? '';

export interface Session {
  baseUrl: string;
  token: string;
}

export async function load(): Promise<Session | null> {
  const [token, storedUrl] = await Promise.all([
    SecureStore.getItemAsync(TOKEN_KEY),
    SecureStore.getItemAsync(URL_KEY),
  ]);
  const baseUrl = storedUrl ?? defaultBaseUrl;
  if (!token) {
    api.configure({ baseUrl });
    return null;
  }
  api.configure({ baseUrl, token });
  return { baseUrl, token };
}

export async function save(baseUrl: string, token: string): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(TOKEN_KEY, token),
    SecureStore.setItemAsync(URL_KEY, baseUrl),
  ]);
  api.configure({ baseUrl, token });
}

export async function clear(): Promise<void> {
  // L'adresse du serveur survit à la déconnexion : la ressaisir à chaque fois
  // serait pénible, et elle n'est pas secrète.
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  api.configure({ token: '' });
}
