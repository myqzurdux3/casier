/**
 * Journal d'un job, rafraîchi tant qu'il tourne.
 *
 * Le curseur `since` ne redemande que les lignes nouvelles : un tri de 300
 * titres produit des centaines de lignes qu'il serait absurde de retélécharger
 * toutes les 1,5 s.
 */

import { useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { ErrorBanner, Loading } from '@/components/Feedback';
import * as api from '@/lib/api';
import { bannerStyle, styles } from '@/lib/theme';

const POLL_MS = 1500;

export default function JobScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [lines, setLines] = useState<string[]>([]);
  const [job, setJob] = useState<api.JobSnapshot | null>(null);
  const [error, setError] = useState<unknown>(null);
  const cursor = useRef(0);
  const scroller = useRef<ScrollView>(null);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const snapshot = await api.getJob(id, cursor.current);
        if (!alive) return;

        if (snapshot.lines.length) {
          cursor.current = snapshot.next;
          setLines((previous) => [...previous, ...snapshot.lines]);
        }
        setJob(snapshot);
        setError(null);

        // On s'arrête net à la fin : le statut n'est publié qu'après le journal
        // complet, donc plus rien ne peut arriver ensuite.
        if (snapshot.status === 'running') timer = setTimeout(poll, POLL_MS);
      } catch (err) {
        if (!alive) return;
        setError(err);
        timer = setTimeout(poll, POLL_MS * 4);
      }
    }

    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [id]);

  if (!job && !error) return <Loading label="Ouverture du journal…" />;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      ref={scroller}
      onContentSizeChange={() => scroller.current?.scrollToEnd({ animated: true })}
    >
      {job && (
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.title}>{job.name}</Text>
            <Text
              style={[
                styles.muted,
                job.status === 'error' && { color: '#ff453a' },
                job.status === 'done' && { color: '#30d158' },
              ]}
            >
              {{ running: 'en cours…', done: 'terminé', error: 'échec' }[job.status]}
            </Text>
          </View>
        </View>
      )}

      <ErrorBanner error={error} />

      {job?.status === 'error' && job.error && (
        <View style={[styles.banner, bannerStyle('error')]}>
          <Text style={styles.text}>{job.error}</Text>
        </View>
      )}

      <View style={styles.card}>
        {lines.length === 0 ? (
          <Text style={styles.muted}>Pas encore de sortie.</Text>
        ) : (
          lines.map((line, index) => (
            <Text key={index} style={styles.mono}>
              {line || ' '}
            </Text>
          ))
        )}
      </View>
    </ScrollView>
  );
}
