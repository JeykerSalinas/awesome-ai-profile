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

export type ProfileDataParts = {
  'candidate-photo': CandidatePhotoData
  technologies: TechnologyData
  project: ProjectData
  source: SourceData
  'user-document': UserDocumentData
}

export type ProfileMessage = UIMessage<never, ProfileDataParts>
