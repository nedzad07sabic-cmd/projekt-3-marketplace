"""Validate a Zadenvo backup bundle without restoring or extracting anything.

Hashes detect corruption, not malicious replacement. Only use trusted backups.
A valid header/hash is NOT evidence that PostgreSQL can restore the dump.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

FILES = ('database.dump', 'media.tar.gz')
MAX_MEDIA_BYTES = 20 * 1024**3
MAX_MEMBERS = 1_000_000


class BackupError(ValueError):
    pass


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify(bundle: Path, *, max_media_bytes: int = MAX_MEDIA_BYTES) -> dict:
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise BackupError('Backup must be a regular directory, not a symlink.')
    manifest_path = bundle / 'manifest.json'
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 16384:
        raise BackupError('Missing or invalid manifest.')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if (manifest.get('format') != 'zadenvo-backup-v1'
                or manifest.get('consistent_mode') != 'writers-stopped'
                or set(manifest.get('files', {})) != set(FILES)):
            raise BackupError('Unsupported backup manifest.')
        for name in FILES:
            path = bundle / name
            meta = manifest['files'][name]
            if path.is_symlink() or not path.is_file():
                raise BackupError('Backup contains a missing or linked artifact.')
            if not isinstance(meta, dict) or not re.fullmatch('[0-9a-f]{64}', str(meta.get('sha256', ''))):
                raise BackupError('Invalid artifact digest.')
            if path.stat().st_size != meta.get('bytes') or digest(path) != meta['sha256']:
                raise BackupError('Backup size or checksum mismatch.')
        with (bundle / 'database.dump').open('rb') as stream:
            if stream.read(5) != b'PGDMP':
                raise BackupError('Expected a PostgreSQL custom-format dump.')
        # Read to the end to check gzip CRC/truncation; tarfile alone can stop at
        # the first end-of-archive record without consuming the gzip trailer.
        expanded = 0
        with gzip.open(bundle / 'media.tar.gz', 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                expanded += len(chunk)
                if expanded > max_media_bytes:
                    raise BackupError('Media archive exceeds the configured validation limit.')
        seen: set[str] = set()
        total_size = 0
        count = 0
        with tarfile.open(bundle / 'media.tar.gz', 'r:gz') as archive:
            for member in archive:
                count += 1
                path = PurePosixPath(member.name)
                if (count > MAX_MEMBERS or path.is_absolute() or '..' in path.parts
                        or not path.parts or path.parts[0] != 'media'
                        or '\\' in member.name or not (member.isfile() or member.isdir())
                        or member.name in ('', '.') or any(ord(c) < 32 for c in member.name)):
                    raise BackupError('Unsafe or unsupported media archive entry.')
                normalized = str(path)
                if normalized == 'media' and not member.isdir():
                    raise BackupError('Media root must be a directory.')
                if normalized in seen:
                    raise BackupError('Duplicate media archive entry.')
                seen.add(normalized)
                total_size += member.size
                if member.size < 0 or total_size > max_media_bytes:
                    raise BackupError('Media archive exceeds the configured validation limit.')
        if 'media' not in seen:
            raise BackupError('Media root directory is missing.')
        return {'format': manifest['format'], 'artifacts': len(FILES),
                'media_entries': count, 'media_bytes': total_size,
                'database_restore_tested': False}
    except BackupError:
        raise
    except (OSError, EOFError, ValueError, TypeError, AttributeError, tarfile.TarError) as exc:
        raise BackupError('Backup bundle could not be validated.') from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.bundle)
    except BackupError as exc:
        print(f'BLOCK: {exc}')
        return 2
    print(json.dumps(result, sort_keys=True))
    print('Integrity verified. A real isolated PostgreSQL restore drill is still required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
