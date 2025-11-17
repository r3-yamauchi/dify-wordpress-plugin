# where: wordpress/tools/delete_page.py
# what: Implements the delete page tool via WordPress REST API.
# why: Allow Dify workflows to delete WordPress pages.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class DeletePageTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            page_id = validators.validate_post_id(tool_parameters.get("id"))
            force = tool_parameters.get("force", False)

            # forceパラメータの正規化
            if isinstance(force, str):
                force = force.lower() in ("true", "1", "yes")
            elif not isinstance(force, bool):
                force = bool(force)

            # WordPress REST APIを呼び出し
            logger.debug("Deleting page ID: %s (force: %s)", page_id, force)
            response = client.delete_page(page_id=page_id, force=force)

            # レスポンスの処理
            deleted_page_id = response.get("id")
            deleted = response.get("deleted", False)

            if deleted:
                logger.info("Deleted WordPress page (ID: %s)", deleted_page_id)
                result_text = f"WordPressのページを削除しました (ID: {deleted_page_id})"
            else:
                logger.info("Moved WordPress page to trash (ID: %s)", deleted_page_id)
                result_text = f"WordPressのページをゴミ箱に移動しました (ID: {deleted_page_id})"

            response_data = {
                "id": deleted_page_id,
                "deleted": deleted,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressページ削除")




