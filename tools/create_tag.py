# where: wordpress/tools/create_tag.py
# what: Implements the create tag tool via WordPress REST API.
# why: Allow Dify workflows to create WordPress tags.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class CreateTagTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            name = (tool_parameters.get("name") or "").strip()
            description = tool_parameters.get("description") or ""
            slug = tool_parameters.get("slug")

            # 必須パラメータの検証
            if not name:
                raise ValueError("タグ名を入力してください")

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

            # WordPress REST APIを呼び出し
            logger.debug("Creating tag with name: %s", name)
            response = client.create_tag(data=data)

            # レスポンスの処理
            tag_id = response.get("id")
            tag_name = response.get("name", name)

            logger.info("Created WordPress tag (ID: %s, name: %s)", tag_id, tag_name)

            result_text = f"WordPressにタグを作成しました (ID: {tag_id}, 名前: {tag_name})"

            response_data = {
                "id": tag_id,
                "name": tag_name,
                "slug": response.get("slug"),
                "description": response.get("description"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressタグ作成")
