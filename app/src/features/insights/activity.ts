import type { AgentActivityData, ProfileMessage } from '../../types/chat.ts'
import { toolFeatures, type FeatureId } from './catalog.ts'

export function messageActivities(message: ProfileMessage): AgentActivityData[] {
  const activities = new Map<string, AgentActivityData>()
  for (const part of message.parts) {
    if (part.type === 'data-agent-activity') activities.set(part.data.id, part.data)
  }
  return [...activities.values()]
}

export function activityStatus(activity: AgentActivityData, active: boolean): AgentActivityData['status'] {
  // Stopping/losing a stream must never leave a historical row spinning forever.
  return activity.status === 'running' && !active ? 'interrupted' : activity.status
}

export function messageFeatures(message: ProfileMessage): FeatureId[] {
  const used = new Set<FeatureId>()
  for (const activity of messageActivities(message)) {
    if (activity.kind !== 'tool' || !activity.tool_name) continue
    const feature = toolFeatures[activity.tool_name]
    if (!feature) continue
    used.add('tools')
    if (activity.status === 'completed') used.add(feature)
  }
  for (const part of message.parts) {
    if (part.type === 'data-feature-used' && part.data.feature === 'streaming') used.add('streaming')
    if (part.type === 'data-source') used.add('sources')
    if (part.type === 'data-user-document') used.add('uploads')
    if (part.type === 'data-candidate-photo') used.add('photo')
  }
  return [...used]
}

/** Rebuild from history: retry/removal cannot leave stale, globally "seen" flags. */
export function firstFeatureMessages(messages: readonly ProfileMessage[]): Map<FeatureId, string> {
  const first = new Map<FeatureId, string>()
  for (const message of messages) {
    for (const feature of messageFeatures(message)) {
      if (!first.has(feature)) first.set(feature, message.id)
    }
  }
  return first
}
