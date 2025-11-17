# WordPress REST API Plugin for Dify

**Author:** r3-yamauchi  
**Version:** 0.0.1  
**Type:** tool

English | [Japanese](https://github.com/r3-yamauchi/dify-wordpress-plugin/blob/main/readme/README_ja_JP.md)

> ⚠️ **Note: This is an unofficial plugin**  
> This plugin is not developed or maintained by WordPress's official provider. It is a community-developed plugin created by independent developers. Use at your own discretion.

## Description

`wordpress` provides direct REST API integration with WordPress sites for Dify workflows. Manage WordPress posts, pages, and media files without requiring the official WordPress SDK. This implementation uses the `requests` library to call WordPress REST API directly, making it compatible with restricted Dify environments.

The source code of this plugin is available in the [GitHub repository](https://github.com/r3-yamauchi/dify-wordpress-plugin).

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/r3-yamauchi/dify-wordpress-plugin)

## Highlights

- **Post management**: Full CRUD operations for WordPress posts (get, create, update, delete).
- **Page management**: Full CRUD operations for WordPress pages (get, create, update, delete).
- **Media management**: Full CRUD operations for WordPress media files (get, upload, update, delete).
- **Category management**: Full CRUD operations for WordPress categories (get, create, update, delete).
- **Tag management**: Full CRUD operations for WordPress tags (get, create, update, delete).
- **Comment management**: Full CRUD operations for WordPress comments (get, create, update, delete).
- **WordPress.com MCP features**: Support for WordPress.com MCP server features (site settings, statistics, users, comments, plugins, etc.).
- **Authentication**: Secure authentication using WordPress Application Passwords.
- **Direct REST API**: No dependency on the official WordPress SDK. Uses HTTP client with built-in retry logic and rate-limit handling.
- **Security**: Debug logs are properly sanitized to prevent sensitive information leakage in production environments.
- **Error handling**: Comprehensive error handling with helpful hints for common issues.

## Provider Setup

1. Upload/package the plugin in Dify.
2. Configure credentials:
   - `wordpress_url` *(required)* – WordPress site URL (e.g., https://example.com).
   - `username` *(required)* – WordPress username for authentication.
   - `application_password` *(secret, required)* – Application password generated from WordPress user profile.
3. Drop the tools into your workflow nodes and map parameters.

### How to Generate Application Password

1. Log in to your WordPress admin panel.
2. Go to Users → Profile.
3. Scroll down to "Application Passwords" section.
4. Enter a name for the application (e.g., "Dify Plugin").
5. Click "Add New Application Password".
6. Copy the generated password (it will only be shown once).

## Tools

### `get_posts`
Retrieve posts from WordPress site with optional filtering.

- **Inputs**: 
  - `per_page` (optional): Number of posts per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter posts
  - `status` (optional): Filter by status (publish, draft, pending, private, future, trash)
  - `categories` (optional): Filter by category IDs (single ID, comma-separated IDs, or array of IDs)
  - `tags` (optional): Filter by tag IDs (single ID, comma-separated IDs, or array of IDs)
- **Outputs**: Array of posts with ID, title, content, status, and other metadata.

### `create_post`
Create a new post in WordPress.

- **Inputs**:
  - `title` (required): Post title (max 255 characters)
  - `content` (required): Post content in HTML format
  - `status` (optional): Post status (publish, draft, pending, private, future). Default is draft.
  - `featured_media` (optional): Featured media (image) ID for post thumbnail
  - `categories` (optional): Category IDs to assign to the post. Can be a single ID, comma-separated IDs (e.g., "1,2,3"), or an array of IDs. You can use IDs retrieved from the `get_categories` tool.
  - `tags` (optional): Tag IDs to assign to the post. Can be a single ID, comma-separated IDs (e.g., "1,2,3"), or an array of IDs. You can use IDs retrieved from the `get_tags` tool.
- **Outputs**: Created post information including ID, title, link, and status.

### `update_post`
Update an existing WordPress post.

- **Inputs**:
  - `id` (required): Post ID to update
  - `title` (optional): New post title
  - `content` (optional): New post content
  - `status` (optional): New post status
  - `featured_media` (optional): New featured media ID (set to 0 to remove)
  - `categories` (optional): Category IDs to assign to the post. Can be a single ID, comma-separated IDs (e.g., "1,2,3"), or an array of IDs. You can use IDs retrieved from the `get_categories` tool.
  - `tags` (optional): Tag IDs to assign to the post. Can be a single ID, comma-separated IDs (e.g., "1,2,3"), or an array of IDs. You can use IDs retrieved from the `get_tags` tool.
- **Outputs**: Updated post information.

### `delete_post`
Delete a WordPress post.

- **Inputs**:
  - `id` (required): Post ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with post ID and deletion status.

### `get_pages`
Retrieve pages from WordPress site with optional filtering.

- **Inputs**: 
  - `per_page` (optional): Number of pages per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter pages
  - `status` (optional): Filter by status (publish, draft, pending, private, future, trash)
- **Outputs**: Array of pages with ID, title, content, status, and other metadata.

### `create_page`
Create a new page in WordPress.

- **Inputs**:
  - `title` (required): Page title (max 255 characters)
  - `content` (required): Page content in HTML format
  - `status` (optional): Page status (publish, draft, pending, private, future). Default is draft.
  - `featured_media` (optional): Featured media (image) ID for page thumbnail
  - `parent` (optional): Parent page ID to create a child page
- **Outputs**: Created page information including ID, title, link, and status.

### `update_page`
Update an existing WordPress page.

- **Inputs**:
  - `id` (required): Page ID to update
  - `title` (optional): New page title
  - `content` (optional): New page content
  - `status` (optional): New page status
  - `featured_media` (optional): New featured media ID (set to 0 to remove)
  - `parent` (optional): New parent page ID (set to 0 to remove parent relationship)
- **Outputs**: Updated page information.

### `delete_page`
Delete a WordPress page.

- **Inputs**:
  - `id` (required): Page ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with page ID and deletion status.

### `get_media`
Retrieve media files from WordPress site with optional filtering.

- **Inputs**: 
  - `per_page` (optional): Number of media items per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter media
  - `media_type` (optional): Filter by media type (image, video, audio, application, etc.)
  - `mime_type` (optional): Filter by MIME type (e.g., image/jpeg, image/png, video/mp4)
- **Outputs**: Array of media items with ID, title, URL, MIME type, and other metadata.

### `upload_media`
Upload a media file (image, video, audio, etc.) to WordPress.

- **Inputs**:
  - `file` (required): Media file to upload
  - `title` (optional): Media title
  - `caption` (optional): Media caption (displayed below the media)
  - `alt_text` (optional): Alternative text for accessibility
  - `description` (optional): Media description
- **Outputs**: Uploaded media information including ID, title, URL, and MIME type.

### `update_media`
Update metadata of an existing WordPress media file.

- **Inputs**:
  - `id` (required): Media ID to update
  - `title` (optional): New media title
  - `caption` (optional): New media caption
  - `alt_text` (optional): New alternative text
  - `description` (optional): New media description
- **Outputs**: Updated media information.

### `delete_media`
Delete a WordPress media file.

- **Inputs**:
  - `id` (required): Media ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with media ID and deletion status.

### `get_post_details`
Retrieve detailed information about a specific WordPress post by its ID.

- **Inputs**:
  - `post_id` (required): The ID of the post to retrieve
- **Outputs**: Detailed post information including ID, title, content, status, and metadata.

### `get_site_settings`
Retrieve WordPress site settings.

- **Inputs**: None
- **Outputs**: Site settings including title, description, URL, and other general settings.

### `get_site_users`
Retrieve users from WordPress site with optional filtering.

- **Inputs**:
  - `per_page` (optional): Number of users per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter users by name, email, or username
  - `roles` (optional): Filter users by role (e.g., "administrator", "editor", "author"). Multiple roles can be specified as comma-separated values
- **Outputs**: Array of users with ID, name, email, and role.

### `update_user`
Update an existing WordPress user.

- **Inputs**:
  - `id` (required): User ID to update
  - `name` (optional): New display name for the user
  - `email` (optional): New email address for the user
  - `description` (optional): New description/biography for the user
  - `url` (optional): New website URL for the user
  - `roles` (optional): New roles for the user. Can be a single role or comma-separated roles (e.g., "administrator", "editor,author")
- **Outputs**: Updated user information including ID, name, email, and roles.

### `get_comments`
Retrieve comments from WordPress site with optional filtering.

- **Inputs**:
  - `per_page` (optional): Number of comments per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter comments by content
  - `post_id` (optional): Filter comments by post ID
  - `status` (optional): Filter comments by status (approved, hold, spam, trash)
- **Outputs**: Array of comments with ID, content, post ID, and status.

### `get_plugins`
Retrieve information about installed plugins on the WordPress site.

- **Inputs**: None
- **Outputs**: Information about installed plugins including name, version, and status.

### `get_site_statistics`
Retrieve WordPress site statistics.

- **Inputs**: None
- **Outputs**: Site statistics including visitor data and performance metrics.
- **Note**: This feature may require WordPress.com specific API endpoints. May not be available on standard WordPress installations.

### `get_categories`
Retrieve categories from WordPress site with optional filtering.

- **Inputs**:
  - `per_page` (optional): Number of categories per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter categories by name
- **Outputs**: Array of categories with ID, name, description, and slug.

### `create_category`
Create a new category in WordPress.

- **Inputs**:
  - `name` (required): Category name
  - `description` (optional): Category description
  - `slug` (optional): Category slug (URL-friendly name)
  - `parent` (optional): Parent category ID to create a subcategory
- **Outputs**: Created category information including ID, name, slug, and description.

### `update_category`
Update an existing WordPress category.

- **Inputs**:
  - `id` (required): Category ID to update
  - `name` (optional): New category name
  - `description` (optional): New category description
  - `slug` (optional): New category slug
  - `parent` (optional): New parent category ID (set to 0 to remove parent relationship)
- **Outputs**: Updated category information.

### `delete_category`
Delete a WordPress category.

- **Inputs**:
  - `id` (required): Category ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with category ID and deletion status.

### `get_tags`
Retrieve tags from WordPress site with optional filtering.

- **Inputs**:
  - `per_page` (optional): Number of tags per page (default: 10, max: 100)
  - `page` (optional): Page number (default: 1)
  - `search` (optional): Search query to filter tags by name
- **Outputs**: Array of tags with ID, name, description, and slug.

### `create_tag`
Create a new tag in WordPress.

- **Inputs**:
  - `name` (required): Tag name
  - `description` (optional): Tag description
  - `slug` (optional): Tag slug (URL-friendly name)
- **Outputs**: Created tag information including ID, name, slug, and description.

### `update_tag`
Update an existing WordPress tag.

- **Inputs**:
  - `id` (required): Tag ID to update
  - `name` (optional): New tag name
  - `description` (optional): New tag description
  - `slug` (optional): New tag slug
- **Outputs**: Updated tag information.

### `delete_tag`
Delete a WordPress tag.

- **Inputs**:
  - `id` (required): Tag ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with tag ID and deletion status.

### `create_comment`
Create a new comment on a WordPress post.

- **Inputs**:
  - `post_id` (required): The ID of the post to comment on
  - `content` (required): Comment content
  - `author_name` (optional): Comment author name
  - `author_email` (optional): Comment author email address
  - `parent` (optional): Parent comment ID to create a reply comment
- **Outputs**: Created comment information including ID, post ID, content, and status.

### `update_comment`
Update an existing WordPress comment.

- **Inputs**:
  - `id` (required): Comment ID to update
  - `content` (optional): New comment content
  - `status` (optional): New comment status (approved, hold, spam, trash)
- **Outputs**: Updated comment information.

### `delete_comment`
Delete a WordPress comment.

- **Inputs**:
  - `id` (required): Comment ID to delete
  - `force` (optional): If true, permanently delete. If false (default), move to trash.
- **Outputs**: Deletion result with comment ID and deletion status.

## Requirements

- WordPress 5.6 or higher (for Application Passwords support)
- WordPress REST API enabled (default in WordPress 4.7+)
- User account with appropriate permissions (Editor or Administrator recommended)

## Security Considerations

1. **HTTPS**: Always use HTTPS for WordPress site URL to protect credentials.
2. **Application Passwords**: Use Application Passwords instead of your main WordPress password.
3. **Permissions**: Grant only necessary permissions to the WordPress user account.
4. **Rate Limiting**: The plugin includes automatic retry logic for rate-limited requests.

## License

MIT License — full text in `LICENSE`.
