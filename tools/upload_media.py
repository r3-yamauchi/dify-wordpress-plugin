# where: wordpress/tools/upload_media.py
# what: Implements the upload media tool via WordPress REST API.
# why: Allow Dify workflows to upload media files to WordPress.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from .file_utils import ResolvedFile, cleanup_files, resolve_files

logger = logging.getLogger(__name__)


class UploadMediaTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        resolved_file: ResolvedFile | None = None
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            file_param = tool_parameters.get("file")
            if not file_param:
                raise ValueError("ファイルを指定してください")

            # ファイルを解決
            resolved_files = resolve_files([file_param])
            if not resolved_files:
                raise ValueError("ファイルを解決できませんでした")
            
            resolved_file = resolved_files[0]

            # 追加パラメータ
            title = tool_parameters.get("title")
            caption = tool_parameters.get("caption")
            alt_text = tool_parameters.get("alt_text")
            description = tool_parameters.get("description")

            # リクエストデータの構築
            data: dict[str, Any] = {}
            
            if title:
                data["title"] = title.strip()
            
            if caption:
                data["caption"] = caption.strip()
            
            if alt_text:
                data["alt_text"] = alt_text.strip()
            
            if description:
                data["description"] = description.strip()

            # WordPress REST APIを呼び出し
            logger.debug("Uploading media file: %s", resolved_file.path)
            response = client.upload_media(file_path=resolved_file.path, data=data if data else None)

            # レスポンスの処理
            media_id = response.get("id")
            media_url = response.get("source_url", "")
            media_title = response.get("title", {}).get("rendered", title or "")

            logger.info("Uploaded WordPress media (ID: %s, URL: %s)", media_id, media_url)

            result_text = f"WordPressにメディアをアップロードしました (ID: {media_id})"
            if media_url:
                result_text += f"\nURL: {media_url}"

            response_data = {
                "id": media_id,
                "title": media_title,
                "url": media_url,
                "source_url": media_url,
                "mime_type": response.get("mime_type"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressメディアアップロード")
        finally:
            if resolved_file:
                cleanup_files([resolved_file])




