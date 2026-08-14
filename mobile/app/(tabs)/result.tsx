/** Playlists calculées : parcours, détail, retrait d'un titre mal classé. */

import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Empty, ErrorBanner, Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import { colors, styles } from '@/lib/theme';

export default function ResultScreen() {
  const [document, setDocument] = useState<api.ResultDocument | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setDocument(await api.getResult());
      setError(null);
    } catch (err) {
      setDocument(null);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  function confirmRemove(key: string, trackId: string, label: string) {
    Alert.alert('Retirer ce titre ?', label, [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Retirer',
        style: 'destructive',
        onPress: async () => {
          try {
            setDocument(await api.removeFromResult(key, trackId));
          } catch (err) {
            setError(err);
          }
        },
      },
    ]);
  }

  if (loading) return <Loading />;

  const noResult = error instanceof api.ApiError && error.code === 'no_result';

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor="#fff" />}
    >
      {noResult ? (
        <Empty>Aucun classement enregistré. Lance un tri depuis le tableau de bord.</Empty>
      ) : (
        <ErrorBanner error={error} onRetry={refresh} />
      )}

      {document && (
        <>
          <View style={styles.card}>
            <Text style={styles.title}>
              {document.playlists.length} playlists · {document.track_count} titres
            </Text>
            <Text style={styles.muted}>
              Le retrait ne touche que le classement local. Relance un import pour
              répercuter sur Spotify.
            </Text>
          </View>

          {document.playlists.map((playlist) => {
            const open = openKey === playlist.key;
            return (
              <View key={playlist.key} style={styles.card}>
                <Pressable
                  style={styles.row}
                  onPress={() => setOpenKey(open ? null : playlist.key)}
                >
                  <Text style={[styles.heading, { flex: 1 }]}>{playlist.name}</Text>
                  <Text style={styles.muted}>
                    {playlist.track_ids.length} {open ? '▾' : '▸'}
                  </Text>
                </Pressable>

                {open &&
                  playlist.track_ids.map((trackId) => {
                    const track = document.tracks?.[trackId];
                    const label = track
                      ? `${track.title} — ${track.artists.join(', ')}`
                      : trackId;
                    return (
                      <Pressable
                        key={trackId}
                        style={styles.row}
                        onLongPress={() => confirmRemove(playlist.key, trackId, label)}
                      >
                        <Text style={[styles.text, { flex: 1 }]} numberOfLines={2}>
                          {label}
                        </Text>
                        <Text style={{ color: colors.muted, fontSize: 12 }}>appui long</Text>
                      </Pressable>
                    );
                  })}
              </View>
            );
          })}
        </>
      )}
    </ScrollView>
  );
}
