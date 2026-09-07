from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


@dataclass(slots=True)
class DiscoveryResult:
    supported: list[Path]
    ignored: list[Path]


def discover_folder(folder: Path, recursive: bool = False) -> DiscoveryResult:
    folder = Path(folder).resolve()
    paths = folder.rglob("*") if recursive else folder.iterdir()
    files = [p.resolve() for p in paths if p.is_file()]
    return _classify(files)


def discover_files(paths: Iterable[Path]) -> DiscoveryResult:
    seen: set[Path] = set()
    files: list[Path] = []
    for raw in paths:
        p = Path(raw).resolve()
        if p in seen:
            continue
        seen.add(p)
        if p.is_file():
            files.append(p)
    return _classify(files)


def _classify(files: Iterable[Path]) -> DiscoveryResult:
    supported: list[Path] = []
    ignored: list[Path] = []
    for p in files:
        if p.suffix.lower() in SUPPORTED_SUFFIXES:
            supported.append(p)
        else:
            ignored.append(p)
    supported.sort(key=lambda p: p.name.lower())
    ignored.sort(key=lambda p: p.name.lower())
    return DiscoveryResult(supported=supported, ignored=ignored)
