# where: wordpress/tools/update_user.py
# what: Implements the update user tool via WordPress REST API.
# why: Allow Dify workflows to update WordPress users.

from __future__ import annotations

import logging
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from . import base
from . import validators

logger = logging.getLogger(__name__)


class UpdateUserTool(base.BaseWordPressTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
        try:
            context = self._load_provider_context()
            client = self._create_http_client(context)

            # パラメータの取得と検証
            user_id = validators.validate_user_id(tool_parameters.get("id"))
            name = tool_parameters.get("name")
            email = tool_parameters.get("email")
            description = tool_parameters.get("description")
            url = tool_parameters.get("url")
            roles = tool_parameters.get("roles")

            # リクエストデータの構築
            data: dict[str, Any] = {}

            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("ユーザー名が空です")
                data["name"] = name

            if email is not None:
                email = email.strip()
                if not email:
                    raise ValueError("メールアドレスが空です")
                # 簡単なメールアドレス形式チェック
                if "@" not in email or "." not in email.split("@")[-1]:
                    raise ValueError(f"無効なメールアドレス形式です: {email}")
                data["email"] = email

            if description is not None:
                data["description"] = description

            if url is not None:
                url = url.strip()
                if url:
                    # 簡単なURL形式チェック
                    if not url.startswith(("http://", "https://")):
                        raise ValueError(f"URLはhttp://またはhttps://で始まる必要があります: {url}")
                    data["url"] = url

            if roles is not None:
                # rolesは文字列（カンマ区切り）またはリスト
                if isinstance(roles, list):
                    data["roles"] = roles
                elif isinstance(roles, str):
                    # カンマ区切りの文字列をリストに変換
                    role_list = [r.strip() for r in roles.split(",") if r.strip()]
                    if role_list:
                        data["roles"] = role_list
                else:
                    raise ValueError(f"ロールの形式が不正です: {roles}")

            # 更新するデータがない場合
            if not data:
                raise ValueError("更新する項目（name, email, description, url, roles）を少なくとも1つ指定してください")

            # WordPress REST APIを呼び出し
            logger.debug("Updating user ID: %s with data keys: %s", user_id, list(data.keys()))
            response = client.update_user(user_id=user_id, data=data)

            # レスポンスの処理
            updated_user_id = response.get("id")
            updated_name = response.get("name", name or "")
            updated_email = response.get("email", email or "")

            logger.info("Updated WordPress user (ID: %s)", updated_user_id)

            result_text = f"WordPressのユーザーを更新しました (ID: {updated_user_id})"
            if updated_name:
                result_text += f"\n名前: {updated_name}"
            if updated_email:
                result_text += f"\nメール: {updated_email}"

            response_data = {
                "id": updated_user_id,
                "name": updated_name,
                "email": updated_email,
                "roles": response.get("roles", []),
            }

            return [
                self._create_text_message(result_text),
                self._create_json_message(response_data),
            ]
        except Exception as exc:  # noqa: BLE001
            return self._handle_error(exc, "WordPressユーザー更新")

