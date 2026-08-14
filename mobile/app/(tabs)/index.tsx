/** Tableau de bord : état du serveur et lancement des tâches. */

import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Empty, ErrorBanner, Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import * as session from '@/lib/session';
import { bannerStyle, styles } from '@/lib/theme';

const ACTIONS: { action: api.JobAction; label: string; hint: string }[] = [
  { action: 'fetch', label: 'Récupérer les likés', hint: 'Relit la bibliothèque Spotify.' },
  { action: 'sort', label: 'Trier', hint: 'Classe les titres via Claude.' },
  { action: 'import', label: 'Importer', hint: 'Crée les playlists sur le compte.' },
  { action: 'sync-likes', label: 'Rattraper les likes', hint: 'Like les titres des playlists.' },
  { action: 'reference', label: 'Playlists de référence', hint: 'Relit tes exemples.' },
  { action: 'doctor', label: 'Diagnostic', hint: 'Vérifie scopes et endpoints.' },
];

export default function DashboardScreen() {
  const [status, setStatus] = useState<api.Status | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.getStatus());
      setError(null);
    } catch (err) {
      setError(err);
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
      await session.clear();
      router.replace('/login');
    }
  }

  if (!status && !error) return <Loading label="Lecture de l'état…" />;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor="#fff" />}
    >
      <ErrorBanner error={error} onRetry={refresh} />

      {status && (
        <>
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.title}>État</Text>
              <Text style={styles.muted}>v{status.version}</Text>
            </View>
            <Text style={styles.text}>{status.liked_count} titres likés en cache</Text>
            <Text style={styles.text}>
              {status.has_result
                ? `${status.playlist_count} playlists calculées`
                : 'Aucun classement enregistré'}
            </Text>
            <Text style={[styles.text, { color: status.spotify_ready ? '#30d158' : '#ffd60a' }]}>
              {status.spotify_ready ? '✓ Compte Spotify lié' : '✗ Compte Spotify non lié'}
            </Text>
            <Text style={[styles.text, { color: status.anthropic_ready ? '#30d158' : '#ffd60a' }]}>
              {status.anthropic_ready ? '✓ Clé Claude présente' : '✗ Clé Claude absente'}
            </Text>
          </View>

          {!status.spotify_ready && (
            <View style={[styles.banner, bannerStyle('warn')]}>
              <Text style={styles.text}>
                Connecte ton compte Spotify depuis le panel web : la liaison OAuth
                passe par un navigateur.
              </Text>
            </View>
          )}

          {status.job && (
            <Pressable
              style={[styles.card, { borderColor: '#1db954' }]}
              onPress={() => router.push({ pathname: '/job', params: { id: status.job!.id } })}
            >
              <Text style={styles.heading}>« {status.job.name} » en cours</Text>
              <Text style={styles.muted}>Toucher pour suivre la progression.</Text>
            </Pressable>
          )}

          <View style={styles.card}>
            <Text style={styles.title}>Tâches</Text>
            {ACTIONS.map(({ action, label, hint }) => (
              <View key={action} style={{ gap: 4 }}>
                <Pressable
                  style={[styles.buttonGhost, busy && styles.disabled]}
                  disabled={busy}
                  onPress={() => launch(action)}
                >
                  <Text style={styles.buttonGhostText}>{label}</Text>
                </Pressable>
                <Text style={styles.muted}>{hint}</Text>
              </View>
            ))}
          </View>

          <Pressable style={styles.buttonGhost} onPress={disconnect}>
            <Text style={styles.buttonGhostText}>Déconnexion</Text>
          </Pressable>
        </>
      )}

      {!status && error ? <Empty>Impossible de lire l'état du serveur.</Empty> : null}
    </ScrollView>
  );
}
