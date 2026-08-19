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
  Text,
  TextInput,
  View,
} from 'react-native';

import { ErrorBanner, Loading } from '@/components/Feedback';
import { SquareSwitch } from '@/components/SquareSwitch';
import { Swatch } from '@/components/Swatch';
import { useI18n, type LangPref } from '@/lib/i18n';
import * as api from '@/lib/api';
import { colors, styles } from '@/lib/theme';

const GROUPS = ['moods', 'genres', 'specials'] as const;
const TOLERANCES = ['large', 'stricte'] as const;
const LANGUES: LangPref[] = ['auto', 'fr', 'en'];

export default function SettingsScreen() {
  const { t, pref, setPref } = useI18n();
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
    Alert.alert(
      t('reglages.supprimer_categorie'),
      t('reglages.ne_sera_plus_proposee', { name }),
      [
      { text: t('commun.annuler'), style: 'cancel' },
      {
        text: t('reglages.supprimer'),
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
      ]
    );
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
      refreshControl={
        <RefreshControl refreshing={false} onRefresh={refresh} tintColor={colors.text} />
      }
    >
      <ErrorBanner error={error} onRetry={refresh} />

      <View style={[styles.card, { borderTopWidth: 0 }]}>
        <Text style={styles.title}>{t('reglages.langue')}</Text>
        <Text style={styles.muted}>{t('reglages.langue_aide')}</Text>
        {/* Purement local : aucun appel réseau, le serveur apprend la langue
            par l'en-tête Accept-Language de la requête suivante. */}
        <View
          style={{
            flexDirection: 'row',
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 4,
            overflow: 'hidden',
          }}
        >
          {LANGUES.map((valeur) => {
            const actif = pref === valeur;
            return (
              <Pressable
                key={valeur}
                style={{
                  flex: 1,
                  paddingVertical: 13,
                  alignItems: 'center',
                  backgroundColor: actif ? colors.accent : 'transparent',
                }}
                onPress={() => setPref(valeur)}
              >
                <Text
                  style={{
                    color: actif ? colors.onAccent : colors.muted,
                    fontSize: 15,
                    fontWeight: actif ? '700' : '600',
                  }}
                >
                  {t(`reglages.langue.${valeur}`)}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>{t('reglages.tolerance')}</Text>
        <Text style={styles.muted}>{t('reglages.tolerance_aide')}</Text>
        {/* Un seul cadre coupé en deux, et non deux boutons voisins : les deux
            moitiés sont exclusives, la forme doit le dire. */}
        <View
          style={{
            flexDirection: 'row',
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 4,
            overflow: 'hidden',
          }}
        >
          {TOLERANCES.map((value) => {
            const actif = settings.tolerance === value;
            return (
              <Pressable
                key={value}
                style={[
                  {
                    flex: 1,
                    paddingVertical: 13,
                    alignItems: 'center',
                    backgroundColor: actif ? colors.accent : 'transparent',
                  },
                  busy && styles.disabled,
                ]}
                disabled={busy}
                onPress={() => patch({ tolerance: value })}
              >
                <Text
                  style={{
                    color: actif ? colors.onAccent : colors.muted,
                    fontSize: 15,
                    fontWeight: actif ? '700' : '600',
                  }}
                >
                  {t(`reglages.${value}`)}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>{t('reglages.playlists')}</Text>

        <Text style={styles.label}>{t('reglages.prefixe')}</Text>
        <TextInput
          style={styles.input}
          defaultValue={settings.playlist_prefix}
          placeholder={t('reglages.prefixe_exemple')}
          placeholderTextColor={colors.faint}
          onEndEditing={(event) => patch({ playlist_prefix: event.nativeEvent.text })}
        />

        <View style={styles.listRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.text}>{t('reglages.publiques')}</Text>
            <Text style={styles.muted}>{t('reglages.publiques_aide')}</Text>
          </View>
          <SquareSwitch
            value={settings.playlist_public}
            disabled={busy}
            onValueChange={(value) => patch({ playlist_public: value })}
          />
        </View>
      </View>

      {GROUPS.map((group) => {
        const entries = Object.entries(settings.categories[group] ?? {});
        const open = openGroup === group;
        return (
          <View key={group} style={styles.card}>
            <Pressable style={styles.row} onPress={() => setOpenGroup(open ? null : group)}>
              <Text style={[styles.heading, { flex: 1 }]}>{t(`reglages.${group}`)}</Text>
              <Text style={[styles.label, { color: colors.muted }]}>
                {entries.length} {open ? '▾' : '▸'}
              </Text>
            </Pressable>

            {/* Une seule fois dans l'en-tête : répété sous chaque catégorie,
                c'était du bruit. */}
            {open && (
              <Text style={styles.label}>{t('reglages.groupe_aide')}</Text>
            )}

            {open &&
              entries.map(([key, entry]) => (
                <Pressable
                  key={key}
                  style={styles.listRow}
                  onLongPress={() => removeCategory(group, key, entry.name)}
                >
                  {/* Aligné sur la première ligne de texte et non centré : la
                      description peut courir sur deux lignes. */}
                  <View style={{ paddingTop: 4, alignSelf: 'flex-start' }}>
                    <Swatch keyName={key} />
                  </View>
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text style={styles.text}>{entry.name}</Text>
                    <Text style={styles.muted}>{entry.description}</Text>
                  </View>
                </Pressable>
              ))}
          </View>
        );
      })}
    </ScrollView>
  );
}
