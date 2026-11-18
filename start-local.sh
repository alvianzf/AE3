#!/usr/bin/env bash
# Starts Neo4j, Postgres and the Clinic backend (which also serves the built
# SvelteKit frontend from web-build/) on http://localhost:8000.
# Progress is written to .local-run.log so it can be checked from outside.
cd "$(dirname "$0")" || exit 1
MOCK=0; [ "$1" = "--mock-llm" ] && MOCK=1
LOG=.local-run.log
: > "$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "start: services via Homebrew"
if command -v brew >/dev/null 2>&1; then
  for f in $(brew list --formula 2>/dev/null | grep -E '^(postgresql|neo4j)'); do
    say "brew services start $f"
    brew services start "$f" >>"$LOG" 2>&1
  done
else
  say "WARN: brew not found - start Neo4j (7687) and Postgres (5433) yourself"
fi


# pgvector is required by app/retrieval/pgvector_store.py at boot.
PGPREFIX="/opt/homebrew/opt/postgresql@16"
VEC="$PGPREFIX/share/postgresql@16/extension/vector.control"
if [ -d "$PGPREFIX" ] && [ ! -f "$VEC" ]; then
  say "pgvector missing for postgresql@16 - trying brew install pgvector"
  brew install pgvector >>"$LOG" 2>&1
  if [ ! -f "$VEC" ]; then
    say "brew formula did not cover pg16 - building pgvector v0.8.1 from source"
    T=$(mktemp -d)
    if git clone --quiet --depth 1 --branch v0.8.1 https://github.com/pgvector/pgvector.git "$T/pgvector" >>"$LOG" 2>&1 \
       && (cd "$T/pgvector" && make PG_CONFIG="$PGPREFIX/bin/pg_config" >>"$LOG" 2>&1 && make install PG_CONFIG="$PGPREFIX/bin/pg_config" >>"$LOG" 2>&1); then
      say "pgvector built and installed"
    else
      say "FAIL: could not build pgvector (see log above)"; exit 1
    fi
  fi
  [ -f "$VEC" ] && say "pgvector present" || { say "FAIL: vector.control still missing"; exit 1; }
  brew services restart postgresql@16 >>"$LOG" 2>&1
fi


seed_demo() {
  if [ -f seed_demo.py ]; then
    say "seeding local demo accounts (seed_demo.py)"
    .venv/bin/python seed_demo.py 2>&1 | tee -a "$LOG"
  fi
}

wait_port() { # host port name seconds
  for _ in $(seq 1 "$4"); do nc -z "$1" "$2" 2>/dev/null && { say "$3 is up on :$2"; return 0; }; sleep 1; done
  say "FAIL: $3 not listening on :$2 after $4s"; return 1
}
wait_port 127.0.0.1 5433 Postgres 60
wait_port 127.0.0.1 7687 Neo4j 150

if [ "$MOCK" = 1 ]; then
  say "mock-LLM mode: demo-only mock model server on :8765, backend will use it"
  pkill -f "mock_llm_server.py" 2>/dev/null
  nohup .venv/bin/python mock_llm_server.py >mock-llm.log 2>&1 &
  for _ in $(seq 1 15); do curl -fsS -m 2 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break; sleep 1; done
  curl -fsS -m 2 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && say "mock model server is up" || { say "FAIL: mock server did not start - see mock-llm.log"; exit 1; }
  pkill -f "uvicorn app.main:app" 2>/dev/null
  for _ in $(seq 1 20); do curl -fsS -m 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1 || break; sleep 1; done
  for r in READER GRAPH_BUILDER EMBEDDER RETRIEVAL REASONER CHECKER_LLM; do
    export "${r}_BASE_URL=http://127.0.0.1:8765/v1" "${r}_API_KEY=mock-key"
  done
fi

if curl -fsS -m 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  say "backend already running on :8000"
else
  say "starting backend"
  nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >backend-local.log 2>&1 &
  for _ in $(seq 1 90); do
    curl -fsS -m 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1 && { seed_demo; say "READY: http://localhost:8000"; exit 0; }
    sleep 1
  done
  say "FAIL: backend did not become healthy - see backend-local.log"
  tail -n 25 backend-local.log | tee -a "$LOG"
  exit 1
fi
seed_demo
say "READY: http://localhost:8000"
