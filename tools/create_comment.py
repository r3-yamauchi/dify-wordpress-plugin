# where: wordpress/tools/create_comment.py
# what: Implements the create comment tool via WordPress REST API.
# why: Allow Dify workflows to create WordPress comments.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class CreateCommentTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            post_id = validators.validate_post_id(tool_parameters.get("post_id"))
            content = (tool_parameters.get("content") or "").strip()
            author_name = tool_parameters.get("author_name")
            author_email = tool_parameters.get("author_email")
            parent = tool_parameters.get("parent")

            # 必須パラメータの検証
            if not content:
                raise ValueError("コメント内容を入力してください")

            # リクエストデータの構築
            data: dict[str, Any] = {
                "post": post_id,
                "content": content,
            }

            if author_name:
                author_name_str = str(author_name).strip()
                if author_name_str:
                    data["author_name"] = author_name_str

            if author_email:
                author_email_str = str(author_email).strip()
                if author_email_str:
                    data["author_email"] = author_email_str

            if parent:
                try:
                    parent_id = int(parent)
                    if parent_id > 0:
                        data["parent"] = parent_id
                except (ValueError, TypeError):
                    logger.warning("Invalid parent comment ID: %s", parent)

            # WordPress REST APIを呼び出し
            logger.debug("Creating comment for post ID: %s", post_id)
            response = client.create_comment(data=data)

            # レスポンスの処理
            comment_id = response.get("id")
            comment_content = response.get("content", {}).get("rendered", content)

            logger.info("Created WordPress comment (ID: %s, post ID: %s)", comment_id, post_id)

            result_text = f"WordPressにコメントを作成しました (ID: {comment_id}, 投稿ID: {post_id})"

            response_data = {
                "id": comment_id,
                "post": post_id,
                "content": comment_content,
                "status": response.get("status"),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressコメント作成")
