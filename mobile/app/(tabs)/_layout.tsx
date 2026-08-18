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
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.chrome, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.muted,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      {/* `dashboard` et non `index` : `app/index.tsx` occupe déjà « / » comme
          écran d'aiguillage. Deux routes pour le même chemin ne se résolvent pas. */}
      <Tabs.Screen
        name="dashboard"
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
