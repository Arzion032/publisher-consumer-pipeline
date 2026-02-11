# Publisher–Consumer Pipeline

This project is a Dockerised publisher–consumer pipeline for scraping news articles, enriching them with LLM analysis, and storing the results in MongoDB. Redis is used as a prioritized job queue between the publisher and the consumer.

---

## Prerequisites

- **Docker + Docker Compose**
  - Any recent Docker Desktop or Docker Engine installation that supports `docker compose` v2.
- **Environment variables**
  - A `.env` file at the repo root (used by `docker-compose.yml`) containing at least:
    - `GEMINI_API_KEY=<your_google_generative_ai_key>`
    - Optionally override defaults:
      - `REDIS_HOST`, `REDIS_PORT`
      - `MONGO_HOST`, `MONGO_PORT`, `MONGO_DB`, `MONGO_COLLECTION`

---

## Quick Start

From the repository root:

```bash
docker compose up --build
```

What happens:

- `redis` and `mongodb` start first and must pass their health checks.
- **Publisher** container:
  - Reads `publisher/articles.json`.
  - Validates and enqueues articles into Redis lists `articles:priority:1..5`.
  - Exits when all articles have been published.
- **Consumer** container:
  - Runs continuously, consuming from the priority lists.
  - Scrapes each URL, calls the LLM, and stores enriched documents in MongoDB.

To stop the stack:

```bash
docker compose down
```

Data is persisted via Docker volumes for Redis and MongoDB.

---

## Additional Feature / Innovation

This pipeline includes a **shared `common/` package**, **strict payload validation**, and several **resilience features** to keep services consistent and robust:

- **Shared connections (`common.connections`)**
  - Centralised helpers for Redis and MongoDB:
    - `create_redis_client()` – retry loop, shared env configuration.
    - `create_mongo_collection()` – retry loop and a unique index on `id` for idempotency.
  - Both publisher and consumer use these helpers, so connection behaviour and configuration are guaranteed to stay in sync.

- **Payload validation (`common.validation`)**
  - A single `validate_article_payload(article)` function is used:
    - In the **publisher**, before enqueueing any article from `articles.json`.
      - Invalid payloads are logged and pushed to `articles:invalid` (for later inspection) without breaking the normal flow.
    - In the **consumer**, after popping messages from Redis and decoding JSON.
      - Invalid or malformed messages are moved to `articles:failed`.
  - This provides a **defensive contract** around the queue: only structurally valid jobs are processed, while bad payloads are safely quarantined.

- **Scraper and queue hardening**
  - A **retry mechanism with exponential backoff** for failed scrapes (network timeouts, transient HTTP errors).
  - A **per-domain rate limiter** to avoid hammering the same host and reduce the risk of being blocked.
  - A **priority handler** where higher-priority articles (priority `1` is highest) are processed first via `articles:priority:1..5` queues and `BLPOP` ordering.

Together, these additions make the system easier to maintain (shared logic) and more observable and resilient (clear error queues, resilient scraping, and priority-aware processing).

---

## LLM Explanation

- **Model**
  - Uses **Google Gemini** via the `google-generativeai` Python SDK.
  - The configured model is `gemini-2.5-flash-lite` (see `consumer/ai_analyzer.py`).

- **Integration**
  - The consumer’s `process_article` function:
    1. Scrapes the article content using `scraper.scrape_article`.
    2. Calls `ai_analyzer.analyze_article(title, content)` which:
       - Builds a structured prompt.
       - Calls `model.generate_content(...)` from `google.generativeai`.
       - Returns a JSON string with:
         - `summary` (2 sentences),
         - `sentiment` (`positive`/`negative`/`neutral`),
         - `keywords` (5 items).
    3. The consumer parses this JSON and merges it into the MongoDB document.
  - If the LLM call fails or returns unexpected output, the consumer logs a warning and falls back to `summary=None`, `sentiment=None`, `keywords=[]` so that the pipeline still completes.

---

## Design Choices

### Database (MongoDB)

- **Flexible schema**: Articles can evolve over time (new fields from scraping or LLMs) without rigid migrations.
- **Document-centric model**: One MongoDB document corresponds to one processed article, including raw content and derived metadata.
- **Idempotency**:
  - A unique index on `id` ensures the same article is not stored twice.
  - The consumer treats `DuplicateKeyError` as “already processed” and does not fail the job.

### Queue (Redis)

- **Simple, fast, and battle-tested** for producer/consumer workloads.
- **Priority queues**:
  - Uses list keys `articles:priority:1..5` with `BLPOP` to:
    - always check `articles:priority:1` first (1 = highest priority),
    - process items FIFO within each individual priority list.
- **Failed jobs list**:
  - `articles:failed` – single list where all failed jobs end up:
    - invalid JSON from Redis,
    - invalid payloads (schema/validation failures),
    - scrape failures,
    - MongoDB write errors.

### Scraper Error Handling

The scraper (`consumer/scraper.py`) is designed to be robust against real-world web issues:

- **Retries with exponential backoff**:
  - Network timeouts and transient HTTP errors trigger retries with increasing delays.
- **Per-domain rate limiting**:
  - Enforces a minimum delay between requests to the same host to avoid hammering a single site.
- **Content quality checks**:
  - Articles with too-short or empty content are rejected early.
- **Consumer fallback**:
  - If scraping ultimately fails, the consumer pushes the job to `articles:failed` and logs the issue, ensuring the worker keeps running and the failure is visible.

These choices aim to keep the pipeline **observable, resilient, and easy to extend** as new article sources or analysis steps are added.