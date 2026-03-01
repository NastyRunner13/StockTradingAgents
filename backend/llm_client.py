"""
NexusTrade — Groq LLM Client
Creates ChatGroq instances with rate-limit-resilient wrapper.
"""

import asyncio
import random
import logging
from langchain_groq import ChatGroq
from config import GROQ_API_KEY, DEEP_THINK_MODEL, QUICK_THINK_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES

logger = logging.getLogger("nexustrade.llm")

# Global semaphore to limit concurrent LLM calls (prevents burst 429s)
_llm_semaphore = asyncio.Semaphore(2)


class RateLimitedLLM:
    """Wrapper around ChatGroq that handles rate-limit errors with exponential backoff.
    
    Features:
    - Catches 429 / RateLimitError and retries with exponential backoff + jitter
    - Uses a global semaphore to limit concurrent API calls
    - Logs retry attempts with wait durations
    """

    def __init__(self, llm: ChatGroq, max_retries: int = 5, base_delay: float = 5.0):
        self._llm = llm
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def ainvoke(self, messages, **kwargs):
        """Rate-limit-aware async invoke with exponential backoff."""
        last_error = None

        for attempt in range(self._max_retries + 1):
            async with _llm_semaphore:
                try:
                    return await self._llm.ainvoke(messages, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = (
                        "rate_limit" in error_str
                        or "rate limit" in error_str
                        or "429" in error_str
                        or "too many requests" in error_str
                        or "resource_exhausted" in error_str
                        or "tokens per minute" in error_str
                        or "requests per minute" in error_str
                    )

                    if not is_rate_limit:
                        raise  # Not a rate-limit error, re-raise immediately

                    last_error = e

                    if attempt < self._max_retries:
                        # Exponential backoff: 5s, 10s, 20s, 40s, 80s + random jitter
                        delay = self._base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            f"⏳ Rate limit hit (attempt {attempt + 1}/{self._max_retries}), "
                            f"waiting {delay:.1f}s before retry..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"❌ Rate limit exceeded after {self._max_retries} retries. "
                            f"Last error: {e}"
                        )

        raise last_error

    def invoke(self, messages, **kwargs):
        """Synchronous invoke (falls through to underlying LLM)."""
        return self._llm.invoke(messages, **kwargs)

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying LLM."""
        return getattr(self._llm, name)


def create_deep_thinker() -> RateLimitedLLM:
    """Create the deep-thinking LLM (complex reasoning, debates, final decisions)."""
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=DEEP_THINK_MODEL,
        temperature=LLM_TEMPERATURE,
        max_retries=LLM_MAX_RETRIES,
    )
    return RateLimitedLLM(llm)


def create_quick_thinker() -> RateLimitedLLM:
    """Create the quick-thinking LLM (analysts, data processing)."""
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=QUICK_THINK_MODEL,
        temperature=LLM_TEMPERATURE,
        max_retries=LLM_MAX_RETRIES,
    )
    return RateLimitedLLM(llm)
