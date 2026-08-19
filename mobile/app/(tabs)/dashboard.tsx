/** Casier : état du serveur, action principale, tâches secondaires. */

import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Empty, ErrorBanner, Loading } from '@/components/Feedback';
import { Swatch } from '@/components/Swatch';
import * as api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useI18n, type Traduire } from '@/lib/i18n';
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
function estimation(likedCount: number, t: Traduire): string {
  const lots = Math.ceil(likedCount / BATCH_SIZE);
  if (lots === 0) return t('accueil.rien_a_classer');
  const vagues = 1 + Math.ceil((lots - 1) / MAX_CONCURRENCY);
  const secondes = vagues * SECONDES_PAR_LOT;
  return secondes < 90 ? `~${secondes} s` : `~${Math.round(secondes / 60)} min`;
}

const ACTION_PRINCIPALE: api.JobAction = 'sort';

const SECONDAIRES: api.JobAction[] = [
  'fetch',
  'import',
  'sync-likes',
  'reference',
  'doctor',
];

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
  const { t } = useI18n();
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

  if (!status && !error) return <Loading label={t('commun.lecture_etat')} />;

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
              <Text style={styles.title}>{t('onglet.casier')}</Text>
              <Text style={[styles.label, { color: colors.faint }]}>v{status.version}</Text>
            </View>
            <View style={{ flexDirection: 'row', marginTop: 4 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={styles.metric}>{status.liked_count}</Text>
                <Text style={styles.label}>{t('accueil.titres_en_cache')}</Text>
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
                <Text style={styles.label}>{t('accueil.casiers')}</Text>
              </View>
            </View>

            {/* 2 — Puces d'état */}
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <Chip
                on={status.spotify_ready}
                label={t(status.spotify_ready ? 'accueil.compte_lie' : 'accueil.compte_non_lie')}
              />
              <Chip
                on={status.anthropic_ready}
                label={t(status.anthropic_ready ? 'accueil.cle_ok' : 'accueil.cle_absente')}
              />
            </View>
          </View>

          {!status.spotify_ready && (
            <View style={[styles.banner, bannerStyle('warn')]}>
              <Text style={styles.text}>{t('accueil.avertissement_spotify')}</Text>
            </View>
          )}

          {/* 3 — Action principale, une seule par écran */}
          <View style={styles.card}>
            {status.job ? (
              <Pressable
                style={styles.button}
                onPress={() => router.push({ pathname: '/job', params: { id: status.job!.id } })}
              >
                <Text style={styles.buttonText}>{t('accueil.suivre_job', { name: status.job.name })}</Text>
              </Pressable>
            ) : (
              <>
                <Pressable
                  style={[styles.button, busy && styles.disabled]}
                  disabled={busy}
                  onPress={() => launch(ACTION_PRINCIPALE)}
                >
                  <Text style={styles.buttonText}>{t('accueil.trier')}</Text>
                </Pressable>
                <Text style={[styles.label, { textAlign: 'center' }]}>
                  {t('accueil.estimation', {
                    count: status.liked_count,
                    duree: estimation(status.liked_count, t),
                  })}
                </Text>
              </>
            )}
          </View>

          {/* 4 — Derniers casiers remplis */}
          {casiers.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.label}>{t('accueil.casiers_remplis')}</Text>
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
            <Text style={styles.label}>{t('accueil.autres_taches')}</Text>
            {SECONDAIRES.map((action) => (
              <Pressable
                key={action}
                style={[styles.listRow, busy && styles.disabled]}
                disabled={busy}
                onPress={() => launch(action)}
              >
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={{ color: colors.text, fontSize: 16 }}>{t(`tache.${action}`)}</Text>
                  <Text style={styles.label}>{t(`tache.${action}.aide`)}</Text>
                </View>
                <Text style={{ color: colors.faint, fontSize: 16 }}>▸</Text>
              </Pressable>
            ))}
          </View>

          {/* 6 — Déconnexion */}
          <View style={styles.card}>
            <Pressable style={styles.listRow} onPress={disconnect}>
              <Text style={[styles.text, { flex: 1, color: colors.muted }]}>{t('accueil.deconnexion')}</Text>
              <Text style={{ color: colors.faint, fontSize: 16 }}>▸</Text>
            </Pressable>
          </View>
        </>
      )}

      {!status && error ? <Empty>{t('accueil.etat_illisible')}</Empty> : null}
    </ScrollView>
  );
}
