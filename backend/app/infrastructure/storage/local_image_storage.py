"""Implementação em sistema de arquivos da porta `ImageStorage`."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class LocalImageStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, key: str) -> Path:
        path = (self._root / key).resolve()
        # Proteção contra path traversal ("../../etc/passwd")
        if self._root not in path.parents:
            raise ValueError(f"Chave de armazenamento inválida: {key!r}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Escrita atômica: arquivo temporário + rename
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return key

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()  # remove a pasta da inspeção se ficou vazia
        except OSError:
            pass
