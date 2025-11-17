# where: wordpress/tools/get_categories.py
# what: Implements the get categories tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress categories.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetCategoriesTool(base.BaseWordPressTool):
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
            logger.debug("Fetching categories with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_categories(params=params)

            # レスポンスの処理
            categories = response if isinstance(response, list) else []
            total_categories = len(categories)

            logger.info("Retrieved %d categories from WordPress", total_categories)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_categories}件のカテゴリーを取得しました"
            if total_categories == 0:
                result_text = "WordPressからカテゴリーが見つかりませんでした"

            response_data = {
                "total": total_categories,
                "categories": categories,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressカテゴリー取得")
