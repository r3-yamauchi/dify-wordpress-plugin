# where: wordpress/tools/update_post.py
# what: Implements the update post tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress posts.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdatePostTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            post_id = validators.validate_post_id(tool_parameters.get("id"))
            title = tool_parameters.get("title")
            content = tool_parameters.get("content")
            status = tool_parameters.get("status")
            featured_media = tool_parameters.get("featured_media")
            categories = tool_parameters.get("categories")
            tags = tool_parameters.get("tags")

            # タイトルの検証（指定されている場合）
            if title is not None:
                title = title.strip()
                validators.validate_post_title(title)

            # ステータスの検証（指定されている場合）
            if status:
                validators.validate_post_status(status)

            # カテゴリーIDの正規化
            category_ids = validators.normalize_categories(categories) if categories is not None else None
            
            # タグIDの正規化
            tag_ids = validators.normalize_tags(tags) if tags is not None else None

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if title is not None:
                data["title"] = title

            if content is not None:
                data["content"] = content

            if status:
                data["status"] = status

            if featured_media is not None:
                try:
                    featured_media_id = int(featured_media)
                    if featured_media_id > 0:
                        data["featured_media"] = featured_media_id
                    elif featured_media_id == 0:
                        # 0を指定するとアイキャッチ画像を削除
                        data["featured_media"] = 0
                except (ValueError, TypeError):
                    logger.warning("Invalid featured_media ID: %s", featured_media)

            if category_ids is not None:
                data["categories"] = category_ids

            if tag_ids is not None:
                data["tags"] = tag_ids

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（title, content, status, featured_media, categories, tags）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating post ID: %s with data keys: %s", post_id, list(data.keys()))
            response = client.update_post(post_id=post_id, data=data)

            # レスポンスの処理
            updated_post_id = response.get("id")
            updated_title = response.get("title", {}).get("rendered", title or "")
            updated_link = response.get("link", "")

            logger.info("Updated WordPress post (ID: %s)", updated_post_id)

            result_text = f"WordPressの投稿を更新しました (ID: {updated_post_id})"
            if updated_link:
                result_text += f"\nURL: {updated_link}"

            response_data = {
                "id": updated_post_id,
                "title": updated_title,
                "link": updated_link,
                "status": response.get("status"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPress投稿更新")



