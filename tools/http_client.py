# where: wordpress/tools/http_client.py
# what: Minimal WordPress REST API HTTP client.
# why: Some Dify environments cannot install the WordPress SDK, so we reimplement the needed REST flows.

from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests import Response, Session

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_DEFAULT_TIMEOUT = 30
_MAX_LOG_BODY_LENGTH = 200  # Maximum length of response body to log


def _sanitize_for_log(text: str) -> str:
    """Sanitize sensitive information from log messages."""
    if not text:
        return text

    # Mask Basic auth credentials
    text = re.sub(r'Basic\s+[A-Za-z0-9+/=]{20,}', 'Basic ***', text, flags=re.IGNORECASE)

    # Mask long alphanumeric strings that might be passwords
    text = re.sub(r'[A-Za-z0-9]{32,}', '***', text)

    # Truncate if too long
    if len(text) > _MAX_LOG_BODY_LENGTH:
        text = text[:_MAX_LOG_BODY_LENGTH] + "... (truncated)"

    return text


class WordPressHttpError(RuntimeError):
    """Raised when the WordPress REST API returns an error response."""

    def __init__(self, status_code: int | None, message: str, body: str | None = None) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message)


@dataclass
class WordPressHttpClient:
    wordpress_url: str
    username: str
    application_password: str
    timeout: int = _DEFAULT_TIMEOUT
    max_retries: int = 2
    session: Session | None = None

    def __post_init__(self) -> None:
        self._session = self.session or requests.Session()
        
        # WordPress URLの検証
        if not self.wordpress_url or not self.wordpress_url.strip():
            raise ValueError("WordPressサイトURLが空です。Difyのプロバイダー設定でWordPressサイトURLを確認してください。")
        
        # ベースURLを正規化（末尾のスラッシュを削除）
        self.base_url = self.wordpress_url.rstrip("/")
        if not self.base_url.endswith("/wp-json/wp/v2"):
            self.base_url = f"{self.base_url}/wp-json/wp/v2"
        
        logger.debug("WordPressHttpClient initialized with base_url: %s", self.base_url)

    @classmethod
    def from_context(cls, context: Any) -> "WordPressHttpClient":
        wordpress_url = getattr(context, "wordpress_url", None)
        username = getattr(context, "username", None)
        application_password = getattr(context, "application_password", None)
        
        if not wordpress_url:
            raise ValueError("WordPressサイトURLが設定されていません")
        if not username:
            raise ValueError("WordPressユーザー名が設定されていません")
        if not application_password:
            raise ValueError("アプリケーションパスワードが設定されていません")
        
        return cls(
            wordpress_url=wordpress_url,
            username=username,
            application_password=application_password,
        )

    # ---- WordPress REST API Methods -----------------------------------------

    def get_posts(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get posts from WordPress."""
        response = self._request(
            method="GET",
            path="/posts",
            params=params or {},
        )
        return self._parse_json_response(response)

    def create_post(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new post in WordPress."""
        response = self._request(
            method="POST",
            path="/posts",
            json=data,
        )
        return self._parse_json_response(response)

    def update_post(self, post_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing post in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/posts/{post_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_post(self, post_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a post from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/posts/{post_id}",
            params=params,
        )
        return self._parse_json_response(response)

    def get_pages(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get pages from WordPress."""
        response = self._request(
            method="GET",
            path="/pages",
            params=params or {},
        )
        return self._parse_json_response(response)

    def create_page(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new page in WordPress."""
        response = self._request(
            method="POST",
            path="/pages",
            json=data,
        )
        return self._parse_json_response(response)

    def update_page(self, page_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing page in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/pages/{page_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_page(self, page_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a page from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/pages/{page_id}",
            params=params,
        )
        return self._parse_json_response(response)

    def get_media(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get media from WordPress."""
        response = self._request(
            method="GET",
            path="/media",
            params=params or {},
        )
        return self._parse_json_response(response)

    def upload_media(self, file_path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Upload media file to WordPress."""
        import os
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        
        # ファイルを読み込む
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # ファイル名とMIMEタイプを取得
        filename = path.name
        content_type = self._guess_content_type(path)
        
        # filesパラメータを構築（requestsライブラリの形式）
        files = {"file": (filename, file_content, content_type)}
        
        # 追加データがあれば、dataに含める
        form_data = {}
        if data:
            for key, value in data.items():
                if value is not None:
                    form_data[key] = str(value)
        
        response = self._request(
            method="POST",
            path="/media",
            files=files,
            data=form_data if form_data else None,
        )
        return self._parse_json_response(response)

    def update_media(self, media_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing media in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/media/{media_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_media(self, media_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a media from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/media/{media_id}",
            params=params,
        )
        return self._parse_json_response(response)

    def get_post(self, post_id: int) -> dict[str, Any]:
        """Get a single post by ID from WordPress."""
        response = self._request(
            method="GET",
            path=f"/posts/{post_id}",
        )
        return self._parse_json_response(response)

    def get_site_settings(self) -> dict[str, Any]:
        """Get site settings from WordPress."""
        response = self._request(
            method="GET",
            path="/settings",
        )
        return self._parse_json_response(response)

    def get_users(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get users from WordPress."""
        response = self._request(
            method="GET",
            path="/users",
            params=params or {},
        )
        return self._parse_json_response(response)

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Get a single user by ID from WordPress."""
        response = self._request(
            method="GET",
            path=f"/users/{user_id}",
        )
        return self._parse_json_response(response)

    def update_user(self, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update a user in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/users/{user_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def get_comments(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get comments from WordPress."""
        response = self._request(
            method="GET",
            path="/comments",
            params=params or {},
        )
        return self._parse_json_response(response)

    def get_plugins(self) -> dict[str, Any]:
        """Get plugins from WordPress."""
        response = self._request(
            method="GET",
            path="/plugins",
        )
        return self._parse_json_response(response)

    def get_categories(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get categories from WordPress."""
        response = self._request(
            method="GET",
            path="/categories",
            params=params or {},
        )
        return self._parse_json_response(response)

    def get_category(self, category_id: int) -> dict[str, Any]:
        """Get a single category by ID from WordPress."""
        response = self._request(
            method="GET",
            path=f"/categories/{category_id}",
        )
        return self._parse_json_response(response)

    def create_category(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new category in WordPress."""
        response = self._request(
            method="POST",
            path="/categories",
            json=data,
        )
        return self._parse_json_response(response)

    def update_category(self, category_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing category in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/categories/{category_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_category(self, category_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a category from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/categories/{category_id}",
            params=params,
        )
        return self._parse_json_response(response)

    def get_tags(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get tags from WordPress."""
        response = self._request(
            method="GET",
            path="/tags",
            params=params or {},
        )
        return self._parse_json_response(response)

    def get_tag(self, tag_id: int) -> dict[str, Any]:
        """Get a single tag by ID from WordPress."""
        response = self._request(
            method="GET",
            path=f"/tags/{tag_id}",
        )
        return self._parse_json_response(response)

    def create_tag(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new tag in WordPress."""
        response = self._request(
            method="POST",
            path="/tags",
            json=data,
        )
        return self._parse_json_response(response)

    def update_tag(self, tag_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing tag in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/tags/{tag_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_tag(self, tag_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a tag from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/tags/{tag_id}",
            params=params,
        )
        return self._parse_json_response(response)

    def get_comment(self, comment_id: int) -> dict[str, Any]:
        """Get a single comment by ID from WordPress."""
        response = self._request(
            method="GET",
            path=f"/comments/{comment_id}",
        )
        return self._parse_json_response(response)

    def create_comment(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new comment in WordPress."""
        response = self._request(
            method="POST",
            path="/comments",
            json=data,
        )
        return self._parse_json_response(response)

    def update_comment(self, comment_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing comment in WordPress."""
        response = self._request(
            method="POST",  # WordPress REST API uses POST for updates
            path=f"/comments/{comment_id}",
            json=data,
        )
        return self._parse_json_response(response)

    def delete_comment(self, comment_id: int, force: bool = False) -> dict[str, Any]:
        """Delete a comment from WordPress."""
        params = {"force": "true"} if force else {}
        response = self._request(
            method="DELETE",
            path=f"/comments/{comment_id}",
            params=params,
        )
        return self._parse_json_response(response)

    @staticmethod
    def _guess_content_type(path: Path) -> str:
        """Guess content type from file extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type or "application/octet-stream"

    # ---- Low-level helpers -------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {}) or {}
        
        # Basic認証の設定
        credentials = f"{self.username}:{self.application_password}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        headers.setdefault("Authorization", f"Basic {encoded_credentials}")
        
        # Content-Typeの設定（JSONリクエストの場合、filesがある場合は除く）
        if "json" in kwargs and "files" not in kwargs:
            headers.setdefault("Content-Type", "application/json")
        
        # デバッグ用: リクエストURLとメソッドをログ出力
        logger.info("Request: %s %s", method, url)
        
        # デバッグ用: Authorizationヘッダーをマスクしてログ出力
        auth_header = headers.get("Authorization", "")
        if auth_header:
            masked_auth = _sanitize_for_log(auth_header)
            logger.debug("Authorization header: %s", masked_auth)
        
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:  # pragma: no cover - network failures retried
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                sanitized_exc = _sanitize_for_log(str(exc))
                raise WordPressHttpError(None, f"WordPress APIリクエストに失敗しました: {sanitized_exc}") from exc

            if response.status_code in _RETRY_STATUSES and attempt < self.max_retries:
                # 429エラー（レートリミット）の場合はRetry-Afterヘッダーを確認
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_seconds = int(retry_after)
                            logger.info("Rate limited. Waiting %d seconds as specified by Retry-After header", wait_seconds)
                            time.sleep(wait_seconds)
                        except (ValueError, TypeError):
                            logger.warning("Retry-After header value '%s' is not a valid integer, using exponential backoff", retry_after)
                            time.sleep(2**attempt)
                    else:
                        logger.info("Rate limited but no Retry-After header, using exponential backoff")
                        time.sleep(2**attempt)
                else:
                    # その他のリトライ可能なエラーの場合は指数バックオフ
                    time.sleep(2**attempt)
                continue

            if response.status_code >= 400:
                message = self._extract_error_message(response)
                sanitized_body = _sanitize_for_log(response.text)
                logger.error(
                    "WordPress APIエラー (status=%s): %s, body=%s",
                    response.status_code,
                    message,
                    sanitized_body,
                )
                raise WordPressHttpError(response.status_code, message, body=sanitized_body)

            return response

        sanitized_error = _sanitize_for_log(str(last_error)) if last_error else "Unknown error"
        raise WordPressHttpError(None, f"WordPress APIリクエストに失敗しました: {sanitized_error}")  # pragma: no cover

    def _parse_json_response(self, response: Response) -> dict[str, Any] | list[Any]:
        """Parse JSON response with better error handling."""
        # レスポンスの内容を先に確認
        content_type = response.headers.get("Content-Type", "").lower()
        response_text = response.text if response.text else ""
        
        # 空のレスポンスの場合
        if not response_text or not response_text.strip():
            logger.error(
                "JSON解析エラー: status=%s, content_type=%s, response=空",
                response.status_code,
                content_type,
            )
            raise WordPressHttpError(
                response.status_code,
                "WordPress APIが空のレスポンスを返しました。",
                body="",
            )
        
        # HTMLレスポンスの場合（認証エラーなど）
        if "text/html" in content_type:
            response_preview = response_text[:500]
            
            # HTMLレスポンスからエラーの原因を推測
            error_hint = "WordPress APIがHTMLレスポンスを返しました。"
            if "login" in response_text.lower() or "ログイン" in response_text:
                error_hint += " 認証エラーの可能性があります。ユーザー名とアプリケーションパスワードを確認してください。"
            elif "404" in response_text or "not found" in response_text.lower():
                error_hint += " REST APIエンドポイントが見つかりません。WordPressサイトURLが正しいか確認してください。"
            elif "403" in response_text or "forbidden" in response_text.lower():
                error_hint += " アクセスが拒否されました。ユーザーの権限を確認してください。"
            else:
                error_hint += " REST APIが有効でない可能性があります。WordPressサイトの設定を確認してください。"
            
            logger.error(
                "JSON解析エラー: status=%s, content_type=%s, url=%s, response_preview=%s",
                response.status_code,
                content_type,
                response.url if hasattr(response, 'url') else 'unknown',
                _sanitize_for_log(response_preview),
            )
            
            request_url = response.url if hasattr(response, 'url') else 'unknown'
            
            # localhost:8080の場合、より具体的な案内を追加
            additional_hint = ""
            if "localhost:8080" in str(request_url).lower():
                additional_hint = "\n\n注意: リクエストURLがlocalhost:8080になっています。Difyのプロバイダー設定で、正しいWordPressサイトURL（例: https://your-site.com）を設定してください。"
            
            raise WordPressHttpError(
                response.status_code,
                f"{error_hint} リクエストURL: {request_url}{additional_hint}",
                body=response_text,
            )
        
        # JSON解析を試行
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError, requests.exceptions.JSONDecodeError) as exc:
            response_preview = response_text[:500]
            logger.error(
                "JSON解析エラー: status=%s, content_type=%s, response_preview=%s",
                response.status_code,
                content_type,
                _sanitize_for_log(response_preview),
            )
            
            # その他のJSON解析エラー
            raise WordPressHttpError(
                response.status_code,
                f"WordPress APIのレスポンスをJSONとして解析できませんでした。レスポンス: {_sanitize_for_log(response_preview)}",
                body=response_text,
            ) from exc

    @staticmethod
    def _extract_error_message(response: Response) -> str:
        """Extract error message from WordPress REST API error response."""
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            data = None
        
        if isinstance(data, dict):
            # WordPress REST APIのエラーフォーマット
            code = data.get("code", "")
            message = data.get("message", "")
            data_obj = data.get("data", {})
            
            if message:
                if code:
                    return f"WordPress APIエラー ({response.status_code}): [{code}] {message}"
                return f"WordPress APIエラー ({response.status_code}): {message}"
            
            # その他のエラーフィールドを確認
            error = data.get("error")
            if isinstance(error, str):
                sanitized_error = _sanitize_for_log(error)
                return f"WordPress APIエラー ({response.status_code}): {sanitized_error}"
        
        # JSON解析できない場合、レスポンステキストの最初の部分を使用
        if response.text:
            sanitized_text = _sanitize_for_log(response.text[:500])  # 最初の500文字
            return f"WordPress APIエラー ({response.status_code}): {sanitized_text}"
        return f"WordPress APIエラー ({response.status_code})"
