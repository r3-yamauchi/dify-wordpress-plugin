# where: wordpress/tools/get_pages.py
# what: Implements the get pages tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress pages.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetPagesTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            per_page = validators.validate_per_page(tool_parameters.get("per_page"), max_per_page=100)
            page = validators.validate_page_number(tool_parameters.get("page"))
            search = validators.validate_search_query(tool_parameters.get("search"))
            status = tool_parameters.get("status")
            
            # ステータスの検証
            if status:
                validators.validate_post_status(status)

            # リクエストパラメータの構築
            params: dict[str, Any] = {
                "per_page": per_page,
                "page": page,
            }
            
            if search:
                params["search"] = search
            
            if status:
                params["status"] = status

            # WordPress REST APIを呼び出し
            logger.debug("Fetching pages with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_pages(params=params)

            # レスポンスの処理
            pages = response if isinstance(response, list) else []
            total_pages = len(pages)

            logger.info("Retrieved %d pages from WordPress", total_pages)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_pages}件のページを取得しました"
            if total_pages == 0:
                result_text = "WordPressからページが見つかりませんでした"

            response_data = {
                "total": total_pages,
                "pages": pages,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressページ取得")



