/** Tri : casiers calculés, parcours, retrait d'un titre mal classé. */

import { useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Alert, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Empty, ErrorBanner, Loading } from '@/components/Feedback';
import { Swatch } from '@/components/Swatch';
import * as api from '@/lib/api';
import { categoryColor } from '@/lib/categoryColor';
import { useI18n } from '@/lib/i18n';
import { colors, styles } from '@/lib/theme';

/** Au-delà, la rangée mangerait la largeur du titre. */
const MAX_CARRES = 4;

/**
 * Rangée des autres casiers d'un titre.
 *
 * Un titre appartient souvent à quatre ou cinq casiers — mood, genre,
 * décennie. Les montrer sur sa ligne évite d'avoir à parcourir tous les
 * casiers pour reconstituer son classement.
 */
function AutresCasiers({ keys }: { keys: string[] }) {
  if (keys.length === 0) return null;
  const montres = keys.slice(0, MAX_CARRES);
  const reste = keys.length - montres.length;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
      {montres.map((key) => (
        <Swatch key={key} keyName={key} size={8} />
      ))}
      {reste > 0 && (
        <Text style={[styles.label, { color: colors.faint, letterSpacing: 0 }]}>+{reste}</Text>
      )}
    </View>
  );
}

export default function ResultScreen() {
  const { t } = useI18n();
  const [document, setDocument] = useState<api.ResultDocument | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [filtre, setFiltre] = useState<string | null>(null);
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

  /** Titre -> casiers qui le contiennent, pour la rangée de carrés. */
  const casiersParTitre = useMemo(() => {
    const table: Record<string, string[]> = {};
    for (const playlist of document?.playlists ?? []) {
      for (const trackId of playlist.track_ids) {
        (table[trackId] ??= []).push(playlist.key);
      }
    }
    return table;
  }, [document]);

  function confirmRemove(key: string, trackId: string, label: string) {
    Alert.alert(t('tri.retirer_titre'), label, [
      { text: t('commun.annuler'), style: 'cancel' },
      {
        text: t('tri.retirer'),
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
  const visibles = document
    ? document.playlists.filter((p) => filtre === null || p.key === filtre)
    : [];

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={false} onRefresh={refresh} tintColor={colors.text} />
      }
    >
      {noResult ? (
        <Empty>{t('tri.vide')}</Empty>
      ) : (
        <ErrorBanner error={error} onRetry={refresh} />
      )}

      {document && (
        <>
          <View style={[styles.card, { borderTopWidth: 0 }]}>
            <View style={styles.row}>
              <Text style={styles.title}>{t('tri.titre')}</Text>
              <Text style={[styles.mono, { color: colors.muted }]}>
                {t('tri.comptes', {
                  casiers: document.playlists.length,
                  titres: document.track_count,
                })}
              </Text>
            </View>
            <Text style={styles.muted}>{t('tri.aide')}</Text>
          </View>

          {/* Puces de filtre : la puce active prend la teinte de son casier. */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 20, paddingVertical: 12, gap: 8 }}
            style={{ borderTopWidth: 1, borderTopColor: colors.border }}
          >
            {document.playlists.map((playlist) => {
              const actif = filtre === playlist.key;
              const teinte = categoryColor(playlist.key);
              return (
                <Pressable
                  key={playlist.key}
                  onPress={() => setFiltre(actif ? null : playlist.key)}
                  style={[
                    styles.chip,
                    {
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: 6,
                      borderColor: actif ? teinte : colors.border,
                    },
                  ]}
                >
                  <Swatch keyName={playlist.key} size={8} />
                  <Text style={[styles.chipText, { color: actif ? teinte : colors.muted }]}>
                    {playlist.name}
                  </Text>
                  <Text style={[styles.chipText, { color: colors.faint }]}>
                    {playlist.track_ids.length}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>

          {visibles.map((playlist) => {
            const open = openKey === playlist.key;
            return (
              <View key={playlist.key} style={styles.card}>
                <Pressable
                  style={styles.row}
                  onPress={() => setOpenKey(open ? null : playlist.key)}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                    <Swatch keyName={playlist.key} />
                    <Text
                      style={[
                        styles.heading,
                        {
                          borderBottomWidth: 3,
                          borderBottomColor: categoryColor(playlist.key),
                        },
                      ]}
                      numberOfLines={1}
                    >
                      {playlist.name}
                    </Text>
                  </View>
                  <Text style={[styles.label, { color: colors.muted }]}>
                    {t('tri.n_titres', { n: playlist.track_ids.length })} {open ? '▾' : '▸'}
                  </Text>
                </Pressable>

                {open &&
                  playlist.track_ids.map((trackId, index) => {
                    const track = document.tracks?.[trackId];
                    const titre = track?.title ?? trackId;
                    const artistes = track?.artists.join(', ') ?? '';
                    const autres = (casiersParTitre[trackId] ?? []).filter(
                      (key) => key !== playlist.key
                    );
                    return (
                      <Pressable
                        key={trackId}
                        style={styles.listRow}
                        onLongPress={() =>
                          confirmRemove(
                            playlist.key,
                            trackId,
                            artistes ? `${titre} — ${artistes}` : titre
                          )
                        }
                      >
                        <Text
                          style={[styles.mono, { color: colors.faint, width: 20 }]}
                        >
                          {String(index + 1).padStart(2, '0')}
                        </Text>
                        <View style={{ flex: 1, gap: 2 }}>
                          <Text style={styles.text} numberOfLines={1}>
                            {titre}
                          </Text>
                          {artistes ? (
                            <Text style={styles.muted} numberOfLines={1}>
                              {artistes}
                            </Text>
                          ) : null}
                        </View>
                        <AutresCasiers keys={autres} />
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
