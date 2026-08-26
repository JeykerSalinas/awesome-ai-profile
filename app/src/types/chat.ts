import type { UIMessage } from 'ai'

export interface CandidatePhotoData {
  src: string
  alt: string
}

export interface TechnologyData {
  label: string
  items: string[]
}

export interface ProjectData {
  title: string
  description: string
  technologies?: string[]
  url?: string
}

export interface SourceData {
  path: string
}

export interface UserDocumentData {
  filename: string
}

export interface AgentActivityData {
  id: string
  kind: 'model' | 'tool'
  status: 'running' | 'completed' | 'error' | 'interrupted'
  tool_name?: string
  duration_ms?: number
  result_count?: number
}

export type ProfileDataParts = {
  'contact-offer': { mode: 'demo' }
  'contact-form': { mode: 'demo' }
  'contact-choice': { choice: 'details' | 'compose'; offer_message_id: string }
  'agent-activity': AgentActivityData
  'feature-used': { feature: 'streaming' }
  'candidate-photo': CandidatePhotoData
  technologies: TechnologyData
  project: ProjectData
  source: SourceData
  'user-document': UserDocumentData
}

export type ProfileMessage = UIMessage<never, ProfileDataParts>
