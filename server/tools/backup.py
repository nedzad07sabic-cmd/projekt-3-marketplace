"""Create a private, atomic database+media backup during an explicit maintenance window.

Never stops services, deletes old backups or restores production automatically.
Requires the operator to stop web/jobs/proxy and any external writers first.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import uuid
from verify_backup import BackupError, digest, verify

DEPLOY = Path(__file__).resolve().parents[1] / 'deploy'
REPOSITORY = DEPLOY.parents[1]


def compose(*args: str) -> list[str]:
    return ['docker', 'compose', '--project-directory', str(DEPLOY),
            '--file', str(DEPLOY / 'compose.yml'), '--env-file', str(DEPLOY / '.env'), *args]


def run_step(args: list[str], *, output=None) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(args, stdout=output if output is not None else subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupError('Backup command unavailable or timed out; no completed bundle published.') from exc
    if result.returncode:
        # Do not copy command stderr: it can contain configuration or credentials.
        raise BackupError(f'Backup command failed (exit {result.returncode}); no completed bundle published.')
    return result


def writers_stopped() -> None:
    result = run_step(compose('ps', '--status', 'running', '--services', 'web', 'jobs', 'proxy'))
    if result.stdout.strip():
        raise BackupError('Stop web, jobs and proxy in a planned maintenance window before backing up.')


def create_backup(destination: Path, *, maintenance_confirmed: bool = False) -> Path:
    if not maintenance_confirmed:
        raise BackupError('Confirm external writers are stopped with --maintenance-confirmed.')
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise BackupError('Backup destination must not be a symlink.')
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = destination.resolve()
    if destination.is_relative_to(REPOSITORY.resolve()):
        raise BackupError('Keep backups outside the source repository.')
    if stat.S_IMODE(destination.stat().st_mode) & 0o077:
        raise BackupError('Backup directory must have private permissions (0700).')
    writers_stopped()
    temporary = Path(tempfile.mkdtemp(prefix='.incomplete-zadenvo-', dir=destination))
    try:
        database = temporary / 'database.dump'
        with database.open('xb') as out:
            run_step(compose('exec', '-T', 'db', 'pg_dump', '-U', 'marketplace',
                             '--format=custom', '--no-owner', '--no-privileges', 'marketplace'), output=out)
            out.flush(); os.fsync(out.fileno())
        media = temporary / 'media.tar.gz'
        with media.open('xb') as out:
            # One-off read-only operation. Override the application entrypoint;
            # this container runs only tar, never the web server or background jobs.
            run_step(compose('run', '--rm', '--no-deps', '-T', '--entrypoint', 'tar',
                             'web', '-C', '/data', '-czf', '-', 'media'), output=out)
            out.flush(); os.fsync(out.fileno())
        writers_stopped()
        created = datetime.now(timezone.utc)
        manifest = {'format': 'zadenvo-backup-v1', 'created_at_utc': created.isoformat(),
                    'consistent_mode': 'writers-stopped',
                    'files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                              for p in (database, media)}}
        with (temporary / 'manifest.json').open('x', encoding='utf-8') as out:
            json.dump(manifest, out, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
        for path in temporary.iterdir():
            path.chmod(0o600)
        verify(temporary)
        final = destination / ('zadenvo-' + created.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12])
        temporary.rename(final)
        return final
    finally:
        # Only remove this run's private incomplete directory, never older backups.
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--maintenance-confirmed', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        output = create_backup(args.destination, maintenance_confirmed=args.maintenance_confirmed)
    except (BackupError, OSError) as exc:
        print(f'BLOCK: {exc if isinstance(exc, BackupError) else "Backup filesystem operation failed."}')
        return 2
    print(f'Backup completed in {output}')
    print('Encrypt and copy off-site; verify restoration separately. Services remain stopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
