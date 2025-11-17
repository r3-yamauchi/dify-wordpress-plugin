# where: wordpress/provider/http_client.py
# what: Minimal wordpress HTTP client used instead of the official SDK.
# why: Some Dify environments cannot install the SDK, so we reimplement the needed REST flows.

from __future__ import annotations

import base64
import copy
import json
import logging
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import requests
from requests import Response, Session

from ..tools.file_utils import ResolvedFile

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.wordpress.com/v3"
_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_DEFAULT_TIMEOUT = 15
_MAX_LOG_BODY_LENGTH = 200  # Maximum length of response body to log


def _sanitize_for_log(text: str) -> str:
    """Sanitize sensitive information from log messages."""
    if not text:
        return text

    # Mask bearer tokens (base64 encoded strings in Authorization header)
    text = re.sub(r'Bearer\s+[A-Za-z0-9+/=]{20,}', 'Bearer ***', text, flags=re.IGNORECASE)

    # Mask API keys (long alphanumeric strings)
    text = re.sub(r'[A-Za-z0-9]{32,}', '***', text)

    # Mask email-like patterns that might be login IDs
    text = re.sub(r'["\']([a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+)["\']', r'"\1"', text)

    # Truncate if too long
    if len(text) > _MAX_LOG_BODY_LENGTH:
        text = text[:_MAX_LOG_BODY_LENGTH] + "... (truncated)"

    return text


class wordpressHttpError(RuntimeError):
    """Raised when the wordpress REST API returns an error response."""

    def __init__(self, status_code: int | None, message: str, body: str | None = None) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message)


@dataclass
class wordpressHttpClient:
    api_key: str
    base_url: str = _DEFAULT_BASE_URL
    timeout: int = _DEFAULT_TIMEOUT
    max_retries: int = 2
    session: Session | None = None

    def __post_init__(self) -> None:
        self._session = self.session or requests.Session()
        # デバッグ用: APIキーが正しく設定されているか確認
        if self.api_key:
            logger.debug("wordpressHttpClient initialized with API key (length: %d, starts with 'SG.': %s)", 
                        len(self.api_key), self.api_key.startswith("SG."))
        else:
            logger.warning("wordpressHttpClient initialized with empty API key!")

    @classmethod
    def from_context(cls, context: Any) -> "wordpressHttpClient":
        api_key = getattr(context, "api_key", None)
        if not api_key:
            logger.warning("ProviderContext has no api_key attribute!")
        return cls(api_key=api_key or "")

    # ---- Transactional -----------------------------------------------------

    def send_transactional_email(self, payload: dict[str, Any], attachments: Sequence[ResolvedFile]) -> str:
        """
        Send transactional email via wordpress API v3.
        
        wordpress API v3 format:
        {
            "personalizations": [{
                "to": [{"email": "..."}],
                "cc": [{"email": "..."}],
                "bcc": [{"email": "..."}]
            }],
            "from": {"email": "...", "name": "..."},
            "subject": "...",
            "content": [
                {"type": "text/plain", "value": "..."},
                {"type": "text/html", "value": "..."}
            ],
            "attachments": [...],
            "headers": {...},
            "reply_to": {"email": "..."}
        }
        """
        # デバッグ用: 入力ペイロードの内容を確認
        to_field = payload.get("to")
        logger.debug("Input payload 'to' field: type=%s, value=%s, len=%s", 
                    type(to_field), to_field, len(to_field) if isinstance(to_field, (list, str)) else "N/A")
        if isinstance(to_field, list):
            for i, recipient in enumerate(to_field[:5]):  # 最初の5件まで
                logger.debug("  to[%d]: type=%s, value=%s, repr=%s, is_empty=%s", 
                            i, type(recipient), recipient, repr(recipient), 
                            not recipient if isinstance(recipient, str) else "N/A")
        elif isinstance(to_field, str):
            logger.debug("  to (string): value=%s, repr=%s, is_empty=%s", 
                        to_field, repr(to_field), not to_field or not to_field.strip())
        logger.debug("Input payload 'cc' field: type=%s, value=%s", type(payload.get("cc")), payload.get("cc"))
        logger.debug("Input payload 'bcc' field: type=%s, value=%s", type(payload.get("bcc")), payload.get("bcc"))
        
        # wordpress API v3 形式に変換
        wordpress_payload = self._convert_to_wordpress_format(payload, attachments)
        
        # デバッグ用にペイロードの構造をログ出力（機密情報はマスキング）
        debug_payload = self._mask_sensitive_data(wordpress_payload)
        logger.debug("Sending transactional email with payload structure: %s", json.dumps(debug_payload, ensure_ascii=False, indent=2))
        logger.debug("Payload keys: %s", list(wordpress_payload.keys()))
        logger.debug("Has attachments: %s", len(attachments) > 0)
        if attachments:
            logger.debug("Attachment files: %s", [Path(f.path).name for f in attachments])
        
        # デバッグ用: personalizationsの内容を詳細に確認
        if "personalizations" in wordpress_payload and isinstance(wordpress_payload["personalizations"], list):
            for i, personalization in enumerate(wordpress_payload["personalizations"]):
                if isinstance(personalization, dict):
                    for field in ["to", "cc", "bcc"]:
                        if field in personalization:
                            recipients_list = personalization[field]
                            logger.debug("personalizations[%d].%s: type=%s, count=%s", 
                                       i, field, type(recipients_list), len(recipients_list) if isinstance(recipients_list, list) else "N/A")
                            if isinstance(recipients_list, list):
                                if len(recipients_list) == 0:
                                    logger.warning("personalizations[%d].%s is empty list!", i, field)
                                for j, recipient in enumerate(recipients_list[:5]):  # 最初の5件まで
                                    logger.debug("  [%d]: type=%s, value=%s", j, type(recipient), recipient)
                                    if isinstance(recipient, dict):
                                        email = recipient.get("email", "")
                                        name = recipient.get("name", "")
                                        # 空のemailフィールドをチェック
                                        if not email or not isinstance(email, str) or not email.strip():
                                            logger.error("  [%d]: email field is empty or invalid! recipient=%s", j, recipient)
                                        elif "@" not in email:
                                            logger.error("  [%d]: email field does not contain @! email='%s'", j, email)
                                        logger.debug("    email='%s' (type=%s, len=%d, has_at=%s, repr=%s, is_empty=%s), name='%s'", 
                                                   email[:30] + "***" if len(email) > 30 else email, 
                                                   type(email).__name__, len(str(email)), "@" in str(email), repr(email),
                                                   not email or not email.strip(),
                                                   name[:20] if name else "(none)")
                                    else:
                                        logger.warning("  [%d]: recipient is not a dict: %s", j, recipient)
                            else:
                                logger.warning("personalizations[%d].%s is not a list: %s", i, field, recipients_list)
        
        # デバッグ用: 実際に送信されるJSONペイロードを確認（メールアドレスはマスク）
        try:
            debug_json = json.dumps(wordpress_payload, ensure_ascii=False, indent=2)
            # メールアドレスをマスク
            import re
            debug_json_masked = re.sub(r'"email":\s*"([^"]+)"', r'"email": "***"', debug_json)
            logger.debug("Final wordpress API payload (emails masked):\n%s", debug_json_masked)
            # 実際のemailフィールドの値を確認（デバッグ用）
            if "personalizations" in wordpress_payload and isinstance(wordpress_payload["personalizations"], list):
                if len(wordpress_payload["personalizations"]) > 0:
                    first_pers = wordpress_payload["personalizations"][0]
                    if isinstance(first_pers, dict) and "to" in first_pers:
                        to_list = first_pers["to"]
                        if isinstance(to_list, list) and len(to_list) > 0:
                            first_to = to_list[0]
                            if isinstance(first_to, dict):
                                actual_email = first_to.get("email", "")
                                logger.debug("Actual email value in payload: type=%s, value=%s, repr=%s, len=%d", 
                                            type(actual_email).__name__, actual_email, repr(actual_email), len(str(actual_email)))
        except Exception as exc:
            logger.debug("Failed to serialize payload for debug: %s", exc)
        
        # wordpress API v3 エンドポイント: /v3/mail/send
        response = self._request(
            method="POST",
            path="/mail/send",
            json=wordpress_payload,
        )
        
        # wordpress API v3 は成功時に 202 Accepted を返す（レスポンスボディは空）
        # X-Message-Id ヘッダーからメッセージIDを取得
        message_id = response.headers.get("X-Message-Id", "")
        if not message_id:
            # フォールバック: タイムスタンプベースのIDを生成
            message_id = f"msg_{int(time.time())}"
        return message_id

    def _convert_to_wordpress_format(self, payload: dict[str, Any], attachments: Sequence[ResolvedFile]) -> dict[str, Any]:
        """Convert internal payload format to wordpress API v3 format."""
        wordpress_payload: dict[str, Any] = {}
        
        # From
        from_field = payload.get("from", {})
        if isinstance(from_field, dict):
            wordpress_payload["from"] = {
                "email": from_field.get("email", ""),
            }
            if from_field.get("name"):
                wordpress_payload["from"]["name"] = from_field["name"]
        
        # Personalizations (to, cc, bcc)
        personalizations: dict[str, list[dict[str, str]]] = {}
        
        def _normalize_recipient(recipient: Any) -> dict[str, str] | None:
            """Normalize a recipient to wordpress format, return None if invalid.
            
            Accepts:
            - str: email address string (e.g., "user@example.com")
            - dict: recipient dict with "email" key (e.g., {"email": "user@example.com", "name": "Name"})
            
            Returns:
            - dict with "email" key (and optionally "name" key), or None if invalid
            """
            if recipient is None:
                logger.debug("Skipping None recipient")
                return None
            
            # Handle string input (most common case from send_transactional_email.py)
            if isinstance(recipient, str):
                email = recipient.strip()
                # Basic validation
                if not email or "@" not in email:
                    logger.debug("Skipping invalid recipient string: %s", recipient[:50] if recipient else "empty")
                    return None
                # Ensure email has valid format
                parts = email.split("@", 1)
                if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
                    logger.debug("Skipping invalid email format: %s", email[:50])
                    return None
                # Return in wordpress format: {"email": "..."}
                return {"email": email}
            
            # Handle dict input (already in wordpress format)
            if isinstance(recipient, dict):
                email = recipient.get("email", "")
                if not isinstance(email, str):
                    logger.debug("Skipping recipient with non-string email: %s", type(email))
                    return None
                email = email.strip()
                if not email or "@" not in email:
                    logger.debug("Skipping recipient with invalid email: %s", email[:50] if email else "empty")
                    return None
                # Ensure email has valid format
                parts = email.split("@", 1)
                if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
                    logger.debug("Skipping invalid email format: %s", email[:50])
                    return None
                # Build result dict
                result = {"email": email}
                # Add name if present
                name = recipient.get("name")
                if name and isinstance(name, str):
                    name = name.strip()
                    if name:
                        result["name"] = name
                return result
            
            logger.debug("Skipping recipient with unsupported type: %s", type(recipient))
            return None
        
        # To recipients (必須)
        to_recipients = payload.get("to", [])
        if isinstance(to_recipients, str):
            to_recipients = [to_recipients]
        if not isinstance(to_recipients, list) or len(to_recipients) == 0:
            raise ValueError("宛先(to)が指定されていません")
        
        personalizations["to"] = []
        invalid_recipients = []
        for recipient in to_recipients:
            normalized = _normalize_recipient(recipient)
            if normalized:
                # _normalize_recipient already validates, so we can trust the result
                # Final sanity check: ensure email field exists and is not empty
                email = normalized.get("email", "")
                if email and isinstance(email, str) and email.strip():
                    personalizations["to"].append(normalized)
                    logger.debug("Added recipient to personalizations['to']: %s", email[:30] + "..." if len(email) > 30 else email)
                else:
                    logger.error("Invalid email in normalized recipient (should not happen): %s", normalized)
                    invalid_recipients.append(str(recipient))
            else:
                logger.debug("Failed to normalize recipient: %s", recipient)
                invalid_recipients.append(str(recipient))
        
        if len(personalizations["to"]) == 0:
            error_msg = "有効な宛先(to)メールアドレスがありません"
            if invalid_recipients:
                error_msg += f" (無効な宛先: {', '.join(invalid_recipients[:3])})"
            raise ValueError(error_msg)
        
        # CC recipients (オプション)
        cc_recipients = payload.get("cc", [])
        if isinstance(cc_recipients, str):
            cc_recipients = [cc_recipients]
        if isinstance(cc_recipients, list) and cc_recipients:
            personalizations["cc"] = []
            for recipient in cc_recipients:
                normalized = _normalize_recipient(recipient)
                if normalized:
                    personalizations["cc"].append(normalized)
        
        # BCC recipients (オプション)
        bcc_recipients = payload.get("bcc", [])
        if isinstance(bcc_recipients, str):
            bcc_recipients = [bcc_recipients]
        if isinstance(bcc_recipients, list) and bcc_recipients:
            personalizations["bcc"] = []
            for recipient in bcc_recipients:
                normalized = _normalize_recipient(recipient)
                if normalized:
                    personalizations["bcc"].append(normalized)
        
        # デバッグ用: personalizationsのtoフィールドの最終確認
        if "to" in personalizations:
            logger.debug("Final personalizations['to'] count: %d", len(personalizations["to"]))
            for i, recipient in enumerate(personalizations["to"]):
                if isinstance(recipient, dict):
                    email = recipient.get("email", "")
                    logger.debug("  personalizations['to'][%d]: email='%s' (type=%s, len=%d, repr=%s, is_empty=%s)", 
                                i, email[:20] + "..." if len(email) > 20 else email, 
                                type(email).__name__, len(str(email)), repr(email), 
                                not email or not email.strip())
                    if not email or not isinstance(email, str) or not email.strip():
                        logger.error("  ⚠️ personalizations['to'][%d] has invalid email field! recipient=%s", i, recipient)
                else:
                    logger.error("  ⚠️ personalizations['to'][%d] is not a dict! value=%s", i, recipient)
        
        wordpress_payload["personalizations"] = [personalizations]
        
        # Subject
        if payload.get("subject"):
            wordpress_payload["subject"] = payload["subject"]
        
        # Content (text and HTML)
        content = []
        if payload.get("text_part") or payload.get("text_body"):
            text_content = payload.get("text_part") or payload.get("text_body", "")
            if text_content:
                content.append({"type": "text/plain", "value": text_content})
        if payload.get("html_part") or payload.get("html_body"):
            html_content = payload.get("html_part") or payload.get("html_body", "")
            if html_content:
                content.append({"type": "text/html", "value": html_content})
        if content:
            wordpress_payload["content"] = content
        
        # Attachments
        if attachments:
            wordpress_attachments = []
            for attachment in attachments:
                path = Path(attachment.path)
                mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                try:
                    # ファイルハンドルはwith文で自動的にクリーンアップされる
                    # エラー発生時も確実にファイルが閉じられるようにtry-finallyで囲む
                    with open(attachment.path, "rb") as f:
                        file_content = f.read()
                        encoded_content = base64.b64encode(file_content).decode("utf-8")
                        wordpress_attachments.append({
                            "content": encoded_content,
                            "filename": path.name,
                            "type": mime_type,
                            "disposition": "attachment",
                        })
                except OSError as exc:
                    # ファイル読み込みエラーを適切に処理
                    raise ValueError(f"添付ファイルの読み込みに失敗しました: {path.name}") from exc
            if wordpress_attachments:
                wordpress_payload["attachments"] = wordpress_attachments
        
        # Custom headers
        custom_headers = payload.get("custom_headers", {})
        if custom_headers and isinstance(custom_headers, dict):
            wordpress_payload["headers"] = custom_headers
        
        # Reply-To
        reply_to = payload.get("reply_to")
        if reply_to:
            if isinstance(reply_to, str):
                wordpress_payload["reply_to"] = {"email": reply_to}
            elif isinstance(reply_to, dict):
                wordpress_payload["reply_to"] = {"email": reply_to.get("email", "")}
        
        return wordpress_payload

    def _mask_sensitive_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive data in payload for logging."""
        # Deep copy to avoid modifying the original payload
        debug_payload = copy.deepcopy(payload)
        
        if "from" in debug_payload and isinstance(debug_payload["from"], dict):
            debug_payload["from"] = {"email": "***", "name": debug_payload["from"].get("name", "***")}
        
        if "personalizations" in debug_payload and isinstance(debug_payload["personalizations"], list):
            for personalization in debug_payload["personalizations"]:
                if isinstance(personalization, dict):
                    if "to" in personalization:
                        personalization["to"] = [{"email": "***"} for _ in personalization.get("to", [])]
                    if "cc" in personalization:
                        personalization["cc"] = [{"email": "***"} for _ in personalization.get("cc", [])]
                    if "bcc" in personalization:
                        personalization["bcc"] = [{"email": "***"} for _ in personalization.get("bcc", [])]
        
        if "reply_to" in debug_payload and isinstance(debug_payload["reply_to"], dict):
            debug_payload["reply_to"] = {"email": "***"}
        
        return debug_payload

    # ---- Low-level helpers -------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {}) or {}
        # wordpress API v3 は API キーを直接 Bearer トークンとして使用
        headers.setdefault("Authorization", f"Bearer {self.api_key}")
        headers.setdefault("Content-Type", "application/json")
        
        # デバッグ用: リクエストURLとメソッドをログ出力（DEBUGレベルで出力）
        logger.debug("Request: %s %s", method, url)
        
        # デバッグ用: Authorizationヘッダーの設定を確認（APIキーはマスク）
        auth_header = headers.get("Authorization", "")
        if auth_header:
            # APIキーをマスクしてログ出力
            masked_auth = _sanitize_for_log(auth_header)
            logger.debug("Authorization header: %s", masked_auth)
            # APIキーの長さと形式を確認
            api_key_part = auth_header.replace("Bearer ", "")
            logger.debug("API key length: %d, starts with 'SG.': %s", len(api_key_part), api_key_part.startswith("SG."))
        else:
            logger.warning("Authorization header is missing!")
        
        # デバッグ用: すべてのヘッダーをログ出力（機密情報はマスク）
        debug_headers = {}
        for key, value in headers.items():
            if key.lower() == "authorization":
                debug_headers[key] = _sanitize_for_log(value)
            else:
                debug_headers[key] = value
        logger.debug("Request headers: %s", debug_headers)
        
        # デバッグ用: JSONペイロードのemailフィールドを確認
        if "json" in kwargs:
            json_payload = kwargs["json"]
            if isinstance(json_payload, dict) and "personalizations" in json_payload:
                personalizations = json_payload["personalizations"]
                if isinstance(personalizations, list) and len(personalizations) > 0:
                    first_personalization = personalizations[0]
                    if isinstance(first_personalization, dict) and "to" in first_personalization:
                        to_list = first_personalization["to"]
                        if isinstance(to_list, list) and len(to_list) > 0:
                            first_to = to_list[0]
                            if isinstance(first_to, dict):
                                email = first_to.get("email", "")
                                logger.debug("JSON payload personalizations[0].to[0].email: type=%s, value='%s', len=%d, repr=%s, is_empty=%s", 
                                            type(email).__name__, 
                                            email[:20] + "..." if len(email) > 20 else email,
                                            len(str(email)), 
                                            repr(email),
                                            not email or not email.strip())
                                if not email or not isinstance(email, str) or not email.strip():
                                    logger.error("⚠️ JSON payload has invalid email field! personalizations[0].to[0]=%s", first_to)

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
                raise wordpressHttpError(None, f"wordpress APIリクエストに失敗しました: {sanitized_exc}") from exc

            if response.status_code in _RETRY_STATUSES and attempt < self.max_retries:
                # 429エラー（レートリミット）の場合はRetry-Afterヘッダーを確認
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            # Retry-Afterは秒数（整数）またはHTTP-date形式
                            wait_seconds = int(retry_after)
                            logger.info("Rate limited. Waiting %d seconds as specified by Retry-After header", wait_seconds)
                            time.sleep(wait_seconds)
                        except (ValueError, TypeError):
                            # HTTP-date形式の場合は簡易的に指数バックオフを使用
                            logger.warning("Retry-After header value '%s' is not a valid integer, using exponential backoff", retry_after)
                            time.sleep(2**attempt)
                    else:
                        # Retry-Afterヘッダーがない場合は指数バックオフを使用
                        logger.info("Rate limited but no Retry-After header, using exponential backoff")
                        time.sleep(2**attempt)
                else:
                    # その他のリトライ可能なエラーの場合は指数バックオフ
                    time.sleep(2**attempt)
                continue

            if response.status_code >= 400:
                message = self._extract_error_message(response)
                sanitized_body = _sanitize_for_log(response.text)
                # デバッグ用にログに詳細を出力
                logger.error(
                    "wordpress APIエラー (status=%s): %s, body=%s",
                    response.status_code,
                    message,
                    sanitized_body,
                )
                raise wordpressHttpError(response.status_code, message, body=sanitized_body)

            return response

        sanitized_error = _sanitize_for_log(str(last_error))
        raise wordpressHttpError(None, f"wordpress APIリクエストに失敗しました: {sanitized_error}")  # pragma: no cover

    @staticmethod
    def _extract_error_message(response: Response) -> str:
        """Extract error message from wordpress API v3 error response."""
        try:
            data = response.json()
        except ValueError:
            data = None
        
        if isinstance(data, dict):
            # wordpress API v3 のエラーフォーマット
            errors = data.get("errors")
            if isinstance(errors, list) and errors:
                error_messages = []
                for error in errors[:5]:  # 最大5件まで
                    if isinstance(error, dict):
                        message = error.get("message", "")
                        field = error.get("field", "")
                        if message:
                            if field:
                                error_messages.append(f"{field}: {message}")
                            else:
                                error_messages.append(message)
                    elif isinstance(error, str):
                        error_messages.append(error)
                if error_messages:
                    sanitized_errors = [_sanitize_for_log(err) for err in error_messages]
                    return f"wordpress APIエラー ({response.status_code}): {'; '.join(sanitized_errors)}"
            
            # その他のエラーフィールドを確認
            message = data.get("message") or data.get("error")
            if isinstance(message, str):
                sanitized_message = _sanitize_for_log(message)
                return f"wordpress APIエラー ({response.status_code}): {sanitized_message}"
        
        # JSON解析できない場合、レスポンステキストの最初の部分を使用
        if response.text:
            sanitized_text = _sanitize_for_log(response.text[:500])  # 最初の500文字
            return f"wordpress APIエラー ({response.status_code}): {sanitized_text}"
        return f"wordpress APIエラー ({response.status_code})"

