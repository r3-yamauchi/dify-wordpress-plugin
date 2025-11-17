# where: wordpress/tools/update_tag.py
# what: Implements the update tag tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress tags.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdateTagTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            tag_id = validators.validate_tag_id(tool_parameters.get("id"))
            name = tool_parameters.get("name")
            description = tool_parameters.get("description")
            slug = tool_parameters.get("slug")

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if name is not None:
                name_str = str(name).strip()
                if name_str:
                    data["name"] = name_str
                else:
                    raise ValueError("タグ名が空です")

            if description is not None:
                data["description"] = description

            if slug is not None:
                slug_str = str(slug).strip()
                if slug_str:
                    data["slug"] = slug_str

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（name, description, slug）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating tag ID: %s with data keys: %s", tag_id, list(data.keys()))
            response = client.update_tag(tag_id=tag_id, data=data)

            # レスポンスの処理
            updated_tag_id = response.get("id")
            updated_name = response.get("name", name or "")

            logger.info("Updated WordPress tag (ID: %s)", updated_tag_id)

            result_text = f"WordPressのタグを更新しました (ID: {updated_tag_id}, 名前: {updated_name})"

            response_data = {
                "id": updated_tag_id,
                "name": updated_name,
                "slug": response.get("slug"),
                "description": response.get("description"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressタグ更新")
