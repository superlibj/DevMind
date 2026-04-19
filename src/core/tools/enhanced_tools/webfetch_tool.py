"""
Enhanced WebFetch tool for fetching and analyzing web content.

Provides content fetching from URLs with processing and analysis capabilities.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class WebFetchTool(ACPTool):
    """Enhanced WebFetch tool for content fetching and analysis."""

    def __init__(self):
        """Initialize WebFetch tool."""
        spec = ACPToolSpec(
            name="WebFetch",
            description="Fetches content from a specified URL and processes it using an AI model",
            version="1.0.0",
            parameters={
                "required": ["url", "prompt"],
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "The URL to fetch content from"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to run on the fetched content"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

        # Domains that typically require authentication
        self.auth_domains = {
            'docs.google.com', 'drive.google.com',
            'confluence.atlassian.com', 'jira.atlassian.com',
            'github.com/private', 'gitlab.com/private',
            'slack.com', 'discord.com',
            'notion.so', 'airtable.com'
        }

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the web fetch request."""
        payload = message.payload

        if not payload.get("url"):
            return "url is required"

        if not payload.get("prompt"):
            return "prompt is required"

        url = payload["url"].strip()
        prompt = payload["prompt"].strip()

        if not url:
            return "url cannot be empty"

        if not prompt:
            return "prompt cannot be empty"

        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return "invalid URL format"

            # Check for potentially authenticated domains
            if any(auth_domain in parsed.netloc.lower() for auth_domain in self.auth_domains):
                return (f"URL points to an authenticated service ({parsed.netloc}). "
                       f"WebFetch will likely fail for private/authenticated URLs. "
                       f"Consider using a specialized tool with authenticated access.")

        except Exception:
            return "invalid URL format"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the web fetch operation."""
        payload = message.payload
        url = payload["url"]
        prompt = payload["prompt"]

        try:
            # Attempt to fetch the URL
            content = await self._fetch_url(url)

            if content is None:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Failed to fetch content from URL: {url}. "
                           f"The URL may require authentication or be unavailable."
                )

            # Process content with the prompt (mock implementation)
            processed_result = await self._process_content_with_prompt(content, prompt)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=processed_result,
                metadata={
                    "url": url,
                    "prompt": prompt,
                    "content_length": len(content),
                    "note": "Mock implementation - requires actual web fetching and AI processing"
                }
            )

        except Exception as e:
            logger.exception(f"Error fetching URL: {url}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error fetching content: {str(e)}"
            )

    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch content from URL."""
        try:
            # Mock implementation - would use aiohttp or similar in real version
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        # Handle different content types
                        content_type = response.headers.get('content-type', '').lower()

                        if 'text/html' in content_type:
                            html_content = await response.text()
                            # Convert HTML to markdown (simplified)
                            return self._html_to_markdown(html_content)
                        elif 'text/' in content_type:
                            return await response.text()
                        else:
                            return f"Content type {content_type} not supported for text processing"
                    else:
                        return None

        except ImportError:
            # Fallback if aiohttp not available
            return self._mock_fetch_content(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {str(e)}")
            return None

    def _mock_fetch_content(self, url: str) -> str:
        """Mock content fetching when real HTTP client not available."""
        parsed = urlparse(url)
        domain = parsed.netloc

        return f"""# Content from {domain}

This is a mock implementation of web content fetching.

URL: {url}

## Mock Content

In a real implementation, this tool would:
1. Fetch the actual content from the URL
2. Convert HTML to markdown format
3. Handle redirects and various content types
4. Apply the processing prompt to extract relevant information

The content would then be processed according to your specific prompt requirements.

For testing purposes, this mock content represents what would be fetched from the URL.
"""

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown (simplified implementation)."""
        # This is a very basic implementation
        # A real version would use libraries like html2text or BeautifulSoup

        # Remove script and style tags
        import re
        html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)

        # Basic tag conversion
        html = re.sub(r'<h1.*?>(.*?)</h1>', r'# \1', html)
        html = re.sub(r'<h2.*?>(.*?)</h2>', r'## \1', html)
        html = re.sub(r'<h3.*?>(.*?)</h3>', r'### \1', html)
        html = re.sub(r'<p.*?>', '\n', html)
        html = re.sub(r'</p>', '\n', html)
        html = re.sub(r'<br.*?>', '\n', html)
        html = re.sub(r'<.*?>', '', html)  # Remove all other tags

        # Clean up whitespace
        html = re.sub(r'\n\s*\n', '\n\n', html)
        html = html.strip()

        return html

    async def _process_content_with_prompt(self, content: str, prompt: str) -> str:
        """Process the fetched content with the given prompt."""
        # Mock implementation - would use LLM in real version

        content_preview = content[:500] + "..." if len(content) > 500 else content

        return f"""Based on the prompt: "{prompt}"

Here's the analysis of the fetched content:

## Content Preview:
{content_preview}

## Analysis:
[In a real implementation, this would use an AI model to process the content according to your prompt]

The content appears to be from a web page containing text and structured information. Based on your prompt, here would be the specific information you requested.

Note: This is a mock response. The actual implementation would:
1. Use a small, fast AI model to process the content
2. Apply your specific prompt to extract relevant information
3. Return the model's response about the content
4. Handle large content by summarizing if necessary
"""

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        url = message.payload.get("url", "")
        self.logger.debug(f"Fetching content from: {url}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            content_length = result.metadata.get("content_length", 0)
            self.logger.debug(f"Successfully processed {content_length} characters of content")


# Create singleton instance
webfetch_tool = WebFetchTool()