# where: wordpress/tools/delete_comment.py
# what: Implements the delete comment tool via WordPress REST API.
# why: Allow Dify workflows to delete WordPress comments.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class DeleteCommentTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            comment_id = validators.validate_comment_id(tool_parameters.get("id"))
            force = tool_parameters.get("force", False)

            # forceパラメータの正規化
            if isinstance(force, str):
                force = force.lower() in ("true", "1", "yes")
            elif not isinstance(force, bool):
                force = bool(force)

            # WordPress REST APIを呼び出し
            logger.debug("Deleting comment ID: %s (force: %s)", comment_id, force)
            response = client.delete_comment(comment_id=comment_id, force=force)

            # レスポンスの処理
            deleted_comment_id = response.get("id")
            deleted = response.get("deleted", False)

            if deleted:
                logger.info("Deleted WordPress comment (ID: %s)", deleted_comment_id)
                result_text = f"WordPressのコメントを削除しました (ID: {deleted_comment_id})"
            else:
                logger.info("Moved WordPress comment to trash (ID: %s)", deleted_comment_id)
                result_text = f"WordPressのコメントをゴミ箱に移動しました (ID: {deleted_comment_id})"

            response_data = {
                "id": deleted_comment_id,
                "deleted": deleted,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressコメント削除")
