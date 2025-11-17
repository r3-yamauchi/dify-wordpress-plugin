# where: wordpress/tools/get_site_settings.py
# what: Implements the get site settings tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress site settings.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base

logger = logging.getLogger(__name__)


class GetSiteSettingsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # WordPress REST APIを呼び出し
            logger.debug("Fetching site settings")
            response = client.get_site_settings()

            # レスポンスの処理
            logger.info("Retrieved site settings from WordPress")

            # レスポンスメッセージの構築
            result_text = "WordPressからサイト設定を取得しました"

            response_data = {
                "settings": response,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressサイト設定取得")

