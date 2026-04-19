"""
Enhanced WebSearch tool for searching the web and accessing current information.

Provides web search capabilities with source tracking and formatted results.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class WebSearchTool(ACPTool):
    """Enhanced WebSearch tool for accessing current information."""

    def __init__(self):
        """Initialize WebSearch tool."""
        spec = ACPToolSpec(
            name="WebSearch",
            description="Searches the web and uses the results to provide up-to-date information",
            version="1.0.0",
            parameters={
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to use",
                        "minLength": 2
                    },
                    "allowed_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Only include search results from these domains"
                    },
                    "blocked_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Never include search results from these domains"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the web search request."""
        payload = message.payload

        if not payload.get("query"):
            return "query is required"

        query = payload["query"].strip()
        if len(query) < 2:
            return "query must be at least 2 characters long"

        # Validate domains if provided
        allowed_domains = payload.get("allowed_domains", [])
        blocked_domains = payload.get("blocked_domains", [])

        if not isinstance(allowed_domains, list):
            return "allowed_domains must be a list"

        if not isinstance(blocked_domains, list):
            return "blocked_domains must be a list"

        # Basic domain validation
        all_domains = allowed_domains + blocked_domains
        for domain in all_domains:
            if not isinstance(domain, str) or not domain.strip():
                return "domain entries must be non-empty strings"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the web search."""
        payload = message.payload
        query = payload["query"]
        allowed_domains = payload.get("allowed_domains", [])
        blocked_domains = payload.get("blocked_domains", [])

        try:
            # For now, return a mock response since we don't have actual web search API
            # In a real implementation, this would use a search API like Google, Bing, or DuckDuckGo

            mock_results = await self._mock_web_search(query, allowed_domains, blocked_domains)

            # Format the results
            if mock_results:
                result_text = f"Search results for: {query}\n\n"
                for i, result in enumerate(mock_results, 1):
                    result_text += f"{i}. **{result['title']}**\n"
                    result_text += f"   {result['url']}\n"
                    result_text += f"   {result['snippet']}\n\n"

                # Add sources section
                result_text += "Sources:\n"
                for result in mock_results:
                    result_text += f"- [{result['title']}]({result['url']})\n"

            else:
                result_text = f"No search results found for: {query}"

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "query": query,
                    "results_count": len(mock_results),
                    "allowed_domains": allowed_domains,
                    "blocked_domains": blocked_domains,
                    "note": "Mock implementation - requires actual search API integration"
                }
            )

        except Exception as e:
            logger.exception(f"Error in web search for query: {query}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error performing web search: {str(e)}"
            )

    async def _mock_web_search(
        self,
        query: str,
        allowed_domains: List[str],
        blocked_domains: List[str]
    ) -> List[Dict[str, str]]:
        """Mock web search implementation."""

        # Simulate search results based on query
        mock_data = [
            {
                "title": f"Documentation for {query}",
                "url": f"https://docs.example.com/{query.lower().replace(' ', '-')}",
                "snippet": f"Official documentation and guides for {query}. Learn how to use and implement {query} in your projects."
            },
            {
                "title": f"{query} Tutorial and Examples",
                "url": f"https://tutorial.example.com/{query.lower().replace(' ', '-')}",
                "snippet": f"Step-by-step tutorial and practical examples for {query}. Includes code samples and best practices."
            },
            {
                "title": f"GitHub - {query} Repository",
                "url": f"https://github.com/example/{query.lower().replace(' ', '-')}",
                "snippet": f"Open source implementation and examples for {query}. Community contributions and active development."
            }
        ]

        # Apply domain filtering
        filtered_results = []
        for result in mock_data:
            domain = self._extract_domain(result["url"])

            # Skip if in blocked domains
            if any(blocked in domain for blocked in blocked_domains):
                continue

            # If allowed_domains specified, only include those
            if allowed_domains and not any(allowed in domain for allowed in allowed_domains):
                continue

            filtered_results.append(result)

        return filtered_results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        query = message.payload.get("query", "")
        self.logger.debug(f"Searching web for: {query}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            results_count = result.metadata.get("results_count", 0)
            self.logger.debug(f"Found {results_count} web search results")


# Create singleton instance
websearch_tool = WebSearchTool()