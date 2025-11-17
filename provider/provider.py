# where: wordpress/provider/provider.py
# what: Validates WordPress credentials and initializes provider-level settings.
# why: Prevents misconfigured plugins from attempting to call WordPress REST API with bad credentials.

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

logger = logging.getLogger(__name__)


class WordPressProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Validate WordPress credentials supplied from the Dify console."""

        wordpress_url = (credentials.get("wordpress_url") or "").strip()
        username = (credentials.get("username") or "").strip()
        application_password = (credentials.get("application_password") or "").strip()

        # WordPressサイトURLの検証
        if not wordpress_url:
            raise ToolProviderCredentialValidationError("WordPressサイトURLを入力してください")
        
        # URL形式の検証
        try:
            parsed = urlparse(wordpress_url)
            if not parsed.scheme:
                raise ToolProviderCredentialValidationError("WordPressサイトURLにはプロトコル（http://またはhttps://）を含めてください")
            if parsed.scheme not in ("http", "https"):
                raise ToolProviderCredentialValidationError("WordPressサイトURLはhttp://またはhttps://で始まる必要があります")
            if not parsed.netloc:
                raise ToolProviderCredentialValidationError("WordPressサイトURLが不正です")
        except Exception as exc:
            raise ToolProviderCredentialValidationError(f"WordPressサイトURLの形式が不正です: {exc}") from exc

        # HTTPSの推奨（警告のみ）
        if wordpress_url.startswith("http://"):
            logger.warning("WordPressサイトURLがHTTPです。セキュリティのためHTTPSの使用を推奨します")

        # ユーザー名の検証
        if not username:
            raise ToolProviderCredentialValidationError("WordPressユーザー名を入力してください")
        
        if len(username) < 1:
            raise ToolProviderCredentialValidationError("ユーザー名が短すぎます")
        
        # ユーザー名の形式チェック（基本的な文字のみ許可）
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            logger.warning("ユーザー名に特殊文字が含まれています。正しいユーザー名を確認してください")

        # アプリケーションパスワードの検証
        if not application_password:
            raise ToolProviderCredentialValidationError("アプリケーションパスワードを入力してください")
        
        # WordPressのアプリケーションパスワードは通常24文字（スペース区切りで4文字×6グループ）
        # スペースを除いた長さで検証
        password_without_spaces = application_password.replace(" ", "")
        if len(password_without_spaces) < 20:
            raise ToolProviderCredentialValidationError("アプリケーションパスワードが短すぎます。WordPress管理画面から正しい値をコピーしてください")

        logger.info("WordPress credentials passed basic validation checks")
