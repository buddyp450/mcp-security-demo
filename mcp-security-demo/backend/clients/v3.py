from __future__ import annotations

from typing import List

from ..models import EventLevel, TestOutcome, TestResult
from ..monitoring.latency import LatencyAnalyzer
from ..monitoring.network import NetworkInterceptor
from ..monitoring.sanitizer import OutputSanitizer
from ..monitoring.syscall import SyscallMonitor
from ..registry import RegistryService
from ..servers.base import ServerBase
from .base import ClientBase, TestContext, extract_breach_indicators


class ClientV3(ClientBase):
    name = "Client v3 (Runtime Defense)"
    version = "1.0"
    description = "Implements registry validation, syscall/network monitoring, latency anomaly detection, and remediation."

    def __init__(self, registry: RegistryService) -> None:
        self.registry = registry
        self.syscalls = SyscallMonitor()
        self.network = NetworkInterceptor()
        self.latency = LatencyAnalyzer()
        self.sanitizer = OutputSanitizer()

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:
        server_id = f"{server.name}:{server.version}"
        await self._log(context, EventLevel.INFO, "registry_check", f"Looking up {server_id}")
        if not self.registry.is_allowed(server.name, server.version):
            await self._log(
                context,
                EventLevel.CRITICAL,
                "registry_block",
                f"Registry denies {server_id}",
            )
            return TestResult(
                test_case=context.test_case,
                client=self.name,
                server=server_id,
                outcome=TestOutcome.BLOCKED,
                summary="Registry blocked execution",
            )

        manifest = server.manifest()
        await self._log(
            context,
            EventLevel.INFO,
            "manifest_capture",
            "Manifest captured for baseline",
            manifest,
        )

        response = await server.run("analyze_subscriptions")
        violation_reasons: List[str] = []
        covert_subset = {
            k: v
            for k, v in extract_breach_indicators(response).items()
            if k in {"covert_data_preview", "covert_fields", "server_notes", "variant_notes"}
        }
        if covert_subset:
            violation_reasons.append("covert-channel")
            await self._log(
                context,
                EventLevel.CRITICAL,
                "covert_channel_alert",
                "Detected covert payload markers; sanitizing + banning.",
                covert_subset,
            )

        syscall_alerts, _ = self.syscalls.inspect(response.syscalls)
        for alert in syscall_alerts:
            violation_reasons.append(alert.rule)
            await self._log(
                context,
                EventLevel.CRITICAL,
                "syscall_alert",
                f"Unauthorized syscall: {alert.syscall}",
                alert.detail,
            )

        net_alerts, _ = self.network.inspect(response.network_events)
        for alert in net_alerts:
            violation_reasons.append(alert.rule)
            await self._log(
                context,
                EventLevel.CRITICAL,
                "network_alert",
                "Unauthorized network connection",
                alert.event,
            )

        latency_flag, latency_meta = self.latency.inspect(response.latency_ms)
        if latency_flag:
            violation_reasons.append("latency-anomaly")
            await self._log(
                context,
                EventLevel.WARNING,
                "latency_alert",
                "Latency anomaly detected",
                latency_meta,
            )

        sanitized_payload = self.sanitizer.sanitize(response.payload)
        await self._log(
            context,
            EventLevel.INFO,
            "output_sanitized",
            "Sanitized payload emitted to host",
            sanitized_payload,
        )

        if violation_reasons:
            reason = ", ".join(sorted(set(violation_reasons)))
            await self._log(
                context,
                EventLevel.ALERT,
                "policy_reject",
                f"Policy REJECT: {server_id}",
                {"reason": reason, "note": "would ban, but demo keeps registry clean"},
            )
            outcome = TestOutcome.BLOCKED
            summary = f"Runtime policy violation ({reason})"
        else:
            await self._log(
                context,
                EventLevel.INFO,
                "policy_allow",
                f"Policy ALLOW: {server_id}",
            )
            outcome = TestOutcome.PASSED
            summary = "Runtime monitoring cleared execution"

        return TestResult(
            test_case=context.test_case,
            client=self.name,
            server=server_id,
            outcome=outcome,
            summary=summary,
        )
