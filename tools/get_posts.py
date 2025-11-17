# where: wordpress/tools/get_posts.py
# what: Implements the get posts tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress posts.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class GetPostsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            per_page = validators.validate_per_page(tool_parameters.get("per_page"), max_per_page=100)
            page = validators.validate_page_number(tool_parameters.get("page"))
            search = validators.validate_search_query(tool_parameters.get("search"))
            status = tool_parameters.get("status")
            categories = tool_parameters.get("categories")
            tags = tool_parameters.get("tags")
            
            # ステータスの検証
            if status:
                validators.validate_post_status(status)

            # カテゴリーIDの正規化
            category_ids = validators.normalize_categories(categories) if categories else []
            
            # タグIDの正規化
            tag_ids = validators.normalize_tags(tags) if tags else []

            # リクエストパラメータの構築
            params: dict[str, Any] = {
                "per_page": per_page,
                "page": page,
            }
            
            if search:
                params["search"] = search
            
            if status:
                params["status"] = status
            
            if category_ids:
                # WordPress REST APIでは、カテゴリーIDはカンマ区切りの文字列で指定
                params["categories"] = ",".join(str(cat_id) for cat_id in category_ids)
            
            if tag_ids:
                # WordPress REST APIでは、タグIDはカンマ区切りの文字列で指定
                params["tags"] = ",".join(str(tag_id) for tag_id in tag_ids)

            # WordPress REST APIを呼び出し
            logger.debug("Fetching posts with params: %s", {k: v for k, v in params.items() if k != "search" or not v})
            response = client.get_posts(params=params)

            # レスポンスの処理
            posts = response if isinstance(response, list) else []
            total_posts = len(posts)

            logger.info("Retrieved %d posts from WordPress", total_posts)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_posts}件の投稿を取得しました"
            if total_posts == 0:
                result_text = "WordPressから投稿が見つかりませんでした"

            response_data = {
                "total": total_posts,
                "posts": posts,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPress投稿取得")



