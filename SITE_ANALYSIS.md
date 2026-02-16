# hentaimama.io - Site Structure Analysis

Technical findings for building the H-CLI scraper.

---

## Platform

- **CMS:** WordPress with DooPlay theme (v2.3x by Doothemes)
- **Anti-scraping:** Cloudflare present but not blocking requests. No JS-only rendering for content pages.
- **Content types:** `tvshows`, `episodes`, `seasons`, `movies`, `dt_links`

---

## URL Patterns

| Content         | URL Pattern                            | Example                                              |
|-----------------|----------------------------------------|------------------------------------------------------|
| Homepage        | `/`                                    | `https://hentaimama.io/`                             |
| Search          | `/?s={query}`                          | `https://hentaimama.io/?s=overflow`                  |
| Series page     | `/tvshows/{slug}/`                     | `https://hentaimama.io/tvshows/overflow/`            |
| Episode page    | `/episodes/{slug}/`                    | `https://hentaimama.io/episodes/overflow-episode-1/` |
| Genre listing   | `/genre/{slug}/`                       | `https://hentaimama.io/genre/romance/`               |
| Genre page N    | `/genre/{slug}/page/{n}/`              | `https://hentaimama.io/genre/romance/page/2/`        |
| All TV shows    | `/tvshows/`                            | `https://hentaimama.io/tvshows/`                     |
| Genre sitemap   | `/genres-sitemap.xml`                  | 127 genres                                           |
| Shows sitemap   | `/tvshows-sitemap.xml`                 | All series URLs                                      |
| Episodes sitemap| `/episodes-sitemap1.xml`, `...2.xml`   | All episode URLs                                     |

---

## Search Results

**URL:** `/?s={query}`
**Rendering:** Server-side HTML (no JS needed)

### Selectors

| Data             | CSS Selector                          | Notes                              |
|------------------|---------------------------------------|------------------------------------|
| Each result      | `.search-page .result-item`           | Container for one result           |
| Title + link     | `.result-item .title a`               | `href` = series/episode URL        |
| Thumbnail        | `.result-item .image .thumbnail a img`| Poster image                       |
| Rating           | `.result-item .meta .rating`          | Text like "IMDb 8.5"              |
| Year             | `.result-item .meta .year`            | Release year                       |
| Description      | `.result-item .details .contenido p`  | Short synopsis                     |
| Content type     | `.result-item .thumbnail span`        | Class = `tvshows`, `episodes` etc. |
| Pagination       | `.pagination a`                       | Page links                         |

---

## Genre Browsing

**URL:** `/genre/{slug}/`
**Items per page:** 30
**Pagination:** `/genre/{slug}/page/{n}/`

### Selectors

| Data             | CSS Selector                          |
|------------------|---------------------------------------|
| Each item card   | `.items .item`                        |
| Title + link     | `.item .data h3 a`                    |
| Poster link      | `.item .poster a`                     |
| Poster image     | `.item .poster img` (uses `data-src`) |
| Rating           | `.item .rating`                       |
| Pagination       | `.pagination a`                       |

### Available Genres (127 total, from sitemap)

Accessible via `/genres-sitemap.xml`. Examples:
```
3d, action, adventure, ahegao, anal, bdsm, blackmail, blowjob, bondage,
cat-girl, comedy, cosplay, creampie, dark-skin, demons, drama, dubbed,
ecchi, elf, fantasy, femdom, footjob, furry, futanari, gangbang, harem,
horror, incest, loli, maid, milf, monster, nurse, ntr, orgy, public-sex,
romance, school-girls, sci-fi, tentacles, threesome, tsundere, uncensored,
vanilla, yuri, ...
```

---

## Series Page (TV Show)

**URL:** `/tvshows/{slug}/`

### Description & Metadata

| Data             | CSS Selector                          | Example Value                     |
|------------------|---------------------------------------|-----------------------------------|
| Synopsis         | `.wp-content p`                       | Multi-paragraph plot description  |
| Genres           | `.sgeneros a`                         | Links like `/genre/romance/`      |
| Title (alt)      | `.custom_fields span.valor` (1st)     | "Overflow"                        |
| Studio           | `.custom_fields span.valor` (2nd)     | "Hokiboshi"                       |
| First air date   | `.custom_fields span.valor` (3rd)     | "Jan. 07, 2020"                   |
| Last air date    | `.custom_fields span.valor` (4th)     | "Jan. 07, 2020"                   |
| Status           | `.custom_fields span.valor` (5th)     | "Ongoing" or "Completed"          |
| Date (header)    | `.sheader .date`                      | "Jan. 07, 2020"                   |

### Episode Listing

Episodes are **server-side rendered** on the series page (not AJAX loaded).

| Data               | CSS Selector                                          |
|--------------------|-------------------------------------------------------|
| Each episode       | `#episodes article.item.se.episodes`                  |
| Episode link       | `.season_m a` → `href`                                |
| Series name        | `.season_m a .b`                                      |
| Episode label      | `.season_m a .c`                                      |
| Rating             | `.rating`                                             |
| Date               | `.data span`                                          |
| Sub/Dub badge      | `.ep_status .status-sub`                              |

Episodes are listed **newest first** (reverse order). Sort ascending for playback.

---

## Episode Page (Video Player)

**URL:** `/episodes/{slug}/`

### Getting the Post ID

The episode's WordPress post ID is needed for the AJAX call. Found in:
```
input[name="idpost"]  →  value="7360"
```

### Loading Video Sources (AJAX)

Video iframes are **NOT** in the initial HTML. They are loaded via AJAX:

```
POST https://hentaimama.io/wp-admin/admin-ajax.php
Content-Type: application/x-www-form-urlencoded

action=get_player_contents&a={post_id}
```

**Response:** JSON array of HTML strings, each containing an `<iframe>`.

Example response (3 mirrors):
```json
[
  "<iframe src=\"https://hentaimama.io/new2.php?p=Ty9PdmVyZmxvdzAxLm1wNA==\" ...></iframe>",
  "<iframe src=\"https://hentaimama.io/newjav.php?p=Ty9PdmVyZmxvdzAxLm1wNA==\" ...></iframe>",
  "<iframe src=\"https://gounlimited.to/embed-9glal8vyd3ij.html\" ...></iframe>"
]
```

### Mirror Types

| Mirror          | URL Pattern                                  | Type         |
|-----------------|----------------------------------------------|--------------|
| Mirror 1        | `hentaimama.io/new2.php?p={base64}`          | Self-hosted  |
| Mirror 2        | `hentaimama.io/newjav.php?p={base64}`        | Self-hosted  |
| Mirror 3+       | External embeds (gounlimited, etc.)          | Third-party  |

### Extracting Direct MP4 URL

**Step 1:** Decode the base64 `p` parameter:
```
Ty9PdmVyZmxvdzAxLm1wNA==  →  O/Overflow01.mp4
```

**Step 2:** Fetch the embed page (`new2.php?p=...`), which contains a JWPlayer-style setup:
```javascript
sources: [{
    file: "https://gdvid.info/O/Overflow01.mp4"
}]
```

**Step 3:** Extract the `file:` URL → direct MP4 link ready for MPV.

### Server Selection List

On the episode page (server-side rendered):

| Data             | CSS Selector                                |
|------------------|---------------------------------------------|
| Server list      | `.sourceslist li a.options`                 |
| Server name      | Text content of the `<a>` tag               |
| Server target    | `href` attribute (`#option-1`, `#option-2`) |

### Episode Navigation

| Data             | CSS Selector                          |
|------------------|---------------------------------------|
| Previous episode | `.pag_episodes .item:first-child a`   |
| Series link      | `.pag_episodes .item:nth-child(2) a`  |
| Next episode     | `.pag_episodes .item:last-child a`    |
| Disabled state   | `.nonex` class on the `.item` div     |

---

## Stream Extraction Pipeline

```
1. Fetch episode page HTML
2. Extract post ID from input[name="idpost"]
3. POST to admin-ajax.php with action=get_player_contents&a={post_id}
4. Parse JSON response → array of iframe HTML strings
5. Extract iframe src URLs
6. For self-hosted mirrors (new2.php / newjav.php):
   a. Decode base64 ?p= parameter → file path
   b. Fetch embed page
   c. Extract "file:" URL from JWPlayer config → direct .mp4
7. For external mirrors: pass iframe URL to yt-dlp
8. Cache resolved stream URL
```

---

## Nonces & Auth

| Endpoint                        | Auth Required? | Notes                                    |
|---------------------------------|----------------|------------------------------------------|
| `/?s={query}` (HTML search)     | No             | Standard HTML page, freely accessible     |
| `/wp-json/dooplay/search`       | Yes (nonce)    | Live search API, NOT usable without nonce |
| `admin-ajax.php` (player)       | No             | `get_player_contents` works without nonce |
| Genre/series/episode pages      | No             | All server-side rendered                  |

---

## Key Technical Notes

1. **No Cloudflare challenge** on content pages — standard requests work fine
2. **Episodes listed newest-first** on series pages — reverse for sequential playback
3. **Base64 decode** is the key to getting self-hosted mirror URLs
4. **`gdvid.info`** is the CDN serving the actual MP4 files
5. **Multiple mirrors** per episode — self-hosted mirrors are most reliable
6. **Lazy-loaded images** use `data-src` attribute instead of `src`
7. **127 genres** available for filtering via sitemap XML
8. **30 items per page** on genre/archive pages with numbered pagination
