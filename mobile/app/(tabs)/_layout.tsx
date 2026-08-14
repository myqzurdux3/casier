import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { colors } from '@/lib/theme';

/** Onglets étiquetés par un emoji : évite une dépendance à une fonte d'icônes. */
const icon = (glyph: string) => ({ color }: { color: string }) => (
  <Text style={{ fontSize: 20, color }}>{glyph}</Text>
);

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.card },
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.muted,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Tableau de bord', tabBarLabel: 'Accueil', tabBarIcon: icon('🏠') }}
      />
      <Tabs.Screen
        name="track"
        options={{ title: 'Titre à l\'unité', tabBarLabel: 'Titre', tabBarIcon: icon('🎵') }}
      />
      <Tabs.Screen
        name="result"
        options={{ title: 'Résultat', tabBarLabel: 'Résultat', tabBarIcon: icon('📋') }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: 'Réglages', tabBarLabel: 'Réglages', tabBarIcon: icon('⚙️') }}
      />
    </Tabs>
  );
}
