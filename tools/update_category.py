# where: wordpress/tools/update_category.py
# what: Implements the update category tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress categories.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdateCategoryTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            category_id = validators.validate_category_id(tool_parameters.get("id"))
            name = tool_parameters.get("name")
            description = tool_parameters.get("description")
            slug = tool_parameters.get("slug")
            parent = tool_parameters.get("parent")

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if name is not None:
                name_str = str(name).strip()
                if name_str:
                    data["name"] = name_str
                else:
                    raise ValueError("カテゴリー名が空です")

            if description is not None:
                data["description"] = description

            if slug is not None:
                slug_str = str(slug).strip()
                if slug_str:
                    data["slug"] = slug_str

            if parent is not None:
                try:
                    parent_id = int(parent)
                    if parent_id > 0:
                        data["parent"] = parent_id
                    elif parent_id == 0:
                        # 0を指定すると親子関係を削除
                        data["parent"] = 0
                except (ValueError, TypeError):
                    logger.warning("Invalid parent category ID: %s", parent)

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（name, description, slug, parent）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating category ID: %s with data keys: %s", category_id, list(data.keys()))
            response = client.update_category(category_id=category_id, data=data)

            # レスポンスの処理
            updated_category_id = response.get("id")
            updated_name = response.get("name", name or "")

            logger.info("Updated WordPress category (ID: %s)", updated_category_id)

            result_text = f"WordPressのカテゴリーを更新しました (ID: {updated_category_id}, 名前: {updated_name})"

            response_data = {
                "id": updated_category_id,
                "name": updated_name,
                "slug": response.get("slug"),
                "description": response.get("description"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressカテゴリー更新")
