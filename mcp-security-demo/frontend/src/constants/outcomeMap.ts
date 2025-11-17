import type { Status } from '../types/testCases'

const map = {
  passed: 'passed',
  blocked: 'blocked',
  breached: 'breached'
} as const

export type OutcomeKey = keyof typeof map

export function statusFromOutcome(value: unknown): Status | undefined {
  if (typeof value !== 'string') {
    return undefined
  }
  const key = value as OutcomeKey
  return map[key] as Status | undefined
}

