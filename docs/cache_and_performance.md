# Cache & Performance Improvements

## What Was Done

### 1. Three-Layer Image Cache (L1 + L2 local + L2 remote)

**Problem:** Education section icons were fetched from remote URLs on every page render, blocking the page for seconds (or 10+ seconds for invalid URLs).

**Solution:** Three cache layers in `controller/cache.py`:

| Layer | Backend | Speed | Survives |
|-------|---------|-------|----------|
| L1 | `@st.cache_data` (in-memory) | instant | process lifetime |
| L2 local | `LocalFileCache` (`.cache/` dir) | ~1 ms | process restarts |
| L2 remote | `RedisCache` | ~5 ms | deployments |

- `get_image_from_cache(url)` -- cache-only lookup, zero network I/O
- `fetch_image_cached(url)` -- full download with 3-second timeout
- Failed downloads are cached as `b""` so invalid URLs never block again

### 2. Non-Blocking Image Loading

**Problem:** Even with caching, first-ever page load blocked while downloading images.

**Solution:** Background-thread pattern in `pages/resume_page.py`:

1. `get_image_from_cache(url)` -- instant cache check (no network)
2. Cache hit: show image immediately
3. Cache miss: `_ensure_image_downloaded(url)` spawns a daemon thread
4. Page renders instantly; images appear on next user interaction

### 3. `@st.fragment` for Atomic Language Switching

**Problem:** Russian data has 15 experience entries vs English's 14. When switching languages, Streamlit's element-position diffing caused ghost duplicates (grey non-clickable elements from the old language persisting alongside fresh ones).

**Solution:** Decorated `_render_page()` with `@st.fragment`:
- Fragment output is replaced atomically (no incremental element diffing)
- `on_click` callback changes language, then only the fragment reruns
- Widget keys include language (`skills-{language}-{i}`) to prevent stale state
- `selected_skills` cleared on switch to avoid cross-language mismatches

### 4. Secrets Warning Eliminated

**Problem:** `st.secrets["REDIS_URL"]` displayed a visible warning banner when `secrets.toml` was missing.

**Solution:** `RedisCache._resolve_url()` now checks the filesystem for `.streamlit/secrets.toml` and `~/.streamlit/secrets.toml` before ever touching `st.secrets`. If neither file exists, it skips silently.

### 5. TTL on All Cache Backends

**Problem:** Local file cache entries persisted forever; Redis TTL was 7 days.

**Solution:** `DEFAULT_TTL_SECONDS = 3600` (1 hour) applied to both backends. `LocalFileCache.get()` checks `mtime` and expires stale entries.

---

## What Can Be Improved Further

### Quick Wins

- **Pre-warm the other language's document cache** on first load. After generating the English DOCX, spawn a background thread to generate the Russian PDF (or vice versa). First language switch would be instant.
- **HTTP caching headers** on education icon URLs via `urllib.request.Request` with `If-Modified-Since` / `ETag` -- avoids re-downloading unchanged images when the L2 TTL expires.
- **Increase image TTL** separately from document TTL. University logos change rarely; a 24-hour or 7-day TTL for images would reduce unnecessary re-downloads.

### Medium Effort

- **Client-side image caching** -- serve education icons as `<img src="...">` HTML tags instead of `st.image(bytes)`. Browsers cache images natively via HTTP cache headers, eliminating server-side download entirely. Trade-off: loses server-side cache control.
- **Streaming fragment rendering** -- split the page into multiple `@st.fragment` sections (header, experience, education) so each can rerun independently. E.g., skill pill clicks would only re-render experience, not the entire page.
- **WebSocket-based image push** -- after background image download completes, push an event to the client to trigger a fragment rerun automatically (instead of waiting for the next user interaction).

### Architectural

- **CDN for static assets** -- serve profile photo, CSS, and cached education icons from a CDN (e.g., Cloudflare R2 or S3+CloudFront). Eliminates origin server load entirely for repeat visitors.
- **Redis connection pooling** -- if Redis is enabled, use a connection pool instead of a single connection. Reduces latency for concurrent users.
- **Cache warming on deploy** -- a startup script that pre-generates both language variants of the DOCX/PDF and populates L2. First visitor gets instant downloads.
