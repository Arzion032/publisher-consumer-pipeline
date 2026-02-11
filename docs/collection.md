# MongoDB: articles collection

## Location
| Setting    | Default        | Env var          |
|-----------|----------------|------------------|
| Database  | `articles_db`  | `MONGO_DB`       |
| Collection| `articles`     | `MONGO_COLLECTION` |

## Document schema
| Field | Type | Description |
|-------|------|-------------|
| `id` | string or int | Unique article identifier from the publisher; used for idempotency. |
| `url` | string | Source URL of the article. |
| `source` | string | Source name (e.g. bbc, reuters). |
| `category` | string | Category (e.g. technology, healthcare, business). |
| `title` | string | Article title extracted by the scraper. |
| `content` | string | Full article body text from the scraper. |
| `summary` | string or null | AI-generated summary. |
| `sentiment` | string or null | AI-derived sentiment (e.g. positive, negative, neutral). |
| `keywords` | array of strings | AI-extracted keywords. |
| `word_count` | int | Number of words in the article content. |
| `priority` | int | Priority level (1–5) from the queue. |
| `created_at` | datetime | Time when the document was stored. |