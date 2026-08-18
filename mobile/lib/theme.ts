/** Palette et styles partagés — l'app et le panel web suivent le même thème. */

import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#1B1D20',
  surface: '#23262A',
  border: '#33373C',
  text: '#F2F3F4',
  muted: '#8E959C',
  faint: '#6E757C',
  // `accent` veut dire « on peut appuyer » : action principale, onglet actif,
  // état OK. Rien d'autre. L'appartenance à un casier se dit avec les huit
  // teintes de categoryColor.ts, et les deux rôles ne se croisent jamais.
  accent: '#D7E63B',
  onAccent: '#1B1D20',
  error: '#F2795E',
  warn: '#E8A33D',
  ok: '#D7E63B',
  // Fond des chromes du système de navigation (barre d'onglets), un cran plus
  // sombre que `bg` pour les détacher du contenu sans y poser de bordure.
  chrome: '#16181A',
};

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  // Le contenu ne met plus de marge : ce sont les sections qui portent leur
  // retrait, pour que leurs filets aillent d'un bord à l'autre de l'écran.
  content: { padding: 0, gap: 0 },
  // Anciennement une carte posée sur le fond. Devient une section : même fond
  // que l'écran, séparée de la précédente par un filet d'un pixel.
  card: {
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 10,
  },
  title: { color: colors.text, fontSize: 26, fontWeight: '700', letterSpacing: -0.6 },
  heading: { color: colors.text, fontSize: 20, fontWeight: '700', letterSpacing: -0.4 },
  text: { color: colors.text, fontSize: 15.5 },
  muted: { color: colors.muted, fontSize: 12.5 },
  // Libellé technique. `textTransform` suffit sur un <Text> : inutile de
  // doubler avec toUpperCase() dans le JSX.
  label: {
    color: colors.muted,
    fontFamily: 'monospace',
    fontSize: 10.5,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  // Chiffre mis en avant. Monospace et non fontVariant: ['tabular-nums'] :
  // le support Android de tabular-nums est inégal, la monospace aligne à coup sûr.
  metric: {
    color: colors.text,
    fontFamily: 'monospace',
    fontSize: 34,
    letterSpacing: -1,
  },
  mono: {
    color: colors.text,
    fontFamily: 'monospace',
    fontSize: 12.5,
    lineHeight: 17,
  },
  input: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 4,
    padding: 12,
    color: colors.text,
    fontFamily: 'monospace',
    fontSize: 12.5,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 4,
    paddingVertical: 15,
    alignItems: 'center',
  },
  buttonText: { color: colors.onAccent, fontSize: 15, fontWeight: '700' },
  // Conservé pour les écrans que la refonte n'a pas encore repris : les tâches
  // secondaires deviendront des lignes de liste, et ce style disparaîtra alors.
  buttonGhost: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 4,
    paddingVertical: 13,
    alignItems: 'center',
  },
  buttonGhostText: { color: colors.text, fontSize: 15, fontWeight: '600' },
  disabled: { opacity: 0.4 },
  // Ligne de liste : 44 points de haut au minimum, la plus petite cible
  // tactile confortable recommandée par Android.
  listRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    minHeight: 44,
    paddingVertical: 10,
  },
  // Puce d'état. Rectangulaire et non une pastille : c'est la forme du carré
  // du logo, reprise partout.
  chip: {
    borderRadius: 2,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderWidth: 1,
  },
  chipText: {
    fontFamily: 'monospace',
    fontSize: 10.5,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  // Marge horizontale portée par le bandeau lui-même : `content` n'en met plus,
  // et un bandeau posé directement dans l'écran toucherait sinon les bords.
  banner: {
    borderRadius: 4,
    padding: 12,
    borderWidth: 1,
    marginHorizontal: 20,
    marginTop: 12,
  },
});

export const bannerStyle = (kind: 'error' | 'warn' | 'ok') => ({
  backgroundColor: { error: '#2A1C19', warn: '#2A2418', ok: '#242A15' }[kind],
  borderColor: { error: colors.error, warn: colors.warn, ok: colors.ok }[kind],
});
