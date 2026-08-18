/** Casier : état du serveur, action principale, tâches secondaires. */

import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Empty, ErrorBanner, Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { categoryColor } from '@/lib/categoryColor';
import { bannerStyle, colors, styles } from '@/lib/theme';

/**
 * Copies de `spotify_sort/config.py`, uniquement pour estimer la durée d'un tri
 * sans ajouter d'appel réseau. Une dérive entre les deux fausse l'estimation
 * affichée, jamais le classement lui-même — le serveur reste seul maître.
 */
const BATCH_SIZE = 40;
const MAX_CONCURRENCY = 6;
/** Ordre de grandeur d'un lot classé par Claude. Volontairement grossier. */
const SECONDES_PAR_LOT = 25;

/**
 * Durée approximative d'un tri.
 *
 * Le premier lot part seul — il amorce le cache de prompt que les suivants
 * relisent —, puis les autres passent par vagues de MAX_CONCURRENCY.
 */
function estimation(likedCount: number): string {
  const lots = Math.ceil(likedCount / BATCH_SIZE);
  if (lots === 0) return 'rien à classer';
  const vagues = 1 + Math.ceil((lots - 1) / MAX_CONCURRENCY);
  const secondes = vagues * SECONDES_PAR_LOT;
  return secondes < 90 ? `~${secondes} s` : `~${Math.round(secondes / 60)} min`;
}

const ACTION_PRINCIPALE: api.JobAction = 'sort';

const SECONDAIRES: { action: api.JobAction; label: string; hint: string }[] = [
  { action: 'fetch', label: 'Récupérer les likés', hint: 'Relit la bibliothèque Spotify.' },
  { action: 'import', label: 'Importer', hint: 'Crée les playlists sur le compte.' },
  { action: 'sync-likes', label: 'Rattraper les likes', hint: 'Like les titres des playlists.' },
  { action: 'reference', label: 'Playlists de référence', hint: 'Relit tes exemples.' },
  { action: 'doctor', label: 'Diagnostic', hint: 'Vérifie scopes et endpoints.' },
];

/** Carré de couleur d'un casier. */
function Swatch({ keyName, size = 12 }: { keyName: string; size?: number }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        backgroundColor: categoryColor(keyName),
        flexShrink: 0,
      }}
    />
  );
}

function Chip({ on, label }: { on: boolean; label: string }) {
  return (
    <View
      style={[
        styles.chip,
        on
          ? { backgroundColor: colors.accent, borderColor: colors.accent }
          : { backgroundColor: 'transparent', borderColor: colors.warn },
      ]}
    >
      <Text style={[styles.chipText, { color: on ? colors.onAccent : colors.warn }]}>
        {label}
      </Text>
    </View>
  );
}

export default function DashboardScreen() {
  const { signOut } = useAuth();
  const [status, setStatus] = useState<api.Status | null>(null);
  const [result, setResult] = useState<api.ResultDocument | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.getStatus());
      setError(null);
    } catch (err) {
      setError(err);
      return;
    }
    // Les derniers casiers sont un agrément : leur absence n'est pas une erreur
    // d'écran, elle fait juste disparaître la section.
    try {
      setResult(await api.getResult());
    } catch {
      setResult(null);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  async function launch(action: api.JobAction) {
    setBusy(true);
    try {
      const { job_id } = await api.startJob(action);
      router.push({ pathname: '/job', params: { id: job_id } });
    } catch (err) {
      // Un job déjà en cours n'est pas un échec : on va le regarder.
      if (err instanceof api.ApiError && err.code === 'job_busy' && err.jobId) {
        router.push({ pathname: '/job', params: { id: err.jobId } });
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    try {
      await api.logout();
    } finally {
      await signOut();
      router.replace('/login');
    }
  }

  if (!status && !error) return <Loading label="Lecture de l'état…" />;

  const casiers = result
    ? [...result.playlists].sort((a, b) => b.track_ids.length - a.track_ids.length).slice(0, 4)
    : [];

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={false} onRefresh={refresh} tintColor={colors.text} />
      }
    >
      <ErrorBanner error={error} onRetry={refresh} />

      {status && (
        <>
          {/* 1 — Métriques */}
          <View style={[styles.card, { borderTopWidth: 0 }]}>
            <View style={styles.row}>
              <Text style={styles.title}>Casier</Text>
              <Text style={[styles.label, { color: colors.faint }]}>v{status.version}</Text>
            </View>
            <View style={{ flexDirection: 'row', marginTop: 4 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={styles.metric}>{status.liked_count}</Text>
                <Text style={styles.label}>Titres en cache</Text>
              </View>
              <View
                style={{
                  flex: 1,
                  gap: 2,
                  paddingLeft: 20,
                  borderLeftWidth: 1,
                  borderLeftColor: colors.border,
                }}
              >
                <Text style={styles.metric}>
                  {status.has_result ? status.playlist_count : '—'}
                </Text>
                <Text style={styles.label}>Casiers</Text>
              </View>
            </View>

            {/* 2 — Puces d'état */}
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <Chip on={status.spotify_ready} label={status.spotify_ready ? 'Compte lié' : 'Compte non lié'} />
              <Chip on={status.anthropic_ready} label={status.anthropic_ready ? 'Clé Claude OK' : 'Clé Claude absente'} />
            </View>
          </View>

          {!status.spotify_ready && (
            <View style={[styles.banner, bannerStyle('warn')]}>
              <Text style={styles.text}>
                Connecte ton compte Spotify depuis le panel web : la liaison OAuth
                passe par un navigateur.
              </Text>
            </View>
          )}

          {/* 3 — Action principale, une seule par écran */}
          <View style={styles.card}>
            {status.job ? (
              <Pressable
                style={styles.button}
                onPress={() => router.push({ pathname: '/job', params: { id: status.job!.id } })}
              >
                <Text style={styles.buttonText}>Suivre « {status.job.name} »</Text>
              </Pressable>
            ) : (
              <>
                <Pressable
                  style={[styles.button, busy && styles.disabled]}
                  disabled={busy}
                  onPress={() => launch(ACTION_PRINCIPALE)}
                >
                  <Text style={styles.buttonText}>Trier</Text>
                </Pressable>
                <Text style={[styles.label, { textAlign: 'center' }]}>
                  {status.liked_count} titres · {estimation(status.liked_count)}
                </Text>
              </>
            )}
          </View>

          {/* 4 — Derniers casiers remplis */}
          {casiers.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.label}>Casiers les plus remplis</Text>
              {casiers.map((casier) => (
                <Pressable
                  key={casier.key}
                  style={styles.listRow}
                  onPress={() => router.navigate('/result')}
                >
                  <Swatch keyName={casier.key} />
                  <Text style={[styles.text, { flex: 1 }]} numberOfLines={1}>
                    {casier.name}
                  </Text>
                  <Text style={[styles.mono, { color: colors.muted }]}>
                    {casier.track_ids.length}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}

          {/* 5 — Tâches secondaires */}
          <View style={styles.card}>
            <Text style={styles.label}>Autres tâches</Text>
            {SECONDAIRES.map(({ action, label, hint }) => (
              <Pressable
                key={action}
                style={[styles.listRow, busy && styles.disabled]}
                disabled={busy}
                onPress={() => launch(action)}
              >
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={{ color: colors.text, fontSize: 16 }}>{label}</Text>
                  <Text style={styles.label}>{hint}</Text>
                </View>
                <Text style={{ color: colors.faint, fontSize: 16 }}>▸</Text>
              </Pressable>
            ))}
          </View>

          {/* 6 — Déconnexion */}
          <View style={styles.card}>
            <Pressable style={styles.listRow} onPress={disconnect}>
              <Text style={[styles.text, { flex: 1, color: colors.muted }]}>Déconnexion</Text>
              <Text style={{ color: colors.faint, fontSize: 16 }}>▸</Text>
            </Pressable>
          </View>
        </>
      )}

      {!status && error ? <Empty>Impossible de lire l'état du serveur.</Empty> : null}
    </ScrollView>
  );
}
