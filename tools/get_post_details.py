# where: wordpress/tools/get_post_details.py
# what: Implements the get post details tool via WordPress REST API.
# why: Allow Dify workflows to retrieve detailed information about a specific WordPress post.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetPostDetailsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            post_id = validators.validate_post_id(tool_parameters.get("post_id"))

            # WordPress REST APIを呼び出し
            logger.debug("Fetching post details for post_id: %d", post_id)
            response = client.get_post(post_id)

            # レスポンスの処理
            logger.info("Retrieved post details for post_id: %d", post_id)

            # レスポンスメッセージの構築
            post_title = response.get("title", {}).get("rendered", "タイトルなし")
            result_text = f"WordPressから投稿の詳細を取得しました: {post_title}"

            response_data = {
                "post": response,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPress投稿詳細取得")

