# where: wordpress/tools/get_comments.py
# what: Implements the get comments tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress comments.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetCommentsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            per_page = validators.validate_per_page(tool_parameters.get("per_page"), max_per_page=100)
            page = validators.validate_page_number(tool_parameters.get("page"))
            search = validators.validate_search_query(tool_parameters.get("search"))
            post_id = tool_parameters.get("post_id")
            status = tool_parameters.get("status")

            # リクエストパラメータの構築
            params: dict[str, Any] = {
                "per_page": per_page,
                "page": page,
            }
            
            if search:
                params["search"] = search
            
            if post_id:
                try:
                    post_id_int = int(post_id)
                    if post_id_int > 0:
                        params["post"] = post_id_int
                except (ValueError, TypeError):
                    logger.warning("Invalid post_id: %s, ignoring", post_id)
            
            if status:
                status_str = str(status).strip().lower()
                valid_statuses = {"approved", "hold", "spam", "trash"}
                if status_str in valid_statuses:
                    params["status"] = status_str
                else:
                    logger.warning("Invalid comment status: %s, ignoring", status)

            # WordPress REST APIを呼び出し
            logger.debug("Fetching comments with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_comments(params=params)

            # レスポンスの処理
            comments = response if isinstance(response, list) else []
            total_comments = len(comments)

            logger.info("Retrieved %d comments from WordPress", total_comments)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_comments}件のコメントを取得しました"
            if total_comments == 0:
                result_text = "WordPressからコメントが見つかりませんでした"

            response_data = {
                "total": total_comments,
                "comments": comments,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressコメント取得")

