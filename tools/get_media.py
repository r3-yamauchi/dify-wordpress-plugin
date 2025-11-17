# where: wordpress/tools/get_media.py
# what: Implements the get media tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress media.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetMediaTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            per_page = validators.validate_per_page(tool_parameters.get("per_page"), max_per_page=100)
            page = validators.validate_page_number(tool_parameters.get("page"))
            search = validators.validate_search_query(tool_parameters.get("search"))
            media_type = tool_parameters.get("media_type")
            mime_type = tool_parameters.get("mime_type")

            # リクエストパラメータの構築
            params: dict[str, Any] = {
                "per_page": per_page,
                "page": page,
            }
            
            if search:
                params["search"] = search
            
            if media_type:
                params["media_type"] = media_type
            
            if mime_type:
                params["mime_type"] = mime_type

            # WordPress REST APIを呼び出し
            logger.debug("Fetching media with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_media(params=params)

            # レスポンスの処理
            media_items = response if isinstance(response, list) else []
            total_media = len(media_items)

            logger.info("Retrieved %d media items from WordPress", total_media)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_media}件のメディアを取得しました"
            if total_media == 0:
                result_text = "WordPressからメディアが見つかりませんでした"

            response_data = {
                "total": total_media,
                "media": media_items,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressメディア取得")




