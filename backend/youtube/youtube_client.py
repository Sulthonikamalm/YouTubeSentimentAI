"""
youtube_client.py — Official YouTube Data API v3 client wrapper.
"""

import time
import socket
import logging
from typing import Dict, Any, Optional
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("youtube_collector")

class YouTubeAPIError(Exception):
    """Base exception for all YouTube Data API errors."""
    pass

class QuotaExceededError(YouTubeAPIError):
    pass

class CommentsDisabledError(YouTubeAPIError):
    pass

class VideoNotFoundError(YouTubeAPIError):
    pass

class InvalidApiKeyError(YouTubeAPIError):
    pass

class ForbiddenError(YouTubeAPIError):
    pass

class YouTubeTimeoutError(YouTubeAPIError):
    pass


class YouTubeClient:
    """Wrapper class for YouTube Data API v3 operations."""
    
    def __init__(self, api_key: str, timeout_seconds: int = 20):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.service = self._build_service()
        
    def _build_service(self):
        try:
            http_client = httplib2.Http(timeout=self.timeout_seconds)
            return build("youtube", "v3", developerKey=self.api_key, http=http_client)
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            raise InvalidApiKeyError(f"Initialization failure: {e}")
            
    def normalize_error(self, error: Exception) -> str:
        if isinstance(error, QuotaExceededError):
            return "quotaExceeded"
        elif isinstance(error, CommentsDisabledError):
            return "commentsDisabled"
        elif isinstance(error, VideoNotFoundError):
            return "videoNotFound"
        elif isinstance(error, InvalidApiKeyError):
            return "invalidApiKey"
        elif isinstance(error, ForbiddenError):
            return "forbidden"
        elif isinstance(error, YouTubeTimeoutError):
            return "timeout"
        else:
            if isinstance(error, HttpError):
                content = error.content.decode("utf-8") if hasattr(error, "content") else str(error)
                if "quotaExceeded" in content:
                    return "quotaExceeded"
                elif "commentsDisabled" in content:
                    return "commentsDisabled"
                elif "videoNotFound" in content or error.resp.status == 404:
                    return "videoNotFound"
                elif "keyInvalid" in content or "API key not valid" in content or error.resp.status == 400:
                    return "invalidApiKey"
                elif error.resp.status == 403:
                    return "forbidden"
            return "unknown_error"

    def safe_request(self, endpoint: str, request_fn, max_retries: int = 3) -> Dict[str, Any]:
        retries = 0
        backoff = 2.0
        
        while True:
            try:
                response = request_fn.execute()
                return response
                
            except HttpError as e:
                content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
                status = e.resp.status
                
                if "quotaExceeded" in content:
                    logger.error("YouTube API quota exceeded!")
                    raise QuotaExceededError("Quota exceeded")
                
                if "commentsDisabled" in content:
                    logger.warning("YouTube video comments are disabled.")
                    raise CommentsDisabledError("Comments disabled")
                
                if "videoNotFound" in content or status == 404:
                    logger.warning("YouTube video not found.")
                    raise VideoNotFoundError("Video not found")
                    
                if "keyInvalid" in content or "API key not valid" in content or status == 400:
                    logger.error("YouTube API key is invalid.")
                    raise InvalidApiKeyError("Invalid API key")
                
                if status == 403:
                    logger.error(f"Access Forbidden: {content}")
                    raise ForbiddenError("Forbidden access")
                
                if status >= 500:
                    if retries < max_retries:
                        retries += 1
                        logger.warning(f"YouTube API server error {status}. Retrying {retries}/{max_retries}...")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    
                raise YouTubeAPIError(f"HTTP Error {status}: {content}")
                
            except (socket.timeout, YouTubeTimeoutError):
                if retries < max_retries:
                    retries += 1
                    logger.warning(f"Network timeout. Retrying {retries}/{max_retries}...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise YouTubeTimeoutError("Network request timed out")
                
            except Exception as e:
                if retries < max_retries and "timeout" in str(e).lower():
                    retries += 1
                    logger.warning(f"Connection issue: {e}. Retrying {retries}/{max_retries}...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise YouTubeAPIError(f"Unexpected request error: {e}")

    def fetch_video_metadata(self, video_id: str) -> Dict[str, Any]:
        request = self.service.videos().list(part="snippet", id=video_id)
        response = self.safe_request("videos.list", request)
        
        items = response.get("items", [])
        if not items:
            raise VideoNotFoundError(f"Video {video_id} metadata empty.")
            
        snippet = items[0]["snippet"]
        return {
            "video_title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
        }

    def fetch_comment_threads(
        self, video_id: str, page_token: Optional[str] = None, max_results: int = 100,
        order: str = "time", text_format: str = "plainText"
    ) -> Dict[str, Any]:
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": max_results,
            "textFormat": text_format,
            "order": order,
        }
        if page_token:
            params["pageToken"] = page_token
            
        request = self.service.commentThreads().list(**params)
        return self.safe_request("commentThreads.list", request)

    def fetch_replies(
        self, parent_id: str, page_token: Optional[str] = None, max_results: int = 100,
        text_format: str = "plainText"
    ) -> Dict[str, Any]:
        params = {
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": max_results,
            "textFormat": text_format,
        }
        if page_token:
            params["pageToken"] = page_token
            
        request = self.service.comments().list(**params)
        return self.safe_request("comments.list", request)
