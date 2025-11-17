# where: wordpress/tools/get_plugins.py
# what: Implements the get plugins tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress plugin information.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base

logger = logging.getLogger(__name__)


class GetPluginsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # WordPress REST APIを呼び出し
            logger.debug("Fetching plugins")
            response = client.get_plugins()

            # レスポンスの処理
            plugins = response if isinstance(response, list) else []
            total_plugins = len(plugins)

            logger.info("Retrieved %d plugins from WordPress", total_plugins)

            # レスポンスメッセージの構築
            result_text = f"WordPressから{total_plugins}件のプラグイン情報を取得しました"
            if total_plugins == 0:
                result_text = "WordPressからプラグイン情報が見つかりませんでした"

            response_data = {
                "total": total_plugins,
                "plugins": plugins,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressプラグイン取得")

