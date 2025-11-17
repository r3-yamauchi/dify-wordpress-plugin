# where: wordpress/tools/validators.py
# what: Validation utilities for WordPress REST API payload fields.
# why: Keep tool logic focused on WordPress REST API orchestration.

from __future__ import annotations

import re
from typing import Any

# WordPress投稿タイトルの最大長（WordPressのデフォルト制限）
MAX_TITLE_LENGTH = 255

# WordPress投稿ステータスの有効な値
VALID_POST_STATUSES = {"publish", "draft", "pending", "private", "future", "trash"}


def validate_wordpress_url(url: str) -> None:
    """Validate WordPress site URL format."""
    if not url or not url.strip():
        raise ValueError("WordPressサイトURLを入力してください")
    
    url = url.strip()
    
    # 基本的なURL形式チェック
    if not url.startswith(("http://", "https://")):
        raise ValueError("WordPressサイトURLはhttp://またはhttps://で始まる必要があります")
    
    # ドメイン部分の存在確認
    if "@" in url or "//" not in url:
        raise ValueError("WordPressサイトURLの形式が不正です")


def validate_post_title(title: str | None) -> None:
    """Validate WordPress post title."""
    if not title:
        raise ValueError("投稿タイトルを入力してください")
    
    title = title.strip()
    
    if not title:
        raise ValueError("投稿タイトルが空です")
    
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"投稿タイトルが長すぎます（最大{MAX_TITLE_LENGTH}文字）")


def validate_post_content(content: str | None) -> None:
    """Validate WordPress post content."""
    if content is None:
        raise ValueError("投稿本文を入力してください")
    
    # 空文字列は許可（ただし警告は出る可能性がある）
    # WordPressでは空の投稿も作成可能だが、通常は本文があるべき


def validate_post_status(status: str | None) -> None:
    """Validate WordPress post status."""
    if status is None:
        return  # ステータスはオプショナル
    
    status = status.strip().lower()
    
    if status not in VALID_POST_STATUSES:
        valid_statuses = ", ".join(sorted(VALID_POST_STATUSES))
        raise ValueError(f"無効な投稿ステータスです。有効な値: {valid_statuses}")


def validate_post_id(post_id: Any) -> int:
    """Validate and convert post ID to integer."""
    if post_id is None:
        raise ValueError("投稿IDを指定してください")
    
    try:
        post_id_int = int(post_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"投稿IDは整数である必要があります: {post_id}") from exc
    
    if post_id_int <= 0:
        raise ValueError(f"投稿IDは正の整数である必要があります: {post_id_int}")
    
    return post_id_int


def validate_user_id(user_id: Any) -> int:
    """Validate and convert user ID to integer."""
    if user_id is None:
        raise ValueError("ユーザーIDを指定してください")
    
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"ユーザーIDは整数である必要があります: {user_id}") from exc
    
    if user_id_int <= 0:
        raise ValueError(f"ユーザーIDは正の整数である必要があります: {user_id_int}")
    
    return user_id_int


def validate_comment_id(comment_id: Any) -> int:
    """Validate and convert comment ID to integer."""
    if comment_id is None:
        raise ValueError("コメントIDを指定してください")
    
    try:
        comment_id_int = int(comment_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"コメントIDは整数である必要があります: {comment_id}") from exc
    
    if comment_id_int <= 0:
        raise ValueError(f"コメントIDは正の整数である必要があります: {comment_id_int}")
    
    return comment_id_int


def validate_category_id(category_id: Any) -> int:
    """Validate and convert category ID to integer."""
    if category_id is None:
        raise ValueError("カテゴリーIDを指定してください")
    
    try:
        category_id_int = int(category_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"カテゴリーIDは整数である必要があります: {category_id}") from exc
    
    if category_id_int <= 0:
        raise ValueError(f"カテゴリーIDは正の整数である必要があります: {category_id_int}")
    
    return category_id_int


def validate_tag_id(tag_id: Any) -> int:
    """Validate and convert tag ID to integer."""
    if tag_id is None:
        raise ValueError("タグIDを指定してください")
    
    try:
        tag_id_int = int(tag_id)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"タグIDは整数である必要があります: {tag_id}") from exc
    
    if tag_id_int <= 0:
        raise ValueError(f"タグIDは正の整数である必要があります: {tag_id_int}")
    
    return tag_id_int


def validate_per_page(per_page: Any, max_per_page: int = 100) -> int:
    """Validate and convert per_page parameter."""
    if per_page is None:
        return 10  # デフォルト値
    
    try:
        per_page_int = int(per_page)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"per_pageは整数である必要があります: {per_page}") from exc
    
    if per_page_int <= 0:
        raise ValueError(f"per_pageは正の整数である必要があります: {per_page_int}")
    
    if per_page_int > max_per_page:
        raise ValueError(f"per_pageは最大{max_per_page}までです: {per_page_int}")
    
    return per_page_int


def validate_page_number(page: Any) -> int:
    """Validate and convert page number."""
    if page is None:
        return 1  # デフォルト値
    
    try:
        page_int = int(page)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"pageは整数である必要があります: {page}") from exc
    
    if page_int < 1:
        raise ValueError(f"pageは1以上である必要があります: {page_int}")
    
    return page_int


def validate_search_query(search: str | None) -> str | None:
    """Validate search query string."""
    if search is None:
        return None
    
    search = search.strip()
    
    if not search:
        return None
    
    # 検索クエリの長さチェック（WordPressの制限に合わせる）
    if len(search) > 200:
        raise ValueError(f"検索クエリが長すぎます（最大200文字）")
    
    return search


def normalize_categories(categories: Any) -> list[int]:
    """Normalize and validate category IDs."""
    if categories is None:
        return []
    
    if isinstance(categories, (int, str)):
        try:
            return [int(categories)]
        except (ValueError, TypeError) as exc:
            raise ValueError(f"カテゴリーIDは整数である必要があります: {categories}") from exc
    
    if isinstance(categories, (list, tuple)):
        category_ids = []
        for cat in categories:
            try:
                cat_id = int(cat)
                if cat_id > 0:
                    category_ids.append(cat_id)
            except (ValueError, TypeError):
                raise ValueError(f"カテゴリーIDは整数である必要があります: {cat}")
        return category_ids
    
    raise ValueError(f"カテゴリーIDの形式が不正です: {categories}")


def normalize_tags(tags: Any) -> list[int]:
    """Normalize and validate tag IDs."""
    if tags is None:
        return []
    
    if isinstance(tags, (int, str)):
        try:
            return [int(tags)]
        except (ValueError, TypeError) as exc:
            raise ValueError(f"タグIDは整数である必要があります: {tags}") from exc
    
    if isinstance(tags, (list, tuple)):
        tag_ids = []
        for tag in tags:
            try:
                tag_id = int(tag)
                if tag_id > 0:
                    tag_ids.append(tag_id)
            except (ValueError, TypeError):
                raise ValueError(f"タグIDは整数である必要があります: {tag}")
        return tag_ids
    
    raise ValueError(f"タグIDの形式が不正です: {tags}")
