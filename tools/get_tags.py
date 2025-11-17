# where: wordpress/tools/get_tags.py
# what: Implements the get tags tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress tags.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetTagsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            per_page = validators.validate_per_page(tool_parameters.get("per_page"), max_per_page=100)
            page = validators.validate_page_number(tool_parameters.get("page"))
            search = validators.validate_search_query(tool_parameters.get("search"))

            # リクエストパラメータの構築
            params: dict[str, Any] = {
                "per_page": per_page,
                "page": page,
            }
            
            if search:
                params["search"] = search

            # WordPress REST APIを呼び出し
            logger.debug("Fetching tags with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_tags(params=params)

            # レスポンスの処理
            tags = response if isinstance(response, list) else []
            total_tags = len(tags)

            logger.info("Retrieved %d tags from WordPress", total_tags)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_tags}件のタグを取得しました"
            if total_tags == 0:
                result_text = "WordPressからタグが見つかりませんでした"

            response_data = {
                "total": total_tags,
                "tags": tags,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressタグ取得")
