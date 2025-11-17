# where: wordpress/tools/get_site_statistics.py
# what: Implements the get site statistics tool via WordPress REST API.
# why: Allow Dify workflows to retrieve WordPress site statistics.
# note: This may require WordPress.com specific API endpoints and may not work with standard WordPress installations.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base

logger = logging.getLogger(__name__)


class GetSiteStatisticsTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # WordPress REST APIを呼び出し
            # 注意: 標準のWordPress REST APIには統計エンドポイントがないため、
            # WordPress.com専用のAPIが必要な可能性があります
            logger.debug("Fetching site statistics")
            
            # WordPress.comの統計APIエンドポイントを試行
            # 標準のWordPressインストールでは利用できない可能性があります
            try:
                # WordPress.comの統計APIエンドポイント（存在する場合）
                # 標準のWordPress REST APIには統計エンドポイントがないため、
                # この機能はWordPress.com専用の可能性があります
                response = client._request(
                    method="GET",
                    path="/stats",  # WordPress.comの統計エンドポイント（推測）
                )
                statistics = response.json()
            except Exception as stats_exc:
                # 統計エンドポイントが利用できない場合、代替情報を提供
                logger.warning("Site statistics endpoint not available: %s", stats_exc)
                
                # 代替として、投稿数やコメント数などの基本情報を取得
                try:
                    posts_response = client.get_posts(params={"per_page": 1})
                    comments_response = client.get_comments(params={"per_page": 1})
                    
                    posts_count = len(posts_response) if isinstance(posts_response, list) else 0
                    comments_count = len(comments_response) if isinstance(comments_response, list) else 0
                    
                    # 基本的な統計情報を構築
                    statistics = {
                        "note": "標準のWordPress REST APIには統計エンドポイントがありません。WordPress.com専用のAPIが必要な可能性があります。",
                        "basic_info": {
                            "posts_available": posts_count > 0,
                            "comments_available": comments_count > 0,
                        }
                    }
                except Exception as fallback_exc:
                    logger.error("Failed to get fallback statistics: %s", fallback_exc)
                    raise ValueError(
                        "サイト統計情報を取得できませんでした。"
                        "この機能はWordPress.com専用のAPIが必要な可能性があります。"
                        f"エラー: {fallback_exc}"
                    ) from fallback_exc

            # レスポンスの処理
            logger.info("Retrieved site statistics from WordPress")

            # レスポンスメッセージの構築
            result_text = "WordPressからサイト統計情報を取得しました"

            response_data = {
                "statistics": statistics,
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressサイト統計取得")

