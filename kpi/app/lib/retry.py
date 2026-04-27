"""Exponential-backoff retry helper for YouTube API + git subprocess calls.

Semantics mirror `scripts/lib/with-retry.sh` but in Python: transient errors
retry up to N attempts with 2^n-second backoff; non-retriable errors raise
immediately. Auth errors (401/403/invalid_grant) are NEVER retried — a retry
cannot fix a bad credential.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

_LOG = logging.getLogger(__name__)

T = TypeVar("T")


class NonRetriable(Exception):
    """Raise inside `fn` to short-circuit retry loop unconditionally."""


def is_transient_http_status(status: int) -> bool:
    """5xx + 429 are transient; 4xx except 408/429 are not."""
    if status in (408, 429):
        return True
    if 500 <= status < 600:
        return True
    return False


def retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.2,
    retriable: Callable[[BaseException], bool] | None = None,
) -> T:
    """Call `fn` up to max_attempts, backing off exponentially on retriable errors.

    Args:
        fn: zero-arg callable. Return value is returned on success.
        max_attempts: total attempts including the first.
        base_delay: initial sleep (seconds). Doubles on each retry.
        max_delay: cap on sleep between attempts.
        jitter: fraction of delay added as uniform random [0, jitter*delay].
        retriable: predicate on exception. Default: only retry NonRetriable's
            inverse (raise NonRetriable to bail). If provided, overrides default.

    Raises:
        The last exception if all attempts exhaust.
        NonRetriable.__cause__ immediately if a NonRetriable is raised.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except NonRetriable as nr:
            # Short-circuit: re-raise the underlying cause if present.
            if nr.__cause__ is not None:
                raise nr.__cause__ from nr
            raise
        except BaseException as exc:  # noqa: BLE001 — generic retry guard
            last_exc = exc
            if retriable is not None and not retriable(exc):
                raise
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay += random.uniform(0, jitter * delay)
            _LOG.warning(
                "retry attempt %d/%d failed (%s); sleeping %.2fs",
                attempt,
                max_attempts,
                exc.__class__.__name__,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None  # unreachable — loop always has a last exception
    raise last_exc
