/**
 * Affichage d'erreur commun à tous les écrans.
 *
 * Trois cas distincts plutôt qu'un « une erreur est survenue » : une panne
 * réseau appelle un bouton Réessayer, un certificat refusé appelle une
 * reconstruction de l'APK, une erreur métier appelle son propre message.
 */

import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { ApiError } from '@/lib/api';
import { bannerStyle, colors, styles } from '@/lib/theme';

export function ErrorBanner({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  if (!error) return null;

  const apiError = error instanceof ApiError ? error : null;
  const message = error instanceof Error ? error.message : String(error);
  const kind = apiError?.code === 'spotify_disconnected' ? 'warn' : 'error';

  return (
    <View style={[styles.banner, bannerStyle(kind), { gap: 10 }]}>
      <Text style={styles.text}>{message}</Text>

      {apiError?.code === 'spotify_disconnected' && (
        <Text style={styles.muted}>
          La liaison OAuth passe par un navigateur : ouvre le panel web sur un
          ordinateur et connecte ton compte Spotify depuis le tableau de bord.
        </Text>
      )}

      {apiError?.code === 'certificate' && (
        <Text style={styles.muted}>
          Sur le serveur : ./deploy/make-certs.sh, puis copie secrets/ca.crt dans
          mobile/assets/ et reconstruis l'APK.
        </Text>
      )}

      {onRetry && (apiError?.isTransient ?? true) && (
        <Pressable style={styles.buttonGhost} onPress={onRetry}>
          <Text style={styles.buttonGhostText}>Réessayer</Text>
        </Pressable>
      )}
    </View>
  );
}

export function Loading({ label }: { label?: string }) {
  return (
    <View style={{ padding: 24, alignItems: 'center', gap: 12 }}>
      <ActivityIndicator color={colors.accent} />
      {label ? <Text style={styles.muted}>{label}</Text> : null}
    </View>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.card}>
      <Text style={styles.muted}>{children}</Text>
    </View>
  );
}
