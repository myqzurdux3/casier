/** Palette et styles partagés — l'app reprend les codes sombres du panel web. */

import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#121212',
  card: '#1c1c1e',
  border: '#2c2c2e',
  text: '#f2f2f7',
  muted: '#98989f',
  accent: '#1db954',
  error: '#ff453a',
  warn: '#ffd60a',
  ok: '#30d158',
};

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, gap: 12 },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { color: colors.text, fontSize: 20, fontWeight: '600' },
  heading: { color: colors.text, fontSize: 16, fontWeight: '600' },
  text: { color: colors.text, fontSize: 15 },
  muted: { color: colors.muted, fontSize: 13 },
  mono: {
    color: colors.text,
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: 17,
  },
  input: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    color: colors.text,
    fontSize: 15,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 13,
    alignItems: 'center',
  },
  buttonText: { color: '#04170c', fontSize: 15, fontWeight: '700' },
  buttonGhost: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 13,
    alignItems: 'center',
  },
  buttonGhostText: { color: colors.text, fontSize: 15, fontWeight: '600' },
  disabled: { opacity: 0.4 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  banner: { borderRadius: 8, padding: 12, borderWidth: 1 },
});

export const bannerStyle = (kind: 'error' | 'warn' | 'ok') => ({
  backgroundColor: { error: '#3a1512', warn: '#332a05', ok: '#0d2c17' }[kind],
  borderColor: { error: colors.error, warn: colors.warn, ok: colors.ok }[kind],
});
