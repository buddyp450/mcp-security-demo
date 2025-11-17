from __future__ import annotations

from typing import Dict, Optional

from ..models import EventLevel, TestOutcome, TestResult
from ..registry import RegistryService
from ..servers.base import ServerBase
from .base import ClientBase, TestContext, extract_breach_indicators, summarize_indicators


class ClientRegistryGuard(ClientBase):
    """A midpoint client that trusts nothing without a registry receipt but still
    lacks runtime defenses. Useful for demonstrating governance gaps."""

    name = "Client v2.5 (Registry Guard)"
    version = "0.8"
    description = "Enforces registry allowlist, tracks manifest drift, but has no runtime interception."

    def __init__(self, registry: RegistryService) -> None:
        self.registry = registry
        self._manifest_cache: Dict[str, Dict] = {}

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:
        server_id = f"{server.name}:{server.version}"
        await self._log(
            context,
            EventLevel.INFO,
            "registry_snapshot",
            "Consulting registry before execution",
            {"registry": self.registry.describe()},
        )

        if not self.registry.is_allowed(server.name, server.version):
            await self._log(
                context,
                EventLevel.CRITICAL,
                "registry_block",
                f"Registry refused {server_id}",
            )
            return TestResult(
                test_case=context.test_case,
                client=self.name,
                server=server_id,
                outcome=TestOutcome.BLOCKED,
                summary="Registry prevented untrusted version",
            )

        manifest = server.manifest()
        await self._log(
            context,
            EventLevel.INFO,
            "manifest_record",
            "Manifest captured for drift detection",
            manifest,
        )

        cached = self._manifest_cache.get(server.name)
        if cached and cached != manifest:
            await self._log(
                context,
                EventLevel.WARNING,
                "manifest_drift",
                "Manifest changed since last approval",
                {"before": cached, "after": manifest},
            )
        elif not cached:
            await self._log(
                context,
                EventLevel.INFO,
                "manifest_baseline",
                "Stored manifest baseline for future comparison",
            )
        self._manifest_cache[server.name] = manifest

        response = await server.run("analyze_subscriptions")
        indicators = extract_breach_indicators(response)
        declared_side_effects = set(manifest.get("side_effects", []))
        actual_side_effects = {sc.get("name") for sc in response.syscalls}

        undeclared = sorted(actual_side_effects - declared_side_effects)
        if undeclared:
            await self._log(
                context,
                EventLevel.CRITICAL,
                "undeclared_side_effects",
                "Runtime observed side effects missing from manifest.",
                {"undeclared": undeclared},
            )

        await self._log(
            context,
            EventLevel.INFO,
            "tool_response_recorded",
            "Captured response for operators (no enforcement).",
            {"payload": response.payload},
        )

        breach_signals = bool(undeclared or indicators)
        if breach_signals:
            await self._log(
                context,
                EventLevel.CRITICAL,
                "runtime_gap",
                "Allowed version executed but violated runtime expectations.",
                {**({"undeclared_side_effects": undeclared} if undeclared else {}), **indicators},
            )
            outcome = TestOutcome.BREACHED
            summary = f"Registry gate only; {summarize_indicators(indicators) if indicators else 'undeclared side effects'} slipped through."
        else:
            outcome = TestOutcome.PASSED
            summary = "Registry-approved execution remained clean"

        return TestResult(
            test_case=context.test_case,
            client=self.name,
            server=server_id,
            outcome=outcome,
            summary=summary,
        )

