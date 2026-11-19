"""
Bench Bookkeeping Connector - unavailable.

Bench Accounting shut down on 27 December 2024 and never offered a public API
(the old `api.bench.co/v2` base this connector called did not exist publicly).
The connector stays registered so saved connections still load and show a
clear reason instead of a generic authentication failure, but it can no longer
connect or sync. The integrations page no longer offers Bench as connectable.
"""

import logging
from datetime import datetime
from typing import List, Optional

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    LedgerEntry,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BENCH_SHUT_DOWN = (
    "Bench has shut down (December 2024) and has no public API, so it can't be "
    "connected. Export your books from Bench and upload them, or connect your "
    "new accounting system instead."
)


@ConnectorRegistry.register
class BenchConnector(BaseConnector):
    PROVIDER_ID = "bench"
    PROVIDER_NAME = "Bench"
    PROVIDER_DESCRIPTION = "Bench shut down in December 2024 and has no public API. Not available."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = ""

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.auth_error: Optional[str] = BENCH_SHUT_DOWN

    async def authenticate(self) -> bool:
        self.auth_error = BENCH_SHUT_DOWN
        logger.info("Bench connector used after Bench shut down; refusing to connect")
        return False

    async def test_connection(self) -> bool:
        return False

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        return []

    async def sync_all(self) -> SyncResult:
        now = datetime.utcnow()
        return SyncResult(
            success=False,
            provider_id=self.PROVIDER_ID,
            sync_type="full",
            errors=[BENCH_SHUT_DOWN],
            sync_started=now,
            sync_completed=now,
        )

    async def close(self):
        return None
