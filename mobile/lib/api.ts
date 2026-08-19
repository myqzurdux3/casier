/**
 * Client de l'API Casier.
 *
 * Seul module qui parle réseau : les écrans appellent des fonctions typées et
 * n'ont ni URL, ni en-tête, ni code HTTP à manipuler. Un `401` invalide la
 * session en mémoire ; l'écran de connexion reprend la main via `onUnauthorized`.
 */

export type ErrorCode =
  | 'bad_token'
  | 'bad_password'
  | 'bad_request'
  | 'too_many_attempts'
  | 'spotify_disconnected'
  | 'classification_failed'
  | 'spotify_denied'
  | 'job_busy'
  | 'no_result'
  | 'not_found'
  | 'internal'
  | 'network'
  | 'certificate';

export class ApiError extends Error {
  code: ErrorCode;
  status: number;
  jobId?: string;

  constructor(code: ErrorCode, message: string, status = 0, jobId?: string) {
    super(message);
    this.code = code;
    this.status = status;
    this.jobId = jobId;
  }

  /** Vrai quand rien n'a pu être tenté — bouton « Réessayer » plutôt que message d'erreur. */
  get isTransient(): boolean {
    return this.code === 'network' || this.status >= 500;
  }
}

export type JobAction =
  | 'fetch'
  | 'reference'
  | 'sort'
  | 'import'
  | 'sync-likes'
  | 'doctor';

export interface JobSnapshot {
  id: string;
  name: string;
  status: 'running' | 'done' | 'error';
  error: string | null;
  lines: string[];
  next: number;
}

export interface Status {
  liked_count: number;
  spotify_ready: boolean;
  anthropic_ready: boolean;
  has_result: boolean;
  playlist_count: number;
  references: Record<string, number>;
  version: string;
  job: JobSnapshot | null;
  actions: Record<JobAction, string>;
}

/** Verdicts renvoyés par le serveur. Des clés stables, pas des phrases : le
 *  client les traduit lui-même, sans aller-retour réseau. */
export type Verdict =
  | 'proposed'
  | 'added'
  | 'already_present'
  | 'playlist_missing'
  | 'failed';

/** Nom réservé de la ligne « Titres likés » : ce n'est pas une playlist du
 *  compte mais la bibliothèque, donc un libellé d'interface à traduire. */
export const LIKED_SONGS = '@liked_songs';

export interface TrackRow {
  /** Clé du casier, d'où vient sa teinte. `null` pour les Titres likés, qui
   *  ne sont pas un casier. */
  key: string | null;
  name: string;
  status: Verdict;
  /** Détail d'un échec, hors du verdict pour rester traduisible. */
  detail: string | null;
}

export interface ClassifyResult {
  track: {
    id: string;
    uri: string;
    title: string;
    artists: string[];
    album: string;
    release_date: string;
  };
  rows: TrackRow[];
}

export interface ResultDocument {
  track_count: number;
  playlists: { key: string; name: string; track_ids: string[] }[];
  tracks: Record<string, { title: string; artists: string[] }>;
}

export interface Settings {
  tolerance: 'large' | 'stricte';
  playlist_prefix: string;
  playlist_public: boolean;
  reference_playlists: Record<string, string>;
  categories: Record<string, Record<string, { name: string; description: string }>>;
}

const TIMEOUT_MS = 30_000;
// Le classement d'un titre appelle Claude : bien plus lent que le reste.
const SLOW_TIMEOUT_MS = 180_000;

let baseUrl = '';
let token = '';
// Langue demandée au serveur. Il traduit ses messages d'erreur et les libellés
// de tâches d'après cet en-tête ; les verdicts de classement, eux, arrivent
// sous forme de clés et sont traduits sur place.
let language = 'fr';
let onUnauthorized: (() => void) | null = null;

export function configure(options: {
  baseUrl?: string;
  token?: string;
  language?: string;
  onUnauthorized?: () => void;
}) {
  if (options.baseUrl !== undefined) baseUrl = options.baseUrl.replace(/\/+$/, '');
  if (options.token !== undefined) token = options.token;
  if (options.language !== undefined) language = options.language;
  if (options.onUnauthorized !== undefined) onUnauthorized = options.onUnauthorized;
}

export function currentBaseUrl(): string {
  return baseUrl;
}

/** Traduit une panne de `fetch` en erreur exploitable par l'utilisateur. */
function networkError(error: unknown): ApiError {
  const message = error instanceof Error ? error.message : String(error);

  // Android remonte les refus TLS sous forme de message texte. Le distinguer
  // d'une simple coupure évite d'envoyer l'utilisateur vérifier son wifi alors
  // que le certificat du serveur a changé.
  if (/certificate|CertPath|SSL|trust anchor|hostname/i.test(message)) {
    return new ApiError(
      'certificate',
      "Le certificat du serveur n'est pas celui attendu par l'app. " +
        "S'il a été régénéré, il faut reconstruire l'APK avec la nouvelle autorité."
    );
  }
  if (/abort/i.test(message)) {
    return new ApiError('network', 'Le serveur ne répond pas — délai dépassé.');
  }
  return new ApiError('network', `Serveur injoignable. Vérifie le réseau.\n${message}`);
}

async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; slow?: boolean; auth?: boolean } = {}
): Promise<T> {
  if (!baseUrl) {
    throw new ApiError('network', "Adresse du serveur non configurée.");
  }

  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(),
    options.slow ? SLOW_TIMEOUT_MS : TIMEOUT_MS
  );

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      signal: controller.signal,
      headers: {
        'Accept-Language': language,
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(options.auth === false ? {} : { Authorization: `Bearer ${token}` }),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw networkError(error);
  } finally {
    clearTimeout(timer);
  }

  const raw = await response.text();
  let payload: any = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      // Le serveur a répondu autre chose que du JSON : page d'erreur d'un
      // proxy, redirection HTML… Le corps brut est plus utile qu'un « erreur ».
      throw new ApiError(
        'internal',
        `Réponse inattendue du serveur (${response.status}) :\n${raw.slice(0, 200)}`,
        response.status
      );
    }
  }

  if (!response.ok) {
    const error = payload?.error ?? {};
    const code: ErrorCode = error.code ?? 'internal';
    if (code === 'bad_token') {
      token = '';
      onUnauthorized?.();
    }
    throw new ApiError(
      code,
      error.message ?? `Erreur ${response.status}`,
      response.status,
      error.job_id
    );
  }

  return payload as T;
}

// --- Authentification -------------------------------------------------------

export async function login(password: string, device: string): Promise<string> {
  const data = await request<{ token: string }>('POST', '/api/v1/auth/login', {
    body: { password, device },
    auth: false,
  });
  token = data.token;
  return data.token;
}

export async function logout(): Promise<void> {
  try {
    await request('POST', '/api/v1/auth/logout');
  } finally {
    token = '';
  }
}

// --- État et jobs -----------------------------------------------------------

export const getStatus = () => request<Status>('GET', '/api/v1/status');

export const startJob = (action: JobAction, params: Record<string, unknown> = {}) =>
  request<{ job_id: string; name: string }>('POST', `/api/v1/jobs/${action}`, {
    body: params,
  });

export const getJob = (jobId: string, since = 0) =>
  request<JobSnapshot>('GET', `/api/v1/jobs/${jobId}?since=${since}`);

// --- Titre à l'unité --------------------------------------------------------

export const classifyTrack = (link: string, add: boolean) =>
  request<ClassifyResult>('POST', '/api/v1/tracks/classify', {
    body: { link, add },
    slow: true,
  });

// --- Résultat et réglages ---------------------------------------------------

export const getResult = () => request<ResultDocument>('GET', '/api/v1/result');

export const removeFromResult = (key: string, trackId: string) =>
  request<ResultDocument>(
    'DELETE',
    `/api/v1/result/${encodeURIComponent(key)}/${encodeURIComponent(trackId)}`
  );

export const getSettings = () => request<Settings>('GET', '/api/v1/settings');

export const putSettings = (patch: Partial<Settings>) =>
  request<Settings>('PUT', '/api/v1/settings', { body: patch });
