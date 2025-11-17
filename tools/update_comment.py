# where: wordpress/tools/update_comment.py
# what: Implements the update comment tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress comments.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdateCommentTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            comment_id = validators.validate_comment_id(tool_parameters.get("id"))
            content = tool_parameters.get("content")
            status = tool_parameters.get("status")

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if content is not None:
                content_str = str(content).strip()
                if content_str:
                    data["content"] = content_str
                else:
                    raise ValueError("コメント内容が空です")

            if status:
                status_str = str(status).strip().lower()
                valid_statuses = {"approved", "hold", "spam", "trash"}
                if status_str in valid_statuses:
                    data["status"] = status_str
                else:
                    raise ValueError(f"無効なコメントステータスです。有効な値: {', '.join(sorted(valid_statuses))}")

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（content, status）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating comment ID: %s with data keys: %s", comment_id, list(data.keys()))
            response = client.update_comment(comment_id=comment_id, data=data)

            # レスポンスの処理
            updated_comment_id = response.get("id")
            updated_content = response.get("content", {}).get("rendered", content or "")

            logger.info("Updated WordPress comment (ID: %s)", updated_comment_id)

            result_text = f"WordPressのコメントを更新しました (ID: {updated_comment_id})"

            response_data = {
                "id": updated_comment_id,
                "content": updated_content,
                "status": response.get("status"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressコメント更新")
