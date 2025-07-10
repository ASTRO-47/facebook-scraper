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
        # Get basic info
        basic_info = data.get("basic_info", {})
        
        # Format all data into the requested JSON structure
        profile_data = {
            "profile": {
                "name": basic_info.get("name", ""),
                "bio": basic_info.get("bio", ""),
                "about": {
                    "work": basic_info.get("work", [])[0] if basic_info.get("work") else "",
                    "education": basic_info.get("education", [])[0] if basic_info.get("education") else "",
                    "location": basic_info.get("current_city", ""),
                    "birthday": basic_info.get("birthday", ""),
                    "contact": {
                        "email": basic_info.get("email", ""),
                        "phone": basic_info.get("phone", "")
                    }
                },
                "pages_followed": self._format_pages(data.get("pages_followed", [])),
                "following": self._format_following(data.get("following_list", [])),
                "friends": self._format_friends(data.get("friends_list", [])),
                "groups": self._format_groups(data.get("groups", []))
            },
            "posts": {
                "own_posts": self._format_posts(data.get("own_posts", [])),
                "tagged_posts": self._format_posts(data.get("tagged_posts", [])),
                "comments_by_user": self._format_user_comments(data.get("user_comments", []))
            },
            "locations_visited": self._format_locations(data.get("locations", []))
        }
        
        # Save JSON to file
        timestamp = int(time.time())
        filepath = os.path.join(self.output_dir, f"{username}_profile_{timestamp}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
        return {
            "data": profile_data,
            "filepath": filepath
        }

    def _format_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format pages followed to match requested structure"""
        formatted_pages = []
        for page in pages:
            formatted_pages.append({
                "page_name": page.get("page_name", page.get("name", "")),
                "page_url": page.get("page_url", page.get("url", "")),
                "bio": page.get("bio", "")
            })
        return formatted_pages

    def _format_following(self, following: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format following list to match requested structure"""
        formatted_following = []
        for follow in following:
            formatted_following.append({
                "name": follow.get("name", ""),
                "profile_url": follow.get("profile_url", follow.get("url", "")),
                "bio": follow.get("bio", "")
            })
        return formatted_following

    def _format_friends(self, friends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format friends list to match requested structure"""
        formatted_friends = []
        for friend in friends:
            formatted_friends.append({
                "name": friend.get("name", ""),
                "profile_url": friend.get("profile_url", friend.get("url", "")),
                "bio": friend.get("bio", "")
            })
        return formatted_friends

    def _format_groups(self, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format groups to match requested structure"""
        formatted_groups = []
        for group in groups:
            formatted_groups.append({
                "group_name": group.get("group_name", group.get("name", "")),
                "group_url": group.get("group_url", group.get("url", "")),
                "bio": group.get("bio", "")
            })
        return formatted_groups

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
                "tagged_accounts": post.get("tagged_accounts", []),
                "location_tagged": post.get("location_tagged", ""),
                "comments": self._format_comments(post.get("comments", []))
            }
            formatted_posts.append(formatted_post)
        return formatted_posts

    def _format_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format comments to match requested structure"""
        formatted_comments = []
        for comment in comments:
            formatted_comment = {
                "commenter": {
                    "name": comment.get("author", comment.get("name", "")),
                    "profile_url": comment.get("profile_url", ""),
                    "bio": comment.get("bio", "")
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
            formatted_comment = {
                "post_url": comment.get("post_url", ""),
                "post_author": {
                    "name": comment.get("post_author", {}).get("name", ""),
                    "profile_url": comment.get("post_author", {}).get("profile_url", ""),
                    "bio": comment.get("post_author", {}).get("bio", "")
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
        """Convert absolute file paths to relative web URLs"""
        if not filepath:
            return ""
            
        # Convert paths like "../static/screenshots/file.png" to "/static/screenshots/file.png"
        if filepath.startswith("../static"):
            return filepath.replace("../static", "/static")
        
        # Handle absolute paths
        path = Path(filepath)
        if "static" in path.parts:
            static_index = path.parts.index("static")
            return "/" + "/".join(path.parts[static_index:])
            
        return filepath