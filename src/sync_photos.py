"""Sync photos module.

This module provides the main photo synchronization functionality,
orchestrating the downloading of photos from iCloud to local storage.
"""

___author___ = "Mandar Patil <mandarons@pm.me>"

import hashlib
import os
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from src import config_parser, configure_icloudpy_logging, get_logger
from src.album_sync_orchestrator import sync_album_photos
from src.hardlink_registry import create_hardlink_registry
from src.photo_cleanup_utils import remove_obsolete_files
from src.photo_path_utils import normalize_file_path

# Configure icloudpy logging immediately after import
configure_icloudpy_logging()

LOGGER = get_logger()


# Legacy functions preserved for backward compatibility with existing tests
# These functions are now implemented using the new modular architecture


def get_max_threads(config):
    """Get maximum number of threads for parallel downloads.

    Legacy function - now delegates to config_parser.

    Args:
        config: Configuration dictionary

    Returns:
        Maximum number of threads to use for downloads
    """
    return config_parser.get_app_max_threads(config)


def get_name_and_extension(photo, file_size):
    """Extract filename and extension.

    Legacy function - now delegates to photo_path_utils.

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant

    Returns:
        Tuple of (name, extension)
    """
    from src.photo_path_utils import get_photo_name_and_extension

    return get_photo_name_and_extension(photo, file_size)


def photo_wanted(photo, extensions):
    """Check if photo is wanted based on extension.

    Legacy function - now delegates to photo_filter_utils.

    Args:
        photo: Photo object from iCloudPy
        extensions: List of allowed extensions

    Returns:
        True if photo should be synced, False otherwise
    """
    from src.photo_filter_utils import is_photo_wanted

    return is_photo_wanted(photo, extensions)


def generate_file_name(photo, file_size, destination_path, folder_format):
    """Generate full path to file.

    Legacy function - now delegates to photo_download_manager.

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant
        destination_path: Base destination path
        folder_format: Folder format string

    Returns:
        Full file path
    """
    from src.photo_download_manager import generate_photo_path

    return generate_photo_path(photo, file_size, destination_path, folder_format)


def photo_exists(photo, file_size, local_path):
    """Check if photo exist locally.

    Legacy function - now delegates to photo_file_utils.

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant
        local_path: Local file path to check

    Returns:
        True if photo exists with correct size, False otherwise
    """
    from src.photo_file_utils import check_photo_exists

    return check_photo_exists(photo, file_size, local_path)


def create_hardlink(source_path, destination_path):
    """Create a hard link from source to destination.

    Legacy function - now delegates to photo_file_utils.

    Args:
        source_path: Path to source file
        destination_path: Path for new hardlink

    Returns:
        True if successful, False otherwise
    """
    from src.photo_file_utils import create_hardlink as create_hardlink_impl

    return create_hardlink_impl(source_path, destination_path)


def download_photo(photo, file_size, destination_path):
    """Download photo from server.

    Legacy function - now delegates to photo_file_utils.

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant
        destination_path: Where to save the photo

    Returns:
        True if successful, False otherwise
    """
    from src.photo_file_utils import download_photo_from_server

    return download_photo_from_server(photo, file_size, destination_path)


def process_photo(photo, file_size, destination_path, files, folder_format, hardlink_registry=None):
    """Process photo details (legacy function for backward compatibility).

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant
        destination_path: Base destination path
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for hardlinks (legacy dict format)

    Returns:
        True if photo was processed successfully, False otherwise
    """
    from src.photo_download_manager import collect_download_task, execute_download_task

    # Convert legacy hardlink registry dict to new registry format if needed
    converted_registry = None
    if hardlink_registry is not None:
        from src.hardlink_registry import HardlinkRegistry

        converted_registry = HardlinkRegistry()
        for key, path in hardlink_registry.items():
            # Legacy format: photo_id_file_size -> path
            if "_" in key:
                parts = key.rsplit("_", 1)
                if len(parts) == 2:
                    photo_id, file_sz = parts
                    converted_registry.register_photo_path(photo_id, file_sz, path)

    # Collect download task
    task_info = collect_download_task(
        photo,
        file_size,
        destination_path,
        files,
        folder_format,
        converted_registry,
    )

    if task_info is None:
        return False

    # Execute task
    result = execute_download_task(task_info)

    # Update legacy registry if provided
    if result and hardlink_registry is not None:
        photo_key = f"{photo.id}_{file_size}"
        hardlink_registry[photo_key] = task_info.photo_path

    return result


def collect_photo_for_download(photo, file_size, destination_path, files, folder_format, hardlink_registry=None):
    """Collect photo info for parallel download without immediately downloading.

    Legacy function - now delegates to photo_download_manager.

    Args:
        photo: Photo object from iCloudPy
        file_size: File size variant
        destination_path: Base destination path
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for hardlinks (legacy dict format)

    Returns:
        Download task info or None
    """
    from src.photo_download_manager import collect_download_task

    # Convert legacy hardlink registry dict to new registry format if needed
    converted_registry = None
    if hardlink_registry is not None:
        from src.hardlink_registry import HardlinkRegistry

        converted_registry = HardlinkRegistry()
        for key, path in hardlink_registry.items():
            if "_" in key:
                parts = key.rsplit("_", 1)
                if len(parts) == 2:
                    photo_id, file_sz = parts
                    converted_registry.register_photo_path(photo_id, file_sz, path)

    task_info = collect_download_task(
        photo,
        file_size,
        destination_path,
        files,
        folder_format,
        converted_registry,
    )

    if task_info is None:
        return None

    # Convert back to legacy format for compatibility
    return {
        "photo": task_info.photo,
        "file_size": task_info.file_size,
        "photo_path": task_info.photo_path,
        "hardlink_source": task_info.hardlink_source,
        "hardlink_registry": hardlink_registry,
    }


def download_photo_task(download_info):
    """Download a single photo or create hardlink as part of parallel execution.

    Legacy function - maintains original implementation for backward compatibility.

    Args:
        download_info: Dictionary with download task information

    Returns:
        True if successful, False otherwise
    """
    photo = download_info["photo"]
    file_size = download_info["file_size"]
    photo_path = download_info["photo_path"]
    hardlink_source = download_info.get("hardlink_source")
    hardlink_registry = download_info.get("hardlink_registry")

    LOGGER.debug(f"[Thread] Starting processing of {photo_path}")

    try:
        # Try hardlink first if source exists
        if hardlink_source:
            if create_hardlink(hardlink_source, photo_path):
                LOGGER.debug(f"[Thread] Created hardlink for {photo_path}")
                return True
            else:
                # Fallback to download if hard link creation fails
                LOGGER.warning(f"Hard link creation failed, downloading {photo_path} instead")

        # Download the photo - this maintains the original function call for test compatibility
        result = download_photo(photo, file_size, photo_path)
        if result:
            # Register for future hard links if enabled
            if hardlink_registry is not None:
                photo_key = f"{photo.id}_{file_size}"
                hardlink_registry[photo_key] = photo_path
            LOGGER.debug(f"[Thread] Completed download of {photo_path}")
        return result
    except Exception as e:
        LOGGER.error(f"[Thread] Failed to process {photo_path}: {e!s}")
        return False


def sync_album(
    album,
    destination_path,
    file_sizes,
    extensions=None,
    files=None,
    folder_format=None,
    hardlink_registry=None,
    config=None,
):
    """Sync given album.

    Legacy function - now delegates to album_sync_orchestrator with conversion
    for legacy hardlink registry format.

    Args:
        album: Album object from iCloudPy
        destination_path: Path where photos should be saved
        file_sizes: List of file size variants to download
        extensions: List of allowed file extensions
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for hardlinks (legacy dict format)
        config: Configuration dictionary

    Returns:
        True on success, None on invalid input
    """
    # Convert legacy hardlink registry dict to new registry format if needed
    converted_registry = None
    if hardlink_registry is not None:
        from src.hardlink_registry import HardlinkRegistry

        converted_registry = HardlinkRegistry()
        for key, path in hardlink_registry.items():
            if "_" in key:
                parts = key.rsplit("_", 1)
                if len(parts) == 2:
                    photo_id, file_sz = parts
                    converted_registry.register_photo_path(photo_id, file_sz, path)

    result = sync_album_photos(
        album=album,
        destination_path=destination_path,
        file_sizes=file_sizes,
        extensions=extensions,
        files=files,
        folder_format=folder_format,
        hardlink_registry=converted_registry,
        config=config,
    )

    # Update legacy registry if provided and new registry was created
    if hardlink_registry is not None and converted_registry is not None:
        # This is a simplified approach - in practice, we'd need to track new entries
        # But for legacy compatibility, we'll maintain the existing behavior
        pass

    return result


def remove_obsolete(destination_path, files):
    """Remove local obsolete file.

    Legacy function - now delegates to photo_cleanup_utils.

    Args:
        destination_path: Path to search for obsolete files
        files: Set of files that should be kept

    Returns:
        Set of removed file paths
    """
    return remove_obsolete_files(destination_path, files)


def sync_photos(config, photos):
    """Sync all photos.

    Main orchestration function that coordinates the entire photo sync process.
    This function has been refactored to use the new modular architecture while
    maintaining backward compatibility.

    Args:
        config: Configuration dictionary
        photos: Photos object from iCloudPy

    Returns:
        Tuple of (total_successful, total_failed) download counts
    """
    # Parse configuration using centralized config parser
    destination_path = config_parser.prepare_photos_destination(config=config)
    library_destinations = config_parser.get_photos_library_destinations(config=config)
    filters = config_parser.get_photos_filters(config=config)
    files = set()
    download_all = config_parser.get_photos_all_albums(config=config)
    use_hardlinks = config_parser.get_photos_use_hardlinks(config=config)
    libraries = (
        []
        if filters["libraries"] is False
        else (
            filters["libraries"]
            if filters["libraries"] is not None
            else photos.libraries
        )
    )
    folder_format = config_parser.get_photos_folder_format(config=config)
    shared_albums_root = normalize_file_path(
        os.path.join(
            destination_path,
            config_parser.get_photos_shared_albums_destination(config=config),
        ),
    )

    # Initialize hard link registry using new modular approach
    hardlink_registry = create_hardlink_registry(use_hardlinks)

    total_successful, total_failed = 0, 0

    # Special handling for "All Photos" when hardlinks are enabled
    if use_hardlinks and download_all:
        sub_successful, sub_failed = _sync_all_photos_first_for_hardlinks(
            photos,
            libraries,
            destination_path,
            filters,
            files,
            folder_format,
            hardlink_registry,
            config,
            library_destinations=library_destinations,
        )
        total_successful += sub_successful
        total_failed += sub_failed

    # Sync albums based on configuration
    sub_successful, sub_failed = _sync_albums_by_configuration(
        photos,
        libraries,
        download_all,
        destination_path,
        filters,
        files,
        folder_format,
        hardlink_registry,
        config,
        library_destinations=library_destinations,
    )
    total_successful += sub_successful
    total_failed += sub_failed

    # Shared Albums are a separate Apple service, not entries in
    # ``photos.libraries``. Keep them album-shaped in their own namespace while
    # reusing the exact same download pipeline and hardlink registry.
    shared_albums_conflict = (
        config_parser.photos_shared_albums_destination_conflicts(config=config)
        or _regular_library_output_conflicts_with_shared_albums(
            photos=photos,
            libraries=libraries,
            download_all=download_all,
            filters=filters,
            destination_path=destination_path,
            library_destinations=library_destinations,
            shared_albums_root=shared_albums_root,
        )
    )
    if shared_albums_conflict:
        sub_successful, sub_failed, shared_albums_enumerated = 0, 0, False
    else:
        sub_successful, sub_failed, shared_albums_enumerated = _sync_shared_albums(
            photos=photos,
            selection=filters["shared_albums"],
            destination_path=shared_albums_root,
            filters=filters,
            files=files,
            folder_format=folder_format,
            hardlink_registry=hardlink_registry,
            config=config,
        )
    total_successful += sub_successful
    total_failed += sub_failed

    # Clean up obsolete files if enabled. When per-library destinations are
    # configured we walk each library's subdir independently, otherwise the
    # legacy single-destination walk preserves backward compatibility.
    if config_parser.get_photos_remove_obsolete(config=config):
        marker_filename = config_parser.get_mount_marker_filename(config=config)
        exclude = {marker_filename}
        # If Shared Albums were disabled or unavailable, preserve any prior
        # Shared Album files during a broader legacy destination cleanup. An
        # unavailable private endpoint must never look like a server-side
        # deletion of every Shared Album.
        if not shared_albums_enumerated and os.path.isdir(shared_albums_root):
            for root, _dirs, shared_files in os.walk(shared_albums_root):
                for filename in shared_files:
                    files.add(normalize_file_path(os.path.join(root, filename)))

        cleanup_destinations = []
        if library_destinations:
            for library in libraries:
                lib_dest = _library_destination(destination_path, library, library_destinations)
                if lib_dest not in cleanup_destinations:
                    cleanup_destinations.append(lib_dest)
        else:
            cleanup_destinations.append(destination_path)
        if shared_albums_enumerated and shared_albums_root not in cleanup_destinations:
            cleanup_destinations.append(shared_albums_root)
        for cleanup_destination in cleanup_destinations:
            remove_obsolete_files(
                cleanup_destination,
                files,
                exclude_filenames=exclude,
            )

    return total_successful, total_failed


def _regular_library_output_conflicts_with_shared_albums(
    photos: Any,
    libraries: Iterable[str],
    download_all: bool,
    filters: dict[str, Any],
    destination_path: str,
    library_destinations: dict[str, str],
    shared_albums_root: str,
) -> bool:
    """Detect a regular-library album planned at the Shared Albums root.

    This protects legacy configurations without ``library_destinations``:
    their libraries continue writing directly beneath ``photos.destination``,
    but an album literally named like the reserved Shared Albums namespace
    must not be mixed with Apple Shared Album contents.

    Args:
        photos: iCloudPy Photos service
        libraries: Regular/Shared Photo Library names selected for syncing
        download_all: Value of ``photos.all_albums``
        filters: Parsed photo filters
        destination_path: Base Photos destination
        library_destinations: Optional per-library destination mapping
        shared_albums_root: Resolved Apple Shared Albums root

    Returns:
        True when a planned regular-library output equals the reserved root
    """
    shared_key = normalize_file_path(shared_albums_root).casefold()
    for library in libraries:
        library_destination = _library_destination(
            destination_path,
            library,
            library_destinations,
            create=False,
        )
        if download_all and library == "PrimarySync":
            album_names = [
                album_name
                for album_name in photos.libraries[library].albums
                if not filters["albums"] or album_name not in filters["albums"]
            ]
        elif filters["albums"] and library == "PrimarySync":
            album_names = list(filters["albums"])
        elif filters["albums"]:
            album_names = [
                album_name
                for album_name in filters["albums"]
                if album_name in photos.libraries[library].albums
            ]
        else:
            album_names = ["all"]

        for album_name in album_names:
            planned = normalize_file_path(
                os.path.join(library_destination, album_name),
            ).casefold()
            if planned == shared_key:
                LOGGER.error(
                    f"Photo library {library!r} album {album_name!r} is planned at "
                    f"the reserved iCloud Shared Albums root {shared_albums_root!r}; "
                    "iCloud Shared Albums will be skipped to prevent source trees "
                    "from merging. Configure photos.shared_albums_destination or "
                    "photos.library_destinations to use distinct paths.",
                )
                return True
    return False


def _safe_shared_album_component(album_name: str) -> str:
    """Convert a Shared Album name to one safe, NFC filesystem component.

    Args:
        album_name: Album name returned by iCloud

    Returns:
        Sanitized non-empty directory name
    """
    normalized = unicodedata.normalize("NFC", str(album_name))
    unsafe = '<>:"/\\|?*'
    component = "".join(
        "_" if character in unsafe or ord(character) < 32 else character
        for character in normalized
    )
    component = component.strip().rstrip(".")
    return component if component not in {"", ".", ".."} else "unnamed"


def _shared_album_directory_names(
    shared_albums: Mapping[str, Any],
) -> dict[str, str]:
    """Resolve stable directory names, suffixing sanitized collisions.

    Collision comparison uses Unicode case-folding so the paths are also safe
    on the common case-insensitive macOS filesystems. Every member of a
    collision group receives a suffix, making the outcome independent of API
    iteration order.

    Args:
        shared_albums: Shared Albums keyed by display name. Each album must
            expose a stable ``id`` (or legacy ``album_guid``) identifier.

    Returns:
        Mapping of original album name to deterministic directory component
    """
    components = {
        album_name: _safe_shared_album_component(album_name)
        for album_name in shared_albums
    }
    collision_counts: dict[str, int] = {}
    for component in components.values():
        key = component.casefold()
        collision_counts[key] = collision_counts.get(key, 0) + 1

    resolved = {}
    for album_name, component in components.items():
        if collision_counts[component.casefold()] > 1:
            album = shared_albums[album_name]
            stable_id = getattr(album, "id", None) or getattr(
                album,
                "album_guid",
                None,
            )
            if stable_id is None:
                LOGGER.warning(
                    f"iCloud Shared Album {album_name!r} has no stable identifier; "
                    "using its display name for the collision suffix.",
                )
                stable_id = album_name
            digest = hashlib.sha256(str(stable_id).encode("utf-8")).hexdigest()[:10]
            component = f"{component}__{digest}"
        resolved[album_name] = component
    return resolved


def _get_shared_albums(photos: Any) -> tuple[Mapping[str, Any], bool]:
    """Read Shared Albums without allowing the private service to break Photos.

    Args:
        photos: iCloudPy Photos service

    Returns:
        Tuple of (album mapping, successfully enumerated flag)
    """
    try:
        shared_albums = photos.shared_albums
    except AttributeError:
        LOGGER.info(
            "iCloud Shared Albums are unavailable in this account/client; "
            "continuing with photo libraries.",
        )
        return {}, False
    except Exception as error:  # noqa: BLE001 - private API must be isolated
        LOGGER.warning(
            f"Unable to enumerate iCloud Shared Albums; continuing with photo "
            f"libraries: {type(error).__name__}: {error!s}",
        )
        return {}, False

    if not isinstance(shared_albums, Mapping):
        LOGGER.warning(
            "iCloud Shared Albums returned an unexpected response; continuing "
            "with photo libraries.",
        )
        return {}, False
    return shared_albums, True


def _select_shared_albums(
    shared_albums: Mapping[str, Any],
    selection: list[str] | bool | None,
) -> dict[str, Any]:
    """Apply the independent Shared Albums selection.

    Args:
        shared_albums: Available Shared Albums keyed by exact name
        selection: None for all, False for disabled, or exact names

    Returns:
        Selected album mapping in deterministic name order
    """
    if selection is False:
        return {}
    names = sorted(shared_albums) if selection is None else selection
    selected = {}
    for album_name in names:
        if album_name in shared_albums:
            selected[album_name] = shared_albums[album_name]
        else:
            LOGGER.warning(
                f"iCloud Shared Album {album_name!r} was not found; skipping it.",
            )
    return selected


def _sync_shared_albums(
    photos: Any,
    selection: list[str] | bool | None,
    destination_path: str,
    filters: dict[str, Any],
    files: set[str],
    folder_format: str | None,
    hardlink_registry: Any,
    config: dict,
) -> tuple[int, int, bool]:
    """Sync selected iCloud Shared Albums through the normal album pipeline.

    Args:
        photos: iCloudPy Photos service
        selection: None for all, False for disabled, or exact album names
        destination_path: Dedicated Shared Albums root
        filters: Parsed photo filters
        files: Set of server-backed local paths for cleanup
        folder_format: Optional date-folder format
        hardlink_registry: Cross-album hardlink registry, if enabled
        config: Configuration dictionary

    Returns:
        Tuple of (successful downloads, failures, enumeration succeeded)
    """
    if selection is False:
        LOGGER.info("iCloud Shared Albums syncing is disabled by configuration.")
        return 0, 0, False

    shared_albums, enumerated = _get_shared_albums(photos)
    if not enumerated:
        return 0, 0, False

    selected = _select_shared_albums(shared_albums, selection)
    if not selected:
        LOGGER.info("No iCloud Shared Albums selected for syncing.")
        return 0, 0, True

    directory_names = _shared_album_directory_names(selected)
    total_successful, total_failed = 0, 0
    for album_name, album in selected.items():
        album_destination = os.path.join(
            destination_path,
            directory_names[album_name],
        )
        LOGGER.info(
            f"Syncing iCloud Shared Album {album_name!r} to {album_destination}",
        )
        try:
            result = sync_album_photos(
                album=album,
                destination_path=album_destination,
                file_sizes=filters["file_sizes"],
                extensions=filters["extensions"],
                files=files,
                folder_format=folder_format,
                hardlink_registry=hardlink_registry,
                config=config,
            )
        except Exception as error:  # noqa: BLE001 - isolate each Shared Album
            LOGGER.error(
                f"Failed to sync iCloud Shared Album {album_name!r}; continuing: "
                f"{type(error).__name__}: {error!s}",
            )
            total_failed += 1
            continue
        if result is not None:
            successful, failed = result
            total_successful += successful
            total_failed += failed
    return total_successful, total_failed, True


def _library_destination(
    base_destination: str,
    library: str,
    library_destinations: dict | None,
    *,
    create: bool = True,
) -> str:
    """Resolve the on-disk destination for a given iCloud photo library.

    When ``library_destinations`` provides a mapping for ``library``, joins
    the configured subdirectory under ``base_destination`` and ensures the
    directory exists when ``create`` is true. Otherwise returns
    ``base_destination`` unchanged
    (preserving mandarons' legacy single-destination behaviour).

    Library-name matching has three rules, in priority order:

    1. **Exact match.** ``library_destinations[library]`` if present.
    2. **Role alias for `SharedLibrary`.** Apple's modern iCloud Shared
       Photo Library is exposed by icloudpy under a GUID-based zone name
       like ``SharedSync-3C977B4A-C15A-46E4-9854-585B9342C409``. A config
       key of ``SharedLibrary`` matches any zone whose name starts with
       ``SharedSync-`` so users don't need to discover and hardcode the
       per-account GUID. (Configs that already use the literal current
       Apple zone name still work via rule 1.)
    3. **Fallthrough.** Returns ``base_destination`` unchanged.

    Args:
        base_destination: Root Photos destination
        library: iCloud photo library name
        library_destinations: Optional library-to-subdirectory mapping
        create: Create a configured destination directory when true

    Returns:
        Resolved destination for the library
    """
    if not library_destinations:
        return base_destination
    # ``get`` returns None only when the key is absent -- the config parser
    # coerces every configured value to str, so an explicit "" stays "".
    # Key on ``is None`` (not falsiness) so an explicitly-mapped library
    # always wins over the SharedLibrary alias and the default, honouring
    # the rule 1 > rule 2 > rule 3 priority documented above.
    subdir = library_destinations.get(library)
    if subdir is None and library.startswith("SharedSync-"):
        subdir = library_destinations.get("SharedLibrary")
    if subdir is None:
        return base_destination
    dest = os.path.join(base_destination, subdir)
    if create:
        os.makedirs(dest, exist_ok=True)
    return dest


def _sync_all_photos_first_for_hardlinks(
    photos,
    libraries,
    destination_path,
    filters,
    files,
    folder_format,
    hardlink_registry,
    config,
    library_destinations: dict | None = None,
) -> tuple[int, int]:
    """Sync 'All Photos' album first to populate hardlink registry.

    Args:
        photos: Photos object from iCloudPy
        libraries: List of photo libraries to sync
        destination_path: Base destination path
        filters: Photo filters configuration
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) download counts
    """
    for library in libraries:
        if library == "PrimarySync" and "All Photos" in photos.libraries[library].albums:
            LOGGER.info("Syncing 'All Photos' album first for hard link reference...")
            lib_dest = _library_destination(destination_path, library, library_destinations or {})
            result = sync_album_photos(
                album=photos.libraries[library].albums["All Photos"],
                destination_path=os.path.join(lib_dest, "All Photos"),
                file_sizes=filters["file_sizes"],
                extensions=filters["extensions"],
                files=files,
                folder_format=folder_format,
                hardlink_registry=hardlink_registry,
                config=config,
            )
            if hardlink_registry:
                LOGGER.info(
                    f"'All Photos' sync complete. Hard link registry populated with "
                    f"{hardlink_registry.get_registry_size()} reference files.",
                )
            if result is not None:
                return result
            break
    return 0, 0


def _sync_albums_by_configuration(
    photos,
    libraries,
    download_all,
    destination_path,
    filters,
    files,
    folder_format,
    hardlink_registry,
    config,
    library_destinations: dict | None = None,
) -> tuple[int, int]:
    """Sync albums based on configuration settings.

    Args:
        photos: Photos object from iCloudPy
        libraries: List of photo libraries to sync
        download_all: Whether to download all albums
        destination_path: Base destination path
        filters: Photo filters configuration
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) aggregated across all libraries
    """
    total_successful, total_failed = 0, 0
    for library in libraries:
        lib_dest = _library_destination(destination_path, library, library_destinations or {})
        if download_all and library == "PrimarySync":
            sub_successful, sub_failed = _sync_all_albums_except_filtered(
                photos,
                library,
                filters,
                lib_dest,
                files,
                folder_format,
                hardlink_registry,
                config,
            )
        elif filters["albums"] and library == "PrimarySync":
            sub_successful, sub_failed = _sync_filtered_albums(
                photos,
                library,
                filters,
                lib_dest,
                files,
                folder_format,
                hardlink_registry,
                config,
            )
        elif filters["albums"]:
            sub_successful, sub_failed = _sync_filtered_albums_in_library(
                photos,
                library,
                filters,
                lib_dest,
                files,
                folder_format,
                hardlink_registry,
                config,
            )
        else:
            sub_successful, sub_failed = _sync_all_photos_in_library(
                photos,
                library,
                lib_dest,
                filters,
                files,
                folder_format,
                hardlink_registry,
                config,
            )
        total_successful += sub_successful
        total_failed += sub_failed
    return total_successful, total_failed


def _sync_all_albums_except_filtered(
    photos,
    library,
    filters,
    destination_path,
    files,
    folder_format,
    hardlink_registry,
    config,
) -> tuple[int, int]:
    """Sync all albums except those in the filter exclusion list.

    Args:
        photos: Photos object from iCloudPy
        library: Library name to sync
        filters: Photo filters configuration
        destination_path: Base destination path
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) aggregated across all synced albums
    """
    total_successful, total_failed = 0, 0
    for album in photos.libraries[library].albums.keys():
        # Skip All Photos if we already synced it first
        if hardlink_registry and album == "All Photos":
            continue
        if filters["albums"] and album in iter(filters["albums"]):
            continue
        result = sync_album_photos(
            album=photos.libraries[library].albums[album],
            destination_path=os.path.join(destination_path, album),
            file_sizes=filters["file_sizes"],
            extensions=filters["extensions"],
            files=files,
            folder_format=folder_format,
            hardlink_registry=hardlink_registry,
            config=config,
        )
        if result is not None:
            sub_successful, sub_failed = result
            total_successful += sub_successful
            total_failed += sub_failed
    return total_successful, total_failed


def _sync_filtered_albums(
    photos,
    library,
    filters,
    destination_path,
    files,
    folder_format,
    hardlink_registry,
    config,
) -> tuple[int, int]:
    """Sync only albums specified in filters.

    Args:
        photos: Photos object from iCloudPy
        library: Library name to sync
        filters: Photo filters configuration
        destination_path: Base destination path
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) aggregated across all synced albums
    """
    total_successful, total_failed = 0, 0
    for album in iter(filters["albums"]):
        result = sync_album_photos(
            album=photos.libraries[library].albums[album],
            destination_path=os.path.join(destination_path, album),
            file_sizes=filters["file_sizes"],
            extensions=filters["extensions"],
            files=files,
            folder_format=folder_format,
            hardlink_registry=hardlink_registry,
            config=config,
        )
        if result is not None:
            sub_successful, sub_failed = result
            total_successful += sub_successful
            total_failed += sub_failed
    return total_successful, total_failed


def _sync_filtered_albums_in_library(
    photos,
    library,
    filters,
    destination_path,
    files,
    folder_format,
    hardlink_registry,
    config,
) -> tuple[int, int]:
    """Sync filtered albums in a specific library.

    Args:
        photos: Photos object from iCloudPy
        library: Library name to sync
        filters: Photo filters configuration
        destination_path: Base destination path
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) aggregated across all synced albums
    """
    total_successful, total_failed = 0, 0
    for album in iter(filters["albums"]):
        if album in photos.libraries[library].albums:
            result = sync_album_photos(
                album=photos.libraries[library].albums[album],
                destination_path=os.path.join(destination_path, album),
                file_sizes=filters["file_sizes"],
                extensions=filters["extensions"],
                files=files,
                folder_format=folder_format,
                hardlink_registry=hardlink_registry,
                config=config,
            )
            if result is not None:
                sub_successful, sub_failed = result
                total_successful += sub_successful
                total_failed += sub_failed
        else:
            LOGGER.warning(f"Album {album} not found in {library}. Skipping the album {album} ...")
    return total_successful, total_failed


def _sync_all_photos_in_library(
    photos,
    library,
    destination_path,
    filters,
    files,
    folder_format,
    hardlink_registry,
    config,
) -> tuple[int, int]:
    """Sync all photos in a library.

    Args:
        photos: Photos object from iCloudPy
        library: Library name to sync
        destination_path: Base destination path
        filters: Photo filters configuration
        files: Set to track downloaded files
        folder_format: Folder format string
        hardlink_registry: Registry for tracking downloaded files
        config: Configuration dictionary

    Returns:
        Tuple of (total_successful, total_failed) download counts
    """
    result = sync_album_photos(
        album=photos.libraries[library].all,
        destination_path=os.path.join(destination_path, "all"),
        file_sizes=filters["file_sizes"],
        extensions=filters["extensions"],
        files=files,
        folder_format=folder_format,
        hardlink_registry=hardlink_registry,
        config=config,
    )
    if result is not None:
        return result
    return 0, 0
