# where: wordpress/tools/create_page.py
# what: Implements the create page tool via WordPress REST API.
# why: Allow Dify workflows to create WordPress pages.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class CreatePageTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            title = (tool_parameters.get("title") or "").strip()
            content = tool_parameters.get("content") or ""
            status = tool_parameters.get("status")
            featured_media = tool_parameters.get("featured_media")
            parent = tool_parameters.get("parent")

            # 必須パラメータの検証
            validators.validate_post_title(title)
            validators.validate_post_content(content)

            # ステータスの検証
            if status:
                validators.validate_post_status(status)

            # リクエストデータの構築
            data: dict[str, Any] = {
                "title": title,
                "content": content,
            }

            if status:
                data["status"] = status

            if featured_media:
                try:
                    featured_media_id = int(featured_media)
                    if featured_media_id > 0:
                        data["featured_media"] = featured_media_id
                except (ValueError, TypeError):
                    logger.warning("Invalid featured_media ID: %s", featured_media)

            if parent:
                try:
                    parent_id = int(parent)
                    if parent_id > 0:
                        data["parent"] = parent_id
                except (ValueError, TypeError):
                    logger.warning("Invalid parent ID: %s", parent)

            # WordPress REST APIを呼び出し
            logger.debug("Creating page with title: %s", title[:50] if title else "")
            response = client.create_page(data=data)

            # レスポンスの処理
            page_id = response.get("id")
            page_title = response.get("title", {}).get("rendered", title)
            page_link = response.get("link", "")

            logger.info("Created WordPress page (ID: %s, title: %s)", page_id, page_title)

            result_text = f"WordPressにページを作成しました (ID: {page_id})"
            if page_link:
                result_text += f"\nURL: {page_link}"

            response_data = {
                "id": page_id,
                "title": page_title,
                "link": page_link,
                "status": response.get("status"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressページ作成")



