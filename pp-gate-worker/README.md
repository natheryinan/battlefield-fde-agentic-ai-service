
# pp-gate-worker

Single-view + TTL gate for sharing sensitive payloads (HTML/JSON).

## Endpoints
- GET /health
- POST /issue
- GET /gate?t=TOKEN

## Setup
```bash
npm i
npx wrangler login
npx wrangler kv namespace create GATES
