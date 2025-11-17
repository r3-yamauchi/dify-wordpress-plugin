# where: wordpress/tools/create_category.py
# what: Implements the create category tool via WordPress REST API.
# why: Allow Dify workflows to create WordPress categories.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class CreateCategoryTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            name = (tool_parameters.get("name") or "").strip()
            description = tool_parameters.get("description") or ""
            slug = tool_parameters.get("slug")
            parent = tool_parameters.get("parent")

            # 必須パラメータの検証
            if not name:
                raise ValueError("カテゴリー名を入力してください")

            # リクエストデータの構築
            data: dict[str, Any] = {
                "name": name,
            }

            if description:
                data["description"] = description

            if slug:
                slug_str = str(slug).strip()
                if slug_str:
                    data["slug"] = slug_str

            if parent:
                try:
                    parent_id = int(parent)
                    if parent_id > 0:
                        data["parent"] = parent_id
                except (ValueError, TypeError):
                    logger.warning("Invalid parent category ID: %s", parent)

            # WordPress REST APIを呼び出し
            logger.debug("Creating category with name: %s", name)
            response = client.create_category(data=data)

            # レスポンスの処理
            category_id = response.get("id")
            category_name = response.get("name", name)

            logger.info("Created WordPress category (ID: %s, name: %s)", category_id, category_name)

            result_text = f"WordPressにカテゴリーを作成しました (ID: {category_id}, 名前: {category_name})"

            response_data = {
                "id": category_id,
                "name": category_name,
                "slug": response.get("slug"),
                "description": response.get("description"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressカテゴリー作成")
