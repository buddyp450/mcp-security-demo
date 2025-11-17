from __future__ import annotations

from ..models import EventLevel, TestOutcome, TestResult
from ..servers.base import ServerBase
from .base import ClientBase, TestContext, extract_breach_indicators, summarize_indicators


class ClientV1(ClientBase):
    name = "Client v1 (Naive)"
    version = "0.1"
    description = "Executes tool calls with zero security posture."

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:
        await self._log(context, EventLevel.INFO, "start", f"Invoking {server.name}:{server.version}")
        response = await server.run("analyze_subscriptions")
        indicators = extract_breach_indicators(response)
        await self._log(
            context,
            EventLevel.INFO,
            "manifest_visible",
            "Manifest read for awareness only",
            {"manifest": response.manifest},
        )
        await self._log(
            context,
            EventLevel.INFO,
            "tool_response",
            "Accepted server response without validation",
            {"payload": response.payload},
        )
        if indicators:
            await self._log(
                context,
                EventLevel.CRITICAL,
                "breach_ignored",
                "Server exfiltrated data; client lacked policies.",
                indicators,
            )
            outcome = TestOutcome.BREACHED
            summary = f"No validation; {summarize_indicators(indicators)} observed only after the fact."
        else:
            outcome = TestOutcome.PASSED
            summary = "No indicators detected (unexpected)"
        return TestResult(
            test_case=context.test_case,
            client=self.name,
            server=f"{server.name}:{server.version}",
            outcome=outcome,
            summary=summary,
        )
