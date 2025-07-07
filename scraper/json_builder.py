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
        # Format all data into a clean JSON structure
        profile_data = {
            "metadata": {
                "username": username,
                "scraped_at": int(time.time()),
                "scraper_version": "1.0.0"
            },
            "profile": {
                "basic_info": {
                    "name": data.get("basic_info", {}).get("name", ""),
                    "bio": data.get("basic_info", {}).get("bio", ""),
                    "profile_picture": self._convert_to_relative_path(data.get("basic_info", {}).get("profile_picture", "")),
                    "work": data.get("basic_info", {}).get("work", []),
                    "education": data.get("basic_info", {}).get("education", []),
                    "current_city": data.get("basic_info", {}).get("location", ""),
                    "hometown": data.get("basic_info", {}).get("hometown", ""),
                    "birthday": data.get("basic_info", {}).get("birthday", ""),
                    "email": data.get("basic_info", {}).get("email", ""),
                    "phone": data.get("basic_info", {}).get("phone", ""),
                },
                "connections": {
                    "friends": data.get("friends_list", []),
                    "following": data.get("following_list", []),
                    "groups": data.get("groups", []),
                    "pages_followed": data.get("pages_followed", [])
                },
                "content": {
                    "own_posts": self._process_posts(data.get("own_posts", [])),
                    "tagged_posts": self._process_posts(data.get("tagged_posts", [])),
                    "comments_made": data.get("user_comments", []),
                    "locations": data.get("locations", [])
                }
            }
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