# where: wordpress/tools/update_page.py
# what: Implements the update page tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress pages.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdatePageTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            page_id = validators.validate_post_id(tool_parameters.get("id"))
            title = tool_parameters.get("title")
            content = tool_parameters.get("content")
            status = tool_parameters.get("status")
            featured_media = tool_parameters.get("featured_media")
            parent = tool_parameters.get("parent")

            # タイトルの検証（指定されている場合）
            if title is not None:
                title = title.strip()
                validators.validate_post_title(title)

            # ステータスの検証（指定されている場合）
            if status:
                validators.validate_post_status(status)

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

            if parent is not None:
                try:
                    parent_id = int(parent)
                    if parent_id > 0:
                        data["parent"] = parent_id
                    elif parent_id == 0:
                        # 0を指定すると親ページを削除
                        data["parent"] = 0
                except (ValueError, TypeError):
                    logger.warning("Invalid parent ID: %s", parent)

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（title, content, status, featured_media, parent）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating page ID: %s with data keys: %s", page_id, list(data.keys()))
            response = client.update_page(page_id=page_id, data=data)

            # レスポンスの処理
            updated_page_id = response.get("id")
            updated_title = response.get("title", {}).get("rendered", title or "")
            updated_link = response.get("link", "")

            logger.info("Updated WordPress page (ID: %s)", updated_page_id)

            result_text = f"WordPressのページを更新しました (ID: {updated_page_id})"
            if updated_link:
                result_text += f"\nURL: {updated_link}"

            response_data = {
                "id": updated_page_id,
                "title": updated_title,
                "link": updated_link,
                "status": response.get("status"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressページ更新")



