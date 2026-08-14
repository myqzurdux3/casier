/**
 * Tests du client API contre un vrai serveur HTTP local.
 *
 * Le client est la seule partie de l'app qui puisse échouer silencieusement :
 * un code d'erreur mal lu et l'utilisateur voit « erreur interne » là où le
 * serveur disait « reconnecte Spotify ». D'où des tests sur le contrat, pas
 * sur les écrans.
 *
 *   node --test tests/
 *
 * Le module est en TypeScript ; on teste la version compilée par tsc, ou à
 * défaut on saute proprement plutôt que de faire croire à une couverture.
 */

const assert = require('node:assert');
const http = require('node:http');
const { test, before, after, describe } = require('node:test');
const path = require('node:path');

let api;
try {
  api = require(path.join(__dirname, '..', 'dist', 'lib', 'api.js'));
} catch {
  console.log('dist/lib/api.js absent — lance `npx tsc --outDir dist` avant.');
  process.exit(0);
}

let server;
let baseUrl;
let handler = () => ({ status: 200, body: {} });

before(async () => {
  server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : null;

    const reply = handler({ method: req.method, url: req.url, body, headers: req.headers });
    res.writeHead(reply.status, { 'Content-Type': reply.raw ? 'text/html' : 'application/json' });
    res.end(reply.raw ?? JSON.stringify(reply.body));
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
  api.configure({ baseUrl, token: 'jeton-de-test' });
});

after(() => server.close());

describe('client API', () => {
  test('login renvoie et mémorise le jeton', async () => {
    handler = ({ body }) => ({
      status: 200,
      body: { token: `jeton-pour-${body.password}` },
    });
    const token = await api.login('secret', 'test');
    assert.strictEqual(token, 'jeton-pour-secret');
  });

  test('le jeton part en en-tête Authorization', async () => {
    let vu = null;
    handler = ({ headers }) => {
      vu = headers.authorization;
      return { status: 200, body: { liked_count: 0 } };
    };
    await api.getStatus();
    assert.strictEqual(vu, 'Bearer jeton-pour-secret');
  });

  test('les codes d erreur du serveur sont préservés', async () => {
    handler = () => ({
      status: 409,
      body: { error: { code: 'spotify_disconnected', message: 'Aucun compte lié.' } },
    });
    await assert.rejects(api.getStatus(), (error) => {
      assert.strictEqual(error.code, 'spotify_disconnected');
      assert.strictEqual(error.message, 'Aucun compte lié.');
      assert.strictEqual(error.status, 409);
      return true;
    });
  });

  test('job_busy transporte l identifiant du job en cours', async () => {
    handler = () => ({
      status: 409,
      body: { error: { code: 'job_busy', message: 'déjà en cours', job_id: 'abc123' } },
    });
    await assert.rejects(api.startJob('fetch'), (error) => {
      assert.strictEqual(error.jobId, 'abc123');
      return true;
    });
  });

  test('un 401 déclenche le rappel de déconnexion', async () => {
    let deconnecte = false;
    api.configure({ token: 'périmé', onUnauthorized: () => (deconnecte = true) });
    handler = () => ({
      status: 401,
      body: { error: { code: 'bad_token', message: 'Jeton invalide.' } },
    });

    await assert.rejects(api.getStatus());
    assert.strictEqual(deconnecte, true);
  });

  test('une réponse non-JSON ne fait pas planter le client', async () => {
    api.configure({ token: 'jeton' });
    handler = () => ({ status: 502, raw: '<html>Bad Gateway</html>' });

    await assert.rejects(api.getStatus(), (error) => {
      assert.strictEqual(error.code, 'internal');
      assert.match(error.message, /Bad Gateway/);
      return true;
    });
  });

  test('serveur injoignable donne une erreur réseau distincte', async () => {
    api.configure({ baseUrl: 'http://127.0.0.1:1' });
    await assert.rejects(api.getStatus(), (error) => {
      assert.strictEqual(error.code, 'network');
      assert.strictEqual(error.isTransient, true);
      return true;
    });
    api.configure({ baseUrl });
  });

  test('le curseur since est transmis', async () => {
    let vue = null;
    handler = ({ url }) => {
      vue = url;
      return { status: 200, body: { lines: [], next: 0 } };
    };
    await api.getJob('job1', 42);
    assert.strictEqual(vue, '/api/v1/jobs/job1?since=42');
  });

  test('les identifiants sont échappés dans l URL', async () => {
    let vue = null;
    handler = ({ url }) => {
      vue = url;
      return { status: 200, body: {} };
    };
    await api.removeFromResult('rap/us', 'a b');
    assert.strictEqual(vue, '/api/v1/result/rap%2Fus/a%20b');
  });
});
