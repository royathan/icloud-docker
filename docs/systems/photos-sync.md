# Photos Sync

The photos sync system (`src/sync_photos.py` + 6 helper modules) handles downloading photos from iCloud Photos to local storage.

## Responsibilities

- Enumerate photos from iCloud Photo Libraries (personal + Shared Photo Library)
- Enumerate Apple Shared Albums as a separate source type
- Support album-based organization with `all_albums` mode
- Deduplicate across albums using hardlinks
- Filter by file extensions and album preferences
- Support multiple file sizes (original, medium, thumb, live_video)
- Handle date-based folder organization via `folder_format`
- Clean up obsolete local photos when enabled

## Module Map

| Module | Responsibility |
|--------|---------------|
| `sync_photos.py` | Entry point — `sync_photos()` orchestrates the process |
| `album_sync_orchestrator.py` | Album synchronization coordination |
| `photo_download_manager.py` | Parallel download task collection and execution |
| `photo_filter_utils.py` | Photo filtering by extensions and album preferences |
| `photo_path_utils.py` | Path normalization, folder format handling |
| `photo_file_utils.py` | File operations, metadata, 410 Gone retry |
| `photo_cleanup_utils.py` | Obsolete file removal |
| `hardlink_registry.py` | `HardlinkRegistry` class for deduplication |

## Boundaries

Photos sync is purely a download system. It writes to the local filesystem at the path configured in `photos.destination`.

## Key Entry Points

| Function | Purpose |
|----------|---------|
| `sync_photos(config, photos)` | Main entry — enumerate libraries and Shared Albums, delegate to album sync |
| `sync_album_photos(...)` | Sync a single album's photos |
| `create_hardlink_registry(...)` | Create registry for cross-album dedup |

## File Size Variants

| Variant | Description |
|---------|-------------|
| `original` | Full-resolution image |
| `original_alt` | RAW fallback |
| `medium` | Medium-quality |
| `thumb` | Thumbnail |
| `live_video_original` | Live Photo video (full-res) |
| `live_video_medium` | Live Photo video (medium) |
| `live_video_thumb` | Live Photo video (thumb) |

## Source Types and Destinations

Photo Libraries retain their historical behavior. With no
`library_destinations`, personal and Shared Photo Libraries write beneath the
same `photos.destination`. Optional mappings can separate them; the
`SharedLibrary` alias matches Apple's GUID-based `SharedSync-*` zone.

Apple Shared Albums are not libraries and never use the `libraries` or
`albums` filter. They are synced independently beneath
`<photos.destination>/shared-albums/<album name>/` by default. The namespace is
configurable with `shared_albums_destination`. A destination conflict with a
configured library root, or a planned regular album output exactly matching
the reserved Shared Albums root, skips Shared Album sync with an error rather
than merging source types.

Safe Shared Album names remain readable. Case-insensitive or sanitization-
equivalent collisions receive a stable suffix derived from `album.id`. Exact
duplicate display names cannot both appear because the current iCloudPy API is
a name-keyed mapping.

Shared Album assets reuse `sync_album_photos()`, so size/extension selection,
date folders, Live Photos, incremental checks, hardlinks, cleanup tracking,
parallel downloads, statistics, and per-photo error handling stay consistent.
Apple may provide reduced-quality Shared Album resources; `original` is the
best resource exposed by that service, not necessarily the uploader's original.

## Invariants

- All file paths MUST be NFC-normalized with `unicodedata.normalize("NFC", path)`
- `use_hardlinks` mode requires `all_albums: true`
- `HardlinkRegistry` tracks hardlinks across albums to prevent duplicates
- `folder_format` uses strftime patterns (e.g., `"%Y/%m"`)
- `enumeration_chunk_size` bounds peak memory (default 1000 photos/chunk)
- Missing `filters.shared_albums` syncs all Shared Albums; `false` disables;
  a list selects exact display names
- `all_albums` affects Photo Libraries only; Shared Albums remain album-shaped
- HTTP 410 Gone triggers download URL refresh via `_refresh_photo_download_url()`
- URL refresh MUST use CloudKit `records/lookup`, not `records/query` — `CPLMaster`
  is not a query-indexable type and querying it always fails with
  `Type is not marked indexable: CPLMaster (BAD_REQUEST)`
- Repeated consecutive refresh failures escalate from DEBUG to WARNING, so a
  systematically broken refresh path is visible without debug logging

## Dependencies

- **Depends on:** `config_parser`, `filesystem_utils`, `icloudpy.services.photos`
- **Depended on by:** `sync.py`

## Tests

- `tests/test_sync_photos.py` — photos sync tests
- `tests/test_photo_cleanup_utils.py` — cleanup tests
- `tests/test_live_photo_extension.py` — live photo handling
- `tests/test_live_photo_pair_download.py` — live photo pairing
- Run: `ENV_CONFIG_FILE_PATH=./tests/data/test_config.yaml pytest tests/test_sync_photos.py`

## Related Docs

- [Sync Cycle Flow](../flows/sync-cycle.md)
- [Coding Standards](../standards/coding.md)
