import { queryOptions } from '@tanstack/react-query'
import { z } from 'zod'

import { ApiError, apiRequest } from '@/lib/api/client'
import { groupNameSchema, nickSchema } from '@/lib/api/schemas'

export const groupSchema = z.object({
  id: z.string(),
  name: z.string(),
  owner_id: z.string(),
  created_at: z.string(),
})

export const memberSchema = z.object({
  user_id: z.string(),
  nick: z.string(),
  status: z.enum(['invited', 'accepted']),
  created_at: z.string(),
})

export const invitationSchema = z.object({
  id: z.string(),
  group: z.object({
    id: z.string(),
    name: z.string(),
  }),
  invited_by: z.object({
    id: z.string(),
    nick: z.string(),
  }),
  created_at: z.string(),
})

export const groupNameInputSchema = z.object({
  name: groupNameSchema,
})

export const inviteInputSchema = z.object({
  nick: nickSchema,
})

export type Group = z.infer<typeof groupSchema>
export type Member = z.infer<typeof memberSchema>
export type Invitation = z.infer<typeof invitationSchema>
export type GroupNameInput = z.infer<typeof groupNameInputSchema>
export type InviteInput = z.infer<typeof inviteInputSchema>

export const groupKeys = {
  all: ['groups'] as const,
  list: () => ['groups', 'list'] as const,
  members: (groupId: string) => ['groups', 'members', groupId] as const,
}

export const invitationKeys = {
  all: ['invitations'] as const,
  list: () => ['invitations', 'list'] as const,
}

export async function listGroups(signal?: AbortSignal) {
  return apiRequest('/groups', z.array(groupSchema), { signal })
}

export async function createGroup(input: GroupNameInput) {
  const payload = groupNameInputSchema.parse(input)
  return apiRequest('/groups', groupSchema, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function renameGroup(groupId: string, input: GroupNameInput) {
  const payload = groupNameInputSchema.parse(input)
  return apiRequest(`/groups/${groupId}`, groupSchema, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function listMembers(groupId: string, signal?: AbortSignal) {
  return apiRequest(`/groups/${groupId}/members`, z.array(memberSchema), {
    signal,
  })
}

export async function inviteMember(groupId: string, input: InviteInput) {
  const payload = inviteInputSchema.parse(input)
  return apiRequest(`/groups/${groupId}/invitations`, z.unknown(), {
    method: 'POST',
    conflict: 'invitation',
    notFoundMessage: 'Não há conta com esse nick.',
    body: JSON.stringify(payload),
  })
}

export async function leaveGroup(groupId: string) {
  return apiRequest(`/groups/${groupId}/leave`, z.unknown(), {
    method: 'POST',
  })
}

export async function listInvitations(signal?: AbortSignal) {
  try {
    return await apiRequest('/invitations', z.array(invitationSchema), {
      signal,
    })
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return []
    }

    throw error
  }
}

export async function acceptInvitation(invitationId: string) {
  return apiRequest(`/invitations/${invitationId}/accept`, z.unknown(), {
    method: 'POST',
  })
}

export async function declineInvitation(invitationId: string) {
  return apiRequest(`/invitations/${invitationId}/decline`, z.unknown(), {
    method: 'POST',
  })
}

export function groupsQueryOptions() {
  return queryOptions({
    queryKey: groupKeys.list(),
    queryFn: ({ signal }) => listGroups(signal),
  })
}

export function membersQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: groupKeys.members(groupId),
    queryFn: ({ signal }) => listMembers(groupId, signal),
  })
}

export function invitationsQueryOptions() {
  return queryOptions({
    queryKey: invitationKeys.list(),
    queryFn: ({ signal }) => listInvitations(signal),
  })
}
