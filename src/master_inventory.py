"""Pure, guarded master input/snapshot traversal; no locking or model authority.

Checks reject static reparse paths before directory enumeration or byte reads.
The caller retains its existing time/candidate/round budgets.
"""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import shutil
import stat

from master_contracts import digest, file_hash, safe_path

SOURCE_DIRS = ('data', 'predictions', 'features', 'models', 'protocols', 'policies',
               'config', 'schemas', 'src', 'scripts', 'docs', '.github',
               'evidence', 'model_specs',
               'artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts')
LEGACY_INPUT = 'reports/legacy_chronological_walkforward.json'
RESEARCH_REQUEST_PATH = 'config/research-model-request.json'


def local_path(root: Path, relative: str = '') -> Path:
    root = Path(root)
    windows = PureWindowsPath(relative)
    if windows.drive or windows.is_absolute() or '..' in windows.parts:
        raise ValueError('Unsafe relative path')
    path = safe_path(root, relative) if relative else root
    absolute = path.absolute()
    for current in reversed((absolute, *absolute.parents)):
        try:
            attributes = current.lstat()
        except FileNotFoundError:
            continue
        if (current.is_symlink() or getattr(current, 'is_junction', lambda: False)() or
                getattr(attributes, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
            raise ValueError('Reparse inventory path is forbidden')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Inventory path resolves outside root')
    return path


def has_research_request(root: Path) -> bool:
    """A lightweight guarded opt-in; legacy adapters need no research imports."""
    return local_path(Path(root), RESEARCH_REQUEST_PATH).exists()


def iter_files(root: Path, relative: str = '', *, ignore_cache: bool = False):
    """Walk iteratively; guard a directory before scandir can enter its target."""
    base = local_path(root, relative)
    if not base.is_dir():
        return
    pending = [base]
    while pending:
        directory = pending.pop()
        directory = local_path(root, directory.relative_to(root).as_posix() if directory != root else '')
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            path = local_path(root, (directory / entry.name).relative_to(root).as_posix())
            if ignore_cache and (entry.name == '__pycache__' or path.suffix == '.pyc'):
                continue
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                yield path


def inventory(root: Path) -> dict:
    root = local_path(root)
    paths = set()
    for name in SOURCE_DIRS:
        paths.update(iter_files(root, name, ignore_cache=True))
    if root.exists():
        with os.scandir(root) as entries:
            for entry in entries:
                if Path(entry.name).match('requirements*.txt'):
                    paths.add(local_path(root, entry.name))
    for name in ('pyproject.toml', 'uv.lock', 'poetry.lock', 'AGENTS.md', LEGACY_INPUT):
        path = local_path(root, name)
        if path.exists():
            paths.add(path)
    result = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        checked = local_path(root, relative)
        result[relative] = {'sha256': file_hash(checked), 'size_bytes': checked.stat().st_size}
    return result


def snapshot_matches(snapshot: Path, inputs: dict) -> bool:
    actual = inventory(snapshot)
    # REPLAY is an output namespace. Existing replay inputs remain hash checked.
    actual = {p: value for p, value in actual.items()
              if p in inputs or not p.startswith('predictions/replay/')}
    return actual == inputs


def generated_artifacts(snapshot: Path, inputs: dict) -> dict:
    artifacts = {}
    for path in sorted(iter_files(snapshot)):
        relative = path.relative_to(snapshot).as_posix()
        if relative not in inputs:
            artifacts['snapshot/' + relative] = file_hash(local_path(snapshot, relative))
    return artifacts


def copy_inputs(root: Path, snapshot: Path, inputs: dict) -> None:
    for relative, info in inputs.items():
        source = local_path(root, relative)
        dest = local_path(snapshot, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Recheck the destination chain after creating missing directories.
        dest = local_path(snapshot, relative)
        shutil.copyfile(source, dest)
        if file_hash(local_path(snapshot, relative)) != info['sha256']:
            raise ValueError(f'INPUT_CHANGED: {relative}')


def runtime_code_hash(base: Path) -> str:
    base = Path(base)
    paths = [path for folder in ('src', 'scripts') for path in iter_files(base, folder)
             if path.suffix == '.py']
    return digest({path.relative_to(base).as_posix(): file_hash(local_path(base, path.relative_to(base).as_posix()))
                   for path in sorted(paths)})
