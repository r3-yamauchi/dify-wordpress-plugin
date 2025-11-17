# where: wordpress/tools/base.py
# what: Shared helper utilities for WordPress tools (credentials, messaging, validation hooks).
# why: Avoid duplicated logic across WordPress REST API tool implementations.

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from .http_client import WordPressHttpClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderContext:
    wordpress_url: str
    username: str
    application_password: str


class BaseWordPressTool(Tool):
    """Base class that takes care of credential loading and HTTP client creation."""

    def _load_provider_context(self) -> ProviderContext:
        credentials: dict[str, Any] = getattr(self.runtime, "credentials", {}) or {}
        wordpress_url = (credentials.get("wordpress_url") or "").strip()
        username = (credentials.get("username") or "").strip()
        application_password = (credentials.get("application_password") or "").strip()

        # デバッグ用: 取得した認証情報をログ出力（機密情報はマスク）
        logger.debug("Loading provider context: wordpress_url=%s, username=%s, application_password=%s", 
                     wordpress_url or "(empty)", 
                     username or "(empty)", 
                     "***" if application_password else "(empty)")

        if not wordpress_url:
            raise ValueError("WordPressサイトURLを設定してください。Difyのプロバイダー設定でWordPressサイトURLを確認してください。")
        if not username:
            raise ValueError("WordPressユーザー名を設定してください。Difyのプロバイダー設定でユーザー名を確認してください。")
        if not application_password:
            raise ValueError("アプリケーションパスワードを設定してください。Difyのプロバイダー設定でアプリケーションパスワードを確認してください。")

        # URL形式の基本的な検証
        if not wordpress_url.startswith(("http://", "https://")):
            raise ValueError(f"WordPressサイトURLはhttp://またはhttps://で始まる必要があります。現在の値: {wordpress_url}")
        
        # localhost:8080は通常のWordPressサイトではないため警告
        if "localhost:8080" in wordpress_url.lower() or wordpress_url.strip() == "http://localhost:8080" or wordpress_url.strip() == "https://localhost:8080":
            raise ValueError(
                f"WordPressサイトURLがlocalhost:8080になっています。これは通常のWordPressサイトではありません。\n"
                f"正しいWordPressサイトURL（例: https://example.com）をDifyのプロバイダー設定で設定してください。\n"
                f"現在の値: {wordpress_url}"
            )

        return ProviderContext(
            wordpress_url=wordpress_url,
            username=username,
            application_password=application_password,
        )

    def _create_http_client(self, context: ProviderContext) -> WordPressHttpClient:
        """Create a WordPress HTTP client from the provider context."""
        logger.debug("Creating WordPress HTTP client")
        return WordPressHttpClient.from_context(context)

    # ---- Messaging helpers -------------------------------------------------

    def _create_text_message(self, text: str) -> ToolInvokeMessage:
        return self.create_text_message(text)

    def _create_json_message(self, payload: dict[str, Any]) -> ToolInvokeMessage:
        return self.create_json_message(payload)

    def _handle_error(self, error: Exception, action: str) -> list[ToolInvokeMessage]:
        logger.exception("Failed to %s: %s", action, error)
        hints: list[str] = []
        message = str(error)
        lowered = message.lower()
        
        # WordPressHttpErrorの場合は詳細情報を取得
        from .http_client import WordPressHttpError
        if isinstance(error, WordPressHttpError):
            # ステータスコードとエラーメッセージを取得
            status_code = error.status_code
            if status_code:
                message = f"WordPress APIエラー (HTTP {status_code}): {error}"
            else:
                message = f"WordPress APIエラー: {error}"
            
            # エラーボディに詳細情報が含まれている場合
            if hasattr(error, "body") and error.body:
                body_str = str(error.body)
                if body_str and len(body_str) > 0:
                    # JSON形式のエラーボディから詳細を抽出
                    try:
                        import json
                        body_json = json.loads(body_str)
                        if isinstance(body_json, dict):
                            # WordPress REST APIのエラーフォーマット
                            code = body_json.get("code", "")
                            error_message = body_json.get("message", "")
                            data = body_json.get("data", {})
                            
                            if error_message:
                                if code:
                                    message += f"\n詳細: [{code}] {error_message}"
                                else:
                                    message += f"\n詳細: {error_message}"
                            
                            # パラメータエラーの場合
                            if isinstance(data, dict) and "params" in data:
                                params = data["params"]
                                if isinstance(params, dict):
                                    param_errors = []
                                    for param, param_msg in params.items():
                                        param_errors.append(f"{param}: {param_msg}")
                                    if param_errors:
                                        message += f"\nパラメータエラー: {'; '.join(param_errors)}"
                    except (json.JSONDecodeError, ValueError):
                        # JSON解析に失敗した場合は生のテキストを使用
                        message += f"\n詳細: {body_str[:500]}"
        
        # エラーメッセージに基づいてヒントを追加
        if "401" in message or "unauthorized" in lowered:
            hints.append("WordPressの認証情報（ユーザー名またはアプリケーションパスワード）が無効です。")
            hints.append("WordPress管理画面でアプリケーションパスワードが正しく生成されているか確認してください。")
        if "403" in message or "forbidden" in lowered:
            hints.append("WordPressユーザーに必要な権限がありません。")
            hints.append("投稿の作成・編集・削除には適切な権限が必要です。")
        if "404" in message or "not found" in lowered:
            hints.append("指定されたリソース（投稿IDなど）が見つかりません。")
            hints.append("正しいIDを指定しているか確認してください。")
        if "rate" in lowered or "429" in lowered:
            hints.append("短時間にリクエストしすぎている可能性があります。数秒待って再実行してください")
        if "400" in message or "validation" in lowered or "invalid" in lowered:
            hints.append("リクエストパラメータの形式を確認してください（タイトル、本文など）")
        if "500" in message or "internal server error" in lowered:
            hints.append("WordPressサーバーでエラーが発生しました。")
            hints.append("WordPressサイトのログを確認してください。")

        text = f"{action} に失敗しました: {message}"
        if hints:
            text += "\n\n" + "\n".join(f"ヒント: {hint}" for hint in hints)

        return [self._create_text_message(text)]
