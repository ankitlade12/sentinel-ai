# Google Cloud + Phoenix setup (full path)

## 1. Project + APIs

```bash
gcloud projects create riverside-sentinel        # or use an existing project
gcloud config set project riverside-sentinel
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

## 2. Credentials (ADC)

```bash
gcloud auth application-default login
```

The backend (Vertex embeddings, Vertex Vector Search, Firestore, Gemini via
Vertex) authenticates with Application Default Credentials. On Cloud Run it uses
the service account; locally it uses your ADC.

## 3. Firestore (quarantine store)

```bash
gcloud firestore databases create --location=us-central1
```

Verdicts are written to the `sentinel_verdicts` collection
(`SENTINEL_FIRESTORE_PREFIX`).

## 4. Vertex AI Vector Search (optional managed index)

The corpus works in **embeddings-only** mode out of the box (real Vertex
embeddings, in-memory nearest-neighbour). To serve retrieval from a managed
index instead:

1. Create an index + index endpoint (see Vertex AI Vector Search docs).
2. Deploy the index and note the endpoint resource name + deployed index id.
3. Set `VERTEX_VECTOR_INDEX_ENDPOINT` and `VERTEX_VECTOR_DEPLOYED_INDEX_ID`.
4. `make index` embeds every chunk and upserts the datapoints.

## 5. Phoenix

Free Phoenix Cloud account → https://app.phoenix.arize.com. Set
`PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY`, and `PHOENIX_PROJECT_NAME`. The
ADK agent spawns a built-in Phoenix MCP server in-process and calls it at
runtime — no endpoint needed. See [`ARIZE.md`](ARIZE.md).

## 6. Deploy to Cloud Run

```bash
# Backend
gcloud run deploy sentinel-backend \
  --source . --region us-central1 \
  --set-env-vars "SENTINEL_CORPUS=vertex,SENTINEL_STORE=firestore,SENTINEL_LLM_PROVIDER=vertex,GOOGLE_CLOUD_PROJECT=riverside-sentinel" \
  --set-secrets "PHOENIX_API_KEY=phoenix-api-key:latest"

# Dashboard (point it at the backend URL)
gcloud run deploy sentinel-frontend \
  --source ./frontend --region us-central1 \
  --set-env-vars "SENTINEL_API_TARGET=https://sentinel-backend-XXXX.run.app"
```

Or build images locally and push: `make docker-build` then `make docker-push`
with `REGISTRY=us-central1-docker.pkg.dev/PROJECT/sentinel`.

## Env reference

Every variable is documented in [`../.env.example`](../.env.example).
