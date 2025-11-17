# where: wordpress/tools/update_media.py
# what: Implements the update media tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress media metadata.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdateMediaTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            media_id = validators.validate_post_id(tool_parameters.get("id"))
            title = tool_parameters.get("title")
            caption = tool_parameters.get("caption")
            alt_text = tool_parameters.get("alt_text")
            description = tool_parameters.get("description")

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if title is not None:
                data["title"] = title.strip() if title else ""

            if caption is not None:
                data["caption"] = caption.strip() if caption else ""

            if alt_text is not None:
                data["alt_text"] = alt_text.strip() if alt_text else ""

            if description is not None:
                data["description"] = description.strip() if description else ""

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（title, caption, alt_text, description）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating media ID: %s with data keys: %s", media_id, list(data.keys()))
            response = client.update_media(media_id=media_id, data=data)

            # レスポンスの処理
            updated_media_id = response.get("id")
            updated_title = response.get("title", {}).get("rendered", title or "")
            updated_url = response.get("source_url", "")

            logger.info("Updated WordPress media (ID: %s)", updated_media_id)

            result_text = f"WordPressのメディアを更新しました (ID: {updated_media_id})"
            if updated_url:
                result_text += f"\nURL: {updated_url}"

            response_data = {
                "id": updated_media_id,
                "title": updated_title,
                "url": updated_url,
                "source_url": updated_url,
                "mime_type": response.get("mime_type"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressメディア更新")



