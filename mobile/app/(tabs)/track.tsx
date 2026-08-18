/**
 * Titre à l'unité — l'écran qui justifie une app native.
 *
 * Depuis Spotify : « Partager → Casier ». Le lien arrive par l'intention
 * Android, l'écran se remplit et lance le classement sans autre geste.
 */

import { useShareIntent } from 'expo-share-intent';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { ErrorBanner, Loading } from '@/components/Feedback';
import { SquareSwitch } from '@/components/SquareSwitch';
import { Swatch } from '@/components/Swatch';
import * as api from '@/lib/api';
import { colors, styles } from '@/lib/theme';

/** Couleur du verdict, pour repérer d'un coup d'œil ce qui a échoué. */
function statusColor(status: string): string {
  if (status.startsWith('échec')) return colors.error;
  if (status === 'ajouté') return colors.accent;
  if (status === 'playlist absente du compte') return colors.warn;
  return colors.muted;
}

export default function TrackScreen() {
  const [link, setLink] = useState('');
  const [add, setAdd] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<api.ClassifyResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();
  // Le classement est asynchrone : sans cette garde, un rendu intermédiaire
  // relancerait la requête sur le même partage.
  const handled = useRef<string | null>(null);

  const classify = useCallback(
    async (target: string, withAdd: boolean) => {
      setBusy(true);
      setError(null);
      setResult(null);
      try {
        setResult(await api.classifyTrack(target, withAdd));
      } catch (err) {
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    []
  );

  useEffect(() => {
    const shared = shareIntent?.webUrl ?? shareIntent?.text ?? '';
    if (!hasShareIntent || !shared || handled.current === shared) return;

    handled.current = shared;
    setLink(shared);
    void classify(shared, add).finally(resetShareIntent);
  }, [hasShareIntent, shareIntent, add, classify, resetShareIntent]);

  const canSubmit = link.trim().length > 0 && !busy;
  const casiers = result?.rows.filter((row) => row.key !== null) ?? [];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={[styles.card, { borderTopWidth: 0 }]}>
        <Text style={styles.title}>Classer un titre</Text>
        <Text style={styles.label}>
          Colle un lien, ou partage un titre depuis Spotify vers Casier
        </Text>

        <TextInput
          style={styles.input}
          value={link}
          onChangeText={setLink}
          placeholder="https://open.spotify.com/track/…"
          placeholderTextColor={colors.faint}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.text}>Ajouter réellement</Text>
            <Text style={styles.muted}>
              Range le titre dans les playlists existantes et l'ajoute aux likés.
            </Text>
          </View>
          <SquareSwitch value={add} onValueChange={setAdd} disabled={busy} />
        </View>

        <Pressable
          style={[styles.button, !canSubmit && styles.disabled]}
          disabled={!canSubmit}
          onPress={() => classify(link.trim(), add)}
        >
          <Text style={styles.buttonText}>{busy ? 'Classement…' : 'Classer'}</Text>
        </Pressable>
      </View>

      {busy && <Loading label="Claude analyse le titre — jusqu'à une minute." />}

      <ErrorBanner error={error} onRetry={() => classify(link.trim(), add)} />

      {result && (
        <View style={styles.card}>
          <Text style={styles.heading}>{result.track.title}</Text>
          <Text style={styles.label}>
            {result.track.artists.join(', ')} · {result.track.release_date?.slice(0, 4)} ·{' '}
            {casiers.length} casiers
          </Text>

          {result.rows.map((row, index) => (
            <View key={index} style={styles.listRow}>
              {/* « Titres likés » n'est pas un casier : pas de carré, mais un
                  retrait de même largeur pour que les noms restent alignés. */}
              {row.key ? <Swatch keyName={row.key} /> : <View style={{ width: 12 }} />}
              <Text style={[styles.text, { flex: 1 }]} numberOfLines={1}>
                {row.name}
              </Text>
              <Text style={[styles.chipText, { color: statusColor(row.status) }]}>
                {row.status}
              </Text>
            </View>
          ))}

          {!add && (
            <Text style={styles.muted}>
              Rien n'a été modifié — active « Ajouter réellement » pour appliquer.
            </Text>
          )}
        </View>
      )}
    </ScrollView>
  );
}
