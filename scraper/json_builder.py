"""
JSON builder for Facebook scraper output
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

class JSONBuilder:
    def __init__(self, output_dir: str = "../static/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def build_profile_json(self, username: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a structured JSON output from all scraped data"""
        # Get basic info from the "profile" key
        basic_info = data.get("profile", {})
        
        # Format all data into the exact requested JSON structure
        profile_data = {
            "profile": {
                "name": basic_info.get("name", ""),
                "bio": basic_info.get("bio", ""),
                "about": {
                    "work": basic_info.get("work", ""),  # Now directly use the string
                    "education": basic_info.get("education", ""),  # Now directly use the string
                    "location": basic_info.get("location", ""),  # Use the combined location field
                    "birthday": basic_info.get("birthday", ""),
                    "contact": {
                        "email": basic_info.get("email", ""),
                        "phone": basic_info.get("phone", "")
                    }
                },
                "friends": self._format_friends(data.get("friends_list", [])),
                "pages_followed": self._format_pages(data.get("pages_followed", [])),
                "following": self._format_following(data.get("following_list", [])),
                "groups": self._format_groups(data.get("groups", []))
            },
            "posts": self._format_all_posts(data.get("posts", {})),
            "locations_visited": self._format_locations(data.get("locations", []))
        }
        
        # Add extraction metadata
        profile_data["extraction_metadata"] = {
            "username": username,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "total_items": self._count_total_items(profile_data)
        }
        
        # Save JSON to file with timestamp
        timestamp = int(time.time())
        filepath = os.path.join(self.output_dir, f"{username}_profile_{timestamp}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        # Also save a "latest" version for easy access
        latest_filepath = os.path.join(self.output_dir, f"{username}_profile_latest.json")
        with open(latest_filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
        return {
            "data": profile_data,
            "filepath": filepath,
            "latest_filepath": latest_filepath
        }

    def _format_all_posts(self, posts_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Formats all post types from the new combined dictionary structure."""
        return {
            "own_posts": self._format_posts(posts_data.get("own_posts", [])),
            "tagged_posts": self._format_posts(posts_data.get("tagged_posts", [])),
            "shared_posts": self._format_posts(posts_data.get("shared_posts", [])),
            "comments_by_user": self._format_user_comments(posts_data.get("user_comments", []))
        }

    def _format_work_education(self, items: List[Any]) -> str:
        """Format work or education items - return first item as string or empty string"""
        if not items:
            return ""
        
        # Handle different data types
        if isinstance(items, list):
            if len(items) > 0:
                first_item = items[0]
                if isinstance(first_item, dict):
                    return first_item.get("name", str(first_item))
                return str(first_item)
        
        return str(items) if items else ""

    def _format_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format pages followed to match requested structure"""
        formatted_pages = []
        for page in pages:
            formatted_pages.append({
                "page_name": page.get("page_name", page.get("name", "")),
                "page_url": page.get("page_url", page.get("url", "")),
                "bio": page.get("bio", page.get("description", ""))
            })
        return formatted_pages

    def _format_following(self, following: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format following list to match requested structure"""
        formatted_following = []
        for follow in following:
            formatted_following.append({
                "name": follow.get("name", ""),
                "profile_url": follow.get("profile_url", follow.get("url", "")),
                "bio": follow.get("bio", follow.get("description", ""))
            })
        return formatted_following

    def _format_groups(self, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format groups to match requested structure"""
        formatted_groups = []
        for group in groups:
            formatted_groups.append({
                "group_name": group.get("group_name", group.get("name", "")),
                "group_url": group.get("group_url", group.get("url", "")),
                "bio": group.get("bio", group.get("description", ""))
            })
        return formatted_groups

    def _format_friends(self, friends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format friends list to match requested structure"""
        formatted_friends = []
        for friend in friends:
            formatted_friends.append({
                "name": friend.get("name", ""),
                "profile_url": friend.get("profile_url", friend.get("url", "")),
                "bio": friend.get("bio", friend.get("description", ""))
            })
        return formatted_friends

    def _format_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format posts to match requested structure"""
        formatted_posts = []
        for post in posts:
            formatted_post = {
                "id": post.get("id", ""),
                "timestamp": post.get("timestamp", ""),
                "content": post.get("content", ""),
                "caption": post.get("caption", ""),
                "media_screenshot_url": self._convert_to_relative_path(post.get("media_screenshot_url", post.get("screenshot", ""))),
                "original_url": post.get("original_url", ""),
                "shared": post.get("shared", False),
                "shared_content": post.get("shared_content", ""),
                "original_poster": post.get("original_poster", ""),
                "is_tagged": post.get("is_tagged", False),
                "tagged_accounts": post.get("tagged_accounts", []),
                "location_tagged": post.get("location_tagged", ""),
                "comments": self._format_comments(post.get("comments", [])),
                "reactions": post.get("reactions", {}),
                "comments_count": post.get("comments_count", 0),
                "shares_count": post.get("shares_count", 0),
                "media": post.get("media", [])
            }
            formatted_posts.append(formatted_post)
        return formatted_posts

    def _format_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format comments to match requested structure"""
        formatted_comments = []
        for comment in comments:
            formatted_comment = {
                "commenter": {
                    "name": comment.get("author", comment.get("commenter", {}).get("name", comment.get("name", ""))),
                    "profile_url": comment.get("profile_url", comment.get("commenter", {}).get("profile_url", "")),
                    "bio": comment.get("bio", comment.get("commenter", {}).get("bio", ""))
                },
                "comment_text": comment.get("text", comment.get("comment_text", "")),
                "timestamp": comment.get("timestamp", "")
            }
            formatted_comments.append(formatted_comment)
        return formatted_comments

    def _format_user_comments(self, user_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format user comments to match requested structure"""
        formatted_comments = []
        for comment in user_comments:
            # Handle different data structures
            post_author = comment.get("post_author", {})
            if isinstance(post_author, str):
                post_author = {"name": post_author, "profile_url": "", "bio": ""}
            
            formatted_comment = {
                "post_url": comment.get("post_url", ""),
                "post_author": {
                    "name": post_author.get("name", ""),
                    "profile_url": post_author.get("profile_url", ""),
                    "bio": post_author.get("bio", "")
                },
                "comment_text": comment.get("comment_text", comment.get("text", "")),
                "timestamp": comment.get("timestamp", "")
            }
            formatted_comments.append(formatted_comment)
        return formatted_comments

    def _format_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format locations to match requested structure"""
        formatted_locations = []
        for location in locations:
            formatted_location = {
                "place": location.get("place", location.get("name", "")),
                "timestamp": location.get("timestamp", "")
            }
            formatted_locations.append(formatted_location)
        return formatted_locations
    
    def _count_total_items(self, profile_data: Dict[str, Any]) -> Dict[str, int]:
        """Count total items extracted for statistics"""
        counts = {
            "friends": len(profile_data.get("profile", {}).get("friends", [])),
            "pages_followed": len(profile_data.get("profile", {}).get("pages_followed", [])),
            "following": len(profile_data.get("profile", {}).get("following", [])),
            "groups": len(profile_data.get("profile", {}).get("groups", [])),
            "own_posts": len(profile_data.get("posts", {}).get("own_posts", [])),
            "tagged_posts": len(profile_data.get("posts", {}).get("tagged_posts", [])),
            "shared_posts": len(profile_data.get("posts", {}).get("shared_posts", [])),
            "comments_by_user": len(profile_data.get("posts", {}).get("comments_by_user", [])),
            "locations_visited": len(profile_data.get("locations_visited", []))
        }
        counts["total"] = sum(counts.values())
        return counts
    
    def _process_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process post data to convert file paths to relative URLs"""
        processed_posts = []
        
        for post in posts:
            processed_posts.append({
                "id": post.get("id", ""),
                "timestamp": post.get("timestamp", ""),
                "content": post.get("content", ""),
                "screenshot": self._convert_to_relative_path(post.get("screenshot", "")),
                "reactions_count": post.get("reactions_count", 0),
                "comments": post.get("comments", []),
                "media": post.get("media", [])
            })
            
        return processed_posts
    
    def _convert_to_relative_path(self, filepath: str) -> str:
        """Convert absolute paths to relative paths for web serving"""
        if not filepath:
            return ""
        
        # Handle different path formats
        filepath = str(filepath)
        
        # Convert paths like "../static/screenshots/file.png" to "/static/screenshots/file.png"
        if filepath.startswith("../static"):
            return filepath.replace("../static", "/static")
        
        # Convert absolute paths to relative
        if filepath.startswith("/"):
            path = Path(filepath)
            if "static" in path.parts:
                static_index = path.parts.index("static")
                return "/" + "/".join(path.parts[static_index:])
            elif "output" in path.parts:
                output_index = path.parts.index("output")
                return "/" + "/".join(path.parts[output_index:])
        
        # Handle relative paths
        if "screenshots" in filepath:
            return f"/screenshots/{Path(filepath).name}"
            
        return filepath