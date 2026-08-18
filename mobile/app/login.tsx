/** Connexion : adresse du serveur et mot de passe, échangés contre un jeton. */

import { router } from 'expo-router';
import { useState } from 'react';
import { Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { ErrorBanner } from '@/components/Feedback';
import * as api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors, styles } from '@/lib/theme';

export default function LoginScreen() {
  const { baseUrl: known, signIn } = useAuth();
  const [baseUrl, setBaseUrl] = useState(known);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const url = baseUrl.trim().replace(/\/+$/, '');
      api.configure({ baseUrl: url });
      const token = await api.login(password, `${Platform.OS} ${Platform.Version}`);
      await signIn(url, token);
      setPassword('');
      // Navigation impérative depuis un gestionnaire d'événement : le
      // navigateur est monté depuis longtemps, c'est sans risque.
      router.replace('/dashboard');
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = baseUrl.trim().length > 0 && password.length > 0 && !busy;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.card}>
        <Text style={styles.title}>Casier</Text>
        <Text style={styles.muted}>
          Le mot de passe est celui du panel web (WEB_PASSWORD). L'app le change
          une fois contre un jeton, conservé dans le stockage sécurisé du
          téléphone.
        </Text>

        <Text style={styles.heading}>Serveur</Text>
        <TextInput
          style={styles.input}
          value={baseUrl}
          onChangeText={setBaseUrl}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          placeholder="https://192.0.2.10:8000"
          placeholderTextColor={colors.faint}
        />

        <Text style={styles.heading}>Mot de passe</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
          onSubmitEditing={() => canSubmit && submit()}
          returnKeyType="go"
        />

        <ErrorBanner error={error} />

        <Pressable
          style={[styles.button, !canSubmit && styles.disabled]}
          disabled={!canSubmit}
          onPress={submit}
        >
          <Text style={styles.buttonText}>{busy ? 'Connexion…' : 'Se connecter'}</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}
