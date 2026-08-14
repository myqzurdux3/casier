/**
 * Racine de l'app : restaure la session avant d'afficher quoi que ce soit, et
 * renvoie vers la connexion dès qu'un `401` invalide le jeton.
 */

import { Stack, router } from 'expo-router';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import * as session from '@/lib/session';
import { colors, styles } from '@/lib/theme';

export default function RootLayout() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api.configure({
      onUnauthorized: () => {
        void session.clear();
        router.replace('/login');
      },
    });

    session
      .load()
      .then((restored) => {
        if (!restored) router.replace('/login');
      })
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <View style={[styles.screen, { justifyContent: 'center' }]}>
        <Loading />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.card },
          headerTintColor: colors.text,
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="login" options={{ title: 'Connexion' }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="job" options={{ title: 'Progression' }} />
      </Stack>
    </SafeAreaProvider>
  );
}
