from __future__ import annotations

from ..models import EventLevel, TestOutcome, TestResult
from ..servers.base import ServerBase
from .base import ClientBase, TestContext, extract_breach_indicators, summarize_indicators


class ClientV2(ClientBase):
    name = "Client v2 (Manifest-Aware)"
    version = "0.5"
    description = "Reads manifests but does not enforce policy."

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:
        await self._log(context, EventLevel.INFO, "start", f"Fetching manifest from {server.name}:{server.version}")
        manifest = server.manifest()
        await self._log(
            context,
            EventLevel.INFO,
            "manifest_analysis",
            "Manifest inspected for visibility",
            manifest,
        )
        response = await server.run("analyze_subscriptions")
        indicators = extract_breach_indicators(response)
        await self._log(
            context,
            EventLevel.WARNING if manifest.get("side_effects") == [] else EventLevel.INFO,
            "manifest_gap",
            "Manifest declared no side effects" if manifest.get("side_effects") == [] else "Side effects declared",
            {"side_effects": manifest.get("side_effects", [])},
        )
        if manifest.get("version") and manifest.get("version") != server.version:
            await self._log(
                context,
                EventLevel.ALERT,
                "manifest_version_spoof",
                "Server manifest version deviates from runtime version.",
                {"manifest_version": manifest.get("version"), "runtime_version": server.version},
            )
        await self._log(
            context,
            EventLevel.INFO,
            "tool_response",
            "Accepted response; compliance theater only",
            {"payload": response.payload},
        )
        if indicators:
            await self._log(
                context,
                EventLevel.CRITICAL,
                "breach_visible_only",
                "Detected suspicious indicators but client cannot block.",
                indicators,
            )
            outcome = TestOutcome.BREACHED
            summary = f"Visibility-only controls; {summarize_indicators(indicators)} persisted."
        else:
            outcome = TestOutcome.PASSED
            summary = "Manifest visibility only"
        return TestResult(
            test_case=context.test_case,
            client=self.name,
            server=f"{server.name}:{server.version}",
            outcome=outcome,
            summary=summary,
        )
