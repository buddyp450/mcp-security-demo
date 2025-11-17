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


class ClientV4HostSentinel(ClientBase):
    """Platform-grade host that layers sandboxing + remediation on top of v3 defenses."""

    name = "Client v4 (Host Sentinel)"
    version = "1.2"
    description = "Adds sandbox policy, syscall shadow-copying, and auto-remediation to the runtime defense stack."

    def __init__(self, registry: RegistryService) -> None:
        self.registry = registry
        self.syscalls = SyscallMonitor()
        self.network = NetworkInterceptor()
        self.latency = LatencyAnalyzer()
        self.sanitizer = OutputSanitizer()
        self.allowed_side_effects = {"read_only_db", "telemetry_emit"}

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:
        server_id = f"{server.name}:{server.version}"
        await self._log(
            context,
            EventLevel.INFO,
            "host_guard",
            "Host sentinel verifying registry + sandbox policies",
            {"server": server_id},
        )

        if not self.registry.is_allowed(server.name, server.version):
            await self._log(
                context,
                EventLevel.CRITICAL,
                "host_registry_reject",
                f"Host refused execution for {server_id}",
            )
            return TestResult(
                test_case=context.test_case,
                client=self.name,
                server=server_id,
                outcome=TestOutcome.BLOCKED,
                summary="Host sentinel registry refusal",
            )

        manifest = server.manifest()
        declared_effects = set(manifest.get("side_effects", []))
        await self._log(
            context,
            EventLevel.INFO,
            "sandbox_policy",
            "Comparing declared side effects with sandbox allowlist",
            {"declared": list(declared_effects), "allowlist": list(self.allowed_side_effects)},
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
                "sandbox_covert_channel",
                "Sandbox trapped covert channel markers.",
                covert_subset,
            )

        syscall_alerts, _ = self.syscalls.inspect(response.syscalls)
        for alert in syscall_alerts:
            violation_reasons.append(alert.rule)
            await self._log(
                context,
                EventLevel.CRITICAL,
                "sandbox_syscall",
                "Sandbox trapped syscall",
                {"rule": alert.rule, "detail": alert.detail},
            )

        undeclared_calls = [sc.get("name") for sc in response.syscalls]
        if undeclared_calls and not declared_effects:
            violation_reasons.append("undeclared-side-effects")
            await self._log(
                context,
                EventLevel.CRITICAL,
                "sandbox_manifest_violation",
                "Runtime detected undeclared side effects",
                {"syscalls": undeclared_calls},
            )

        net_alerts, _ = self.network.inspect(response.network_events)
        for alert in net_alerts:
            violation_reasons.append(alert.rule)
            await self._log(
                context,
                EventLevel.ALERT,
                "sandbox_network",
                "Unauthorized network egress",
                alert.event,
            )

        latency_flag, latency_meta = self.latency.inspect(response.latency_ms)
        if latency_flag:
            violation_reasons.append("latency-anomaly")
            await self._log(
                context,
                EventLevel.WARNING,
                "sandbox_latency",
                "Latency modulation suspicious",
                latency_meta,
            )

        sanitized_payload = self.sanitizer.sanitize(response.payload)
        await self._log(
            context,
            EventLevel.INFO,
            "sandbox_sanitize",
            "Sanitized payload emitted after policy review",
            sanitized_payload,
        )

        if violation_reasons:
            reason = ", ".join(sorted(set(violation_reasons)))
            await self._log(
                context,
                EventLevel.CRITICAL,
                "auto_remediation",
                "Host sentinel would auto-ban, but demo keeps registry pristine",
                {"reason": reason},
            )
            outcome = TestOutcome.BLOCKED
            summary = f"Host sentinel blocked execution ({reason})"
        else:
            outcome = TestOutcome.PASSED
            summary = "Host sentinel allowed runtime (no violations)"
            await self._log(
                context,
                EventLevel.INFO,
                "sandbox_allow",
                "All sandbox checks cleared; payload released",
            )

        return TestResult(
            test_case=context.test_case,
            client=self.name,
            server=server_id,
            outcome=outcome,
            summary=summary,
        )

