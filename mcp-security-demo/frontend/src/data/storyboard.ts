import type { ClientId, ServerVariantId } from '../types/testCases'

export interface ScenarioLookingGlass {
  id: string
  label: string
  summary: string
  file: string
  baseline: ClientId
  variant: ClientId
}

export interface StageServerVariant {
  id: ServerVariantId
  label: string
  description: string
  articleRef?: string
}

export interface StageScenario {
  id: string
  clientId: ClientId
  label: string
  description: string
  lookingGlass?: ScenarioLookingGlass
}

export interface StoryboardStage {
  id: string
  title: string
  blurb: string
  examples: string[]
  articles: string[]
  serverVariants: StageServerVariant[]
  scenarios: StageScenario[]
  lookingGlassRefs: ScenarioLookingGlass[]
}

export const STORYBOARD_STAGES: StoryboardStage[] = [
  {
    id: 'registry-reality',
    title: 'Registry Reality Check',
    blurb:
      'FactSet frames MCP governance as binary: either you can prove what just ran or you are improvising. This stage contrasts the stealthy Version Shift patch with the still-approved Covert Slice so you can narrate manifest-only collapse versus registry + runtime mitigation.',
    examples: [
      '📦 Run Client v2 against Version Shift 2.0.1 to watch a manifest-only host miss the spoof.',
      '🛂 Swap to Client v2.5 with the same variant to show the registry block and manifest diff evidence.',
      '🕳️ Keep Client v2.5 selected but flip to Covert Slice 2.0.0—allowed versions can still leak until runtime policy (Client v3) engages.'
    ],
    articles: ['factset'],
    serverVariants: [
      {
        id: 'version-shift',
        label: 'Version Shift 2.0.1',
        description: 'Updates without disclosure—watch governance fail fast.',
        articleRef: 'factset'
      },
      {
        id: 'covert-slice',
        label: 'Covert Slice 2.0.0',
        description: 'Still “allowed” in the registry, still exfiltrating.',
        articleRef: 'factset'
      }
    ],
    scenarios: [
      {
        id: 'registry-v2',
        clientId: 'client_v2',
        label: 'Client v2 — manifest only',
        description: 'Feels safe, still leaks—pair with Version Shift.',
        lookingGlass: {
          id: 'lg-v2-v25',
          label: 'Manifest aware vs registry guard',
          summary: 'Diff the exact call path where registry enforcement appears.',
          file: 'backend/clients/registry_guard.py',
          baseline: 'client_v2',
          variant: 'client_v25'
        }
      },
      {
        id: 'registry-v25',
        clientId: 'client_v25',
        label: 'Client v2.5 — registry guard',
        description: 'Enforces allowlist but remains runtime blind.'
      },
      {
        id: 'registry-v3',
        clientId: 'client_v3',
        label: 'Client v3 — runtime defense',
        description: 'Stacks registry + runtime policy to stop drift.'
      }
    ],
    lookingGlassRefs: [
      {
        id: 'lg-v2-v25',
        label: 'Where registry enforcement appears',
        summary: 'Shows the added registry block + manifest diff logic.',
        file: 'backend/clients/registry_guard.py',
        baseline: 'client_v2',
        variant: 'client_v25'
      }
    ]
  },
  {
    id: 'trust-failures',
    title: 'Trust Failures Materialized',
    blurb:
      'CyberArk warns that MCP servers will hoard data, smuggle payloads, and mutate prompts. This stage lets you pin those behaviors and compare tails between naive and defended hosts.',
    examples: [
      '🧵 Run Client v1 against Prompt Chainer to watch the prompt instructions land verbatim in the tail.',
      '🕳️ Pair Client v2 with Covert Slice to prove “visibility only” still leaks CSVs and syscalls.',
      '🛡️ Graduate to Client v3 and rerun both variants—the runtime policy severs the session and sanitizes payloads.'
    ],
    articles: ['cyberark'],
    serverVariants: [
      {
        id: 'covert-slice',
        label: 'Covert Slice 2.0.0',
        description: 'Classic covert channel from the CyberArk post.',
        articleRef: 'cyberark'
      },
      {
        id: 'prompt-chainer',
        label: 'Prompt Chainer 2.1.0',
        description: 'Focuses on prompt-level exfiltration.',
        articleRef: 'cyberark'
      }
    ],
    scenarios: [
      {
        id: 'trust-v1',
        clientId: 'client_v1',
        label: 'Client v1 — nothing enforced',
        description: 'Baseline breach. Watch the pinned tail fill with lies.'
      },
      {
        id: 'trust-v2',
        clientId: 'client_v2',
        label: 'Client v2 — transparency only',
        description: 'You see the lie but still leak everything.'
      },
      {
        id: 'trust-v3',
        clientId: 'client_v3',
        label: 'Client v3 — runtime defense',
        description: 'Blocks covert channels, bans the server.',
        lookingGlass: {
          id: 'lg-v1-v3',
          label: 'From naive to runtime defense',
          summary: 'Diff the run loop so attendees see the exact policy hooks.',
          file: 'backend/clients/v3.py',
          baseline: 'client_v1',
          variant: 'client_v3'
        }
      }
    ],
    lookingGlassRefs: [
      {
        id: 'lg-v1-v3',
        label: 'Naive vs runtime defense',
        summary: 'Highlights syscall/network monitors that stop covert exfiltration.',
        file: 'backend/clients/v3.py',
        baseline: 'client_v1',
        variant: 'client_v3'
      }
    ]
  },
  {
    id: 'platform-guardrails',
    title: 'Platform Guardrails',
    blurb:
      'Microsoft’s Windows post describes host-level sandboxing and remediation. Here you pit Client v3 against the new Host Sentinel (v4) to see how platform controls feel.',
    examples: [
      '🛡️ Launch Client v3 vs Side-Effect Cascade to see monitors light up; then switch to Host Sentinel to watch the sandbox auto-ban it.',
      '🗃️ Compare declared side effects with actual syscalls to narrate Microsoft’s “trust but sandbox” guidance.',
      '🚨 Trigger Prompt Chainer under Host Sentinel to show remediation hooks updating the registry instantly.'
    ],
    articles: ['windows'],
    serverVariants: [
      {
        id: 'side-effect-cascade',
        label: 'Side-Effect Cascade 2.2.0',
        description: 'Filesystem + network abuse that pressures sandboxing.',
        articleRef: 'windows'
      },
      {
        id: 'prompt-chainer',
        label: 'Prompt Chainer 2.1.0',
        description: 'Great for showing host sentinel output scanning.',
        articleRef: 'windows'
      }
    ],
    scenarios: [
      {
        id: 'platform-v3',
        clientId: 'client_v3',
        label: 'Client v3 — runtime defense',
        description: 'Registry + monitors without sandbox context.'
      },
      {
        id: 'platform-v4',
        clientId: 'client_v4',
        label: 'Client v4 — host sentinel',
        description: 'Adds sandbox delta + auto remediation.',
        lookingGlass: {
          id: 'lg-v3-v4',
          label: 'Runtime defense vs host sentinel',
          summary: 'See exactly where sandbox checks hook in.',
          file: 'backend/clients/v4.py',
          baseline: 'client_v3',
          variant: 'client_v4'
        }
      }
    ],
    lookingGlassRefs: [
      {
        id: 'lg-v3-v4',
        label: 'Host sentinel diff',
        summary: 'Highlights sandbox, network, and remediation upgrades inspired by Windows guidance.',
        file: 'backend/clients/v4.py',
        baseline: 'client_v3',
        variant: 'client_v4'
      }
    ]
  },
  {
    id: 'diagnostic-playground',
    title: 'Diagnostic Playground',
    blurb:
      'Mix-and-match clients and servers. Pin tails, compare code, and keep a scratchpad of “what broke when we removed X?”.',
    examples: [
      '🎲 Randomize the server variant.',
      '🧪 Pin multiple tails side-by-side and flip between them.',
    ],
    articles: ['factset', 'cyberark', 'windows'],
    serverVariants: [
      { id: 'covert-slice', label: 'Covert Slice 2.0.0', description: 'Latency covert channel' },
      { id: 'version-shift', label: 'Version Shift 2.0.1', description: 'Manifest misdirection' },
      { id: 'side-effect-cascade', label: 'Side-Effect Cascade 2.2.0', description: 'Sandbox breaker' }
    ],
    scenarios: [
      {
        id: 'playground-v1',
        clientId: 'client_v1',
        label: 'Client v1',
        description: 'Use as a reminder of what happens without guardrails.'
      },
      {
        id: 'playground-v25',
        clientId: 'client_v25',
        label: 'Client v2.5',
        description: 'Lightweight registry guard for experiments.'
      },
      {
        id: 'playground-v3',
        clientId: 'client_v3',
        label: 'Client v3',
        description: 'Full runtime defense baseline.'
      },
      {
        id: 'playground-v4',
        clientId: 'client_v4',
        label: 'Client v4',
        description: 'Platform-grade sandbox.'
      }
    ],
    lookingGlassRefs: [
      {
        id: 'lg-playground-xray',
        label: 'Client v1 vs Host Sentinel',
        summary: 'Jump from the naive client to the host sentinel to highlight how the sandbox code branches.',
        file: 'backend/clients/v4.py',
        baseline: 'client_v1',
        variant: 'client_v4'
      }
    ]
  }
]

