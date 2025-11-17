# where: wordpress/tools/file_utils.py
# what: Shared helpers for turning Dify file inputs into local filesystem paths.
# why: wordpress SDK expects file paths when attaching documents.

from __future__ import annotations

import base64
import binascii
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

import requests

_DOWNLOAD_TIMEOUT = 30
_CHUNK_SIZE = 512 * 1024
_MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024  # 10 MB maximum download size


class ResolvedFile:
    __slots__ = ("path", "cleanup")

    def __init__(self, path: str, cleanup: bool) -> None:
        self.path = path
        self.cleanup = cleanup


def resolve_files(inputs: Iterable[Any]) -> list[ResolvedFile]:
    resolved: list[ResolvedFile] = []
    for item in inputs:
        path, cleanup = _resolve_single(item)
        resolved.append(ResolvedFile(path, cleanup))
    return resolved


def cleanup_files(files: Iterable[ResolvedFile]) -> None:
    for file in files:
        if file.cleanup:
            try:
                Path(file.path).unlink(missing_ok=True)
            except Exception:  # pragma: no cover - best effort cleanup
                pass


def _resolve_single(file_info: Any) -> tuple[str, bool]:
    if isinstance(file_info, (str, os.PathLike)):
        return _resolve_pathlike(file_info)

    serialized = _serialize_file_info(file_info)
    explicit_path = serialized.get("path")
    if explicit_path:
        return _resolve_pathlike(explicit_path)

    content = serialized.get("content") or serialized.get("data")
    if content:
        payload = _coerce_bytes(content)
        suffix = _infer_suffix(serialized)
        return _write_temp(payload, suffix)

    url = serialized.get("url")
    if url:
        suffix = _infer_suffix(serialized)
        return _download(url, serialized, suffix)

    upload_id = serialized.get("upload_file_id")
    if upload_id:
        inferred = f"https://files.dify.ai/{upload_id}"
        suffix = _infer_suffix(serialized)
        return _download(inferred, serialized, suffix)

    raise ValueError("ファイル情報に path/url/content のいずれも含まれていません")


def _resolve_pathlike(value: os.PathLike[str] | str) -> tuple[str, bool]:
    path_str = os.fspath(value).strip()
    if not path_str:
        raise ValueError("ファイルパスが空です")

    if path_str.startswith("http://") or path_str.startswith("https://"):
        return _download(path_str, None, None)

    expanded = os.path.expanduser(path_str)
    if not os.path.isfile(expanded):
        raise FileNotFoundError(f"{path_str} はファイルではありません")
    return expanded, False


def _serialize_file_info(file_info: Any) -> dict[str, Any]:
    if isinstance(file_info, dict):
        return dict(file_info)

    exportable: dict[str, Any] = {}
    for attr in ("path", "url", "content", "data", "filename", "name", "mime_type", "upload_file_id", "headers", "authorization", "auth"):
        if hasattr(file_info, attr):
            exportable[attr] = getattr(file_info, attr)

    if exportable:
        return exportable

    if hasattr(file_info, "model_dump"):
        return dict(file_info.model_dump())

    raise ValueError("ファイルパラメータの構造を解釈できません")


def _coerce_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return base64.b64decode(stripped, validate=True)
        except (binascii.Error, ValueError):
            return stripped.encode("utf-8")
    raise ValueError("content/data には bytes か base64文字列を指定してください")


def _write_temp(payload: bytes, suffix: str | None) -> tuple[str, bool]:
    handle, temp_path = tempfile.mkstemp(suffix=suffix or "")
    with os.fdopen(handle, "wb") as fp:
        fp.write(payload)
    return temp_path, True


def _download(url: str, file_meta: dict[str, Any] | None, suffix: str | None) -> tuple[str, bool]:
    normalized = url.strip()
    if not normalized:
        raise ValueError("ファイルURLが空です")

    headers: dict[str, str] = {}
    if file_meta:
        raw_headers = file_meta.get("headers")
        if isinstance(raw_headers, dict):
            for key, value in raw_headers.items():
                if isinstance(key, str) and isinstance(value, str) and key.strip():
                    headers[key.strip()] = value
        auth_token = file_meta.get("authorization") or file_meta.get("auth")
        if isinstance(auth_token, str) and auth_token.strip():
            headers.setdefault("Authorization", auth_token.strip())

    response = requests.get(normalized, headers=headers or None, stream=True, timeout=_DOWNLOAD_TIMEOUT)
    response.raise_for_status()

    # Check Content-Length header if available
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            size = int(content_length)
            if size > _MAX_DOWNLOAD_SIZE:
                raise ValueError(
                    f"ファイルサイズが大きすぎます ({size / 1024 / 1024:.1f}MB)。"
                    f"最大 {_MAX_DOWNLOAD_SIZE / 1024 / 1024:.0f}MB まで対応しています"
                )
        except (ValueError, TypeError):
            pass  # Invalid Content-Length header, continue with size monitoring

    handle, temp_path = tempfile.mkstemp(suffix=suffix or "")
    downloaded_size = 0
    try:
        with os.fdopen(handle, "wb") as fp:
            for chunk in response.iter_content(_CHUNK_SIZE):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > _MAX_DOWNLOAD_SIZE:
                        raise ValueError(
                            f"ダウンロード中にファイルサイズが制限を超えました。"
                            f"最大 {_MAX_DOWNLOAD_SIZE / 1024 / 1024:.0f}MB まで対応しています"
                        )
                    fp.write(chunk)
        return temp_path, True
    except Exception:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:  # pragma: no cover
            pass
        raise


def _infer_suffix(file_meta: dict[str, Any] | None) -> str | None:
    if not file_meta:
        return None
    filename = file_meta.get("filename") or file_meta.get("name")
    if filename:
        suffix = Path(str(filename)).suffix
        if suffix:
            return suffix
    mime_type = file_meta.get("mime_type") or file_meta.get("content_type")
    if mime_type:
        guessed = mimetypes.guess_extension(str(mime_type))
        if guessed:
            return guessed
    return None
