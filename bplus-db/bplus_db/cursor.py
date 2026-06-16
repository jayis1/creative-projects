"""Cursor-based iteration for the B+ Tree Database.

Cursors allow efficient pagination through large result sets without loading
all results into memory at once.  They are especially useful for range queries
and prefix scans where the total number of matches is unknown.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .database import Database


class Cursor:
    """A stateful cursor for paginating through database entries.

    Args:
        db: The database to iterate over.
        start_key: Inclusive lower bound (``None`` = no lower bound).
        end_key: Inclusive upper bound (``None`` = no upper bound).
        page_size: Number of entries to fetch per internal page.

    Usage::

        cursor = db.cursor(page_size=100)
        for key, value in cursor:
            print(key, value)

        # Or explicit pages:
        cursor = db.cursor(start_key="user:", page_size=50)
        while page := cursor.fetch_page():
            for key, value in page:
                process(key, value)
    """

    def __init__(
        self,
        db: Database,
        start_key: str | None = None,
        end_key: str | None = None,
        prefix: str | None = None,
        page_size: int = 100,
    ):
        self._db = db
        self._start_key = start_key
        self._end_key = end_key
        self._prefix = prefix
        self._page_size = max(1, page_size)
        self._exhausted = False
        self._last_key: str | None = None
        self._total_yielded = 0

    # ── iteration protocol ─────────────────────────────────────────

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        """Yield ``(key, value)`` pairs one at a time, lazily fetching pages."""
        while not self._exhausted:
            page = self._fetch_next_page()
            for key, value in page:
                yield key, value

    def __next__(self) -> Tuple[str, Any]:
        """Step one entry at a time."""
        if not hasattr(self, "_buffer"):
            self._buffer = iter(self)
        try:
            return next(self._buffer)
        except StopIteration:
            raise StopIteration

    # ── pagination API ─────────────────────────────────────────────

    def fetch_page(self) -> List[Tuple[str, Any]]:
        """Fetch the next page of results (up to *page_size* entries).

        Returns an empty list when the cursor is exhausted.
        """
        return self._fetch_next_page()

    def _fetch_next_page(self) -> List[Tuple[str, Any]]:
        """Internal: pull one page from the database."""
        if self._exhausted:
            return []

        # Determine the effective start for this page
        effective_start = self._start_key
        if self._last_key is not None:
            # Continue from after the last key we returned
            effective_start = self._last_key

        # Use prefix_scan or range_query depending on args
        if self._prefix is not None:
            # Prefix scan — we filter in-page to avoid re-scanning
            results = self._db.prefix_scan(self._prefix)
            # If we have a last_key, skip entries before it
            page = []
            for key, value in results:
                if effective_start is not None and key < effective_start:
                    continue
                if self._last_key is not None and key == self._last_key:
                    continue  # Already returned
                page.append((key, value))
                if len(page) >= self._page_size:
                    break
            # Check if this is the last page
            remaining_after = 0
            found_break = False
            all_results = results  # Already fetched all :(
            for key, value in all_results:
                if page and key == page[-1][0]:
                    found_break = True
                    continue
                if found_break:
                    remaining_after += 1
            if remaining_after == 0 and len(page) <= self._page_size:
                self._exhausted = True
            if page:
                self._last_key = page[-1][0]
                self._total_yielded += len(page)
            return page
        else:
            # Range query with bounds
            results = self._db.range_query(effective_start, self._end_key)
            # If we have a last_key, skip it (it was already yielded)
            page = []
            for key, value in results:
                if self._last_key is not None and key == self._last_key:
                    continue
                page.append((key, value))
                if len(page) >= self._page_size:
                    break
            # If we got fewer than page_size, we're done
            if len(page) < self._page_size:
                self._exhausted = True
            if page:
                self._last_key = page[-1][0]
                self._total_yielded += len(page)
            return page

    @property
    def exhausted(self) -> bool:
        """Whether the cursor has no more results."""
        return self._exhausted

    @property
    def total_yielded(self) -> int:
        """Total entries yielded so far."""
        return self._total_yielded