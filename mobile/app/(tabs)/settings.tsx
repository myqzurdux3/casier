/**
 * Réglages : tolérance, préfixe, visibilité, et édition de la taxonomie.
 *
 * L'API accepte des mises à jour partielles : chaque enregistrement n'envoie
 * que ce qui a changé, ce qui évite qu'un écran mobile écrase une catégorie
 * ajoutée entre-temps depuis le panel.
 */

import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';

import { ErrorBanner, Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import { colors, styles } from '@/lib/theme';

const GROUPS: Record<string, string> = {
  moods: 'Moods',
  genres: 'Genres',
  specials: 'Catégories spéciales',
};

export default function SettingsScreen() {
  const [settings, setSettings] = useState<api.Settings | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSettings(await api.getSettings());
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

  async function patch(changes: Partial<api.Settings>) {
    setBusy(true);
    try {
      setSettings(await api.putSettings(changes));
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function removeCategory(group: string, key: string, name: string) {
    if (!settings) return;
    Alert.alert('Supprimer cette catégorie ?', `« ${name} » ne sera plus proposée.`, [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer',
        style: 'destructive',
        onPress: () => {
          const categories = {
            ...settings.categories,
            [group]: Object.fromEntries(
              Object.entries(settings.categories[group]).filter(([k]) => k !== key)
            ),
          };
          void patch({ categories });
        },
      },
    ]);
  }

  if (!settings) {
    return error ? (
      <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
        <ErrorBanner error={error} onRetry={refresh} />
      </ScrollView>
    ) : (
      <Loading />
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor="#fff" />}
    >
      <ErrorBanner error={error} onRetry={refresh} />

      <View style={styles.card}>
        <Text style={styles.title}>Tolérance</Text>
        <Text style={styles.muted}>
          « Large » remplit davantage les playlists en acceptant les
          correspondances raisonnables. « Stricte » ne retient que l'évident.
        </Text>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          {(['large', 'stricte'] as const).map((value) => (
            <Pressable
              key={value}
              style={[
                styles.buttonGhost,
                { flex: 1 },
                settings.tolerance === value && { borderColor: colors.accent },
                busy && styles.disabled,
              ]}
              disabled={busy}
              onPress={() => patch({ tolerance: value })}
            >
              <Text
                style={[
                  styles.buttonGhostText,
                  settings.tolerance === value && { color: colors.accent },
                ]}
              >
                {value === 'large' ? 'Large' : 'Stricte'}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>Playlists créées</Text>

        <Text style={styles.heading}>Préfixe</Text>
        <TextInput
          style={styles.input}
          defaultValue={settings.playlist_prefix}
          placeholder="ex. « 🎵 »"
          placeholderTextColor="#6b6b70"
          onEndEditing={(event) => patch({ playlist_prefix: event.nativeEvent.text })}
        />

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.text}>Publiques</Text>
            <Text style={styles.muted}>Privées par défaut.</Text>
          </View>
          <Switch
            value={settings.playlist_public}
            disabled={busy}
            onValueChange={(value) => patch({ playlist_public: value })}
            trackColor={{ true: colors.accent, false: colors.border }}
          />
        </View>
      </View>

      {Object.entries(GROUPS).map(([group, label]) => {
        const entries = Object.entries(settings.categories[group] ?? {});
        const open = openGroup === group;
        return (
          <View key={group} style={styles.card}>
            <Pressable style={styles.row} onPress={() => setOpenGroup(open ? null : group)}>
              <Text style={[styles.heading, { flex: 1 }]}>{label}</Text>
              <Text style={styles.muted}>
                {entries.length} {open ? '▾' : '▸'}
              </Text>
            </Pressable>

            {open &&
              entries.map(([key, entry]) => (
                <Pressable
                  key={key}
                  style={{ gap: 2, paddingVertical: 6 }}
                  onLongPress={() => removeCategory(group, key, entry.name)}
                >
                  <Text style={styles.text}>{entry.name}</Text>
                  <Text style={styles.muted}>{entry.description}</Text>
                </Pressable>
              ))}

            {open && (
              <Text style={styles.muted}>
                Appui long sur une catégorie pour la supprimer. La création et la
                réécriture des descriptions se font depuis le panel web, plus
                confortable au clavier.
              </Text>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}
