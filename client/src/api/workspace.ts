import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

export interface TeamMember {
  id: number;
  user_id: number;
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  status: 'active' | 'pending' | 'suspended';
  invited_at: string;
  joined_at?: string;
}

export interface WorkspaceInvite {
  id: number;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  status: 'pending' | 'accepted' | 'expired';
  invited_at: string;
  expires_at?: string;
}

export interface NotificationSettings {
  email_enabled: boolean;
  email_address: string | null;
  alert_types: {
    runway_warning: boolean;
    growth_decline: boolean;
    churn_spike: boolean;
    cash_low: boolean;
    scenario_complete: boolean;
    team_activity: boolean;
  };
  thresholds: {
    runway_months: number;
    growth_decline_pct: number;
    churn_increase_pct: number;
    cash_low_months: number;
  };
  frequency: 'immediate' | 'daily' | 'weekly';
}

export interface Comment {
  id: number;
  scenario_id: number;
  user_id: number;
  user_email: string;
  content: string;
  created_at: string;
  updated_at?: string;
  parent_id?: number;
}

export function useWorkspaceMembers(companyId: number) {
  return useQuery<TeamMember[]>({
    queryKey: ['/workspace/companies', companyId, 'members'],
    queryFn: async () => {
      const res = await fetch(`/api/workspace/companies/${companyId}/members`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch members');
      return res.json();
    },
    enabled: !!companyId,
  });
}

export function useWorkspaceInvites(companyId: number) {
  return useQuery<WorkspaceInvite[]>({
    queryKey: ['/workspace/companies', companyId, 'invites'],
    queryFn: async () => {
      const res = await fetch(`/api/workspace/companies/${companyId}/invites`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch invites');
      return res.json();
    },
    enabled: !!companyId,
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ companyId, email, role }: { companyId: number; email: string; role: string }) => {
      return apiRequest('POST', `/api/workspace/companies/${companyId}/invite`, { email, role });
    },
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['/workspace/companies', companyId, 'invites'] });
    },
  });
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ memberId, role, companyId }: { memberId: number; role: string; companyId: number }) => {
      return apiRequest('PATCH', `/api/workspace/members/${memberId}/role`, { role });
    },
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['/workspace/companies', companyId, 'members'] });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ memberId, companyId }: { memberId: number; companyId: number }) => {
      return apiRequest('DELETE', `/api/workspace/members/${memberId}`);
    },
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['/workspace/companies', companyId, 'members'] });
    },
  });
}

export function useRevokeInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ inviteId, companyId }: { inviteId: number; companyId: number }) => {
      return apiRequest('DELETE', `/api/workspace/invites/${inviteId}`);
    },
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['/workspace/companies', companyId, 'invites'] });
    },
  });
}

export function useResendInvite() {
  return useMutation({
    mutationFn: async ({ inviteId }: { inviteId: number }) => {
      return apiRequest('POST', `/api/workspace/invites/${inviteId}/resend`);
    },
  });
}

export function useNotificationPreferences() {
  return useQuery<NotificationSettings>({
    queryKey: ['/workspace/notifications/preferences'],
    queryFn: async () => {
      const res = await fetch('/api/workspace/notifications/preferences', {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch notification preferences');
      return res.json();
    },
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (settings: NotificationSettings) => {
      return apiRequest('PUT', '/api/workspace/notifications/preferences', settings);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/workspace/notifications/preferences'] });
    },
  });
}

export function useScenarioComments(scenarioId: number) {
  return useQuery<Comment[]>({
    queryKey: ['/comments/scenarios', scenarioId],
    queryFn: async () => {
      const res = await fetch(`/api/comments/scenarios/${scenarioId}`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch comments');
      return res.json();
    },
    enabled: !!scenarioId,
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ scenarioId, content, parentId }: { scenarioId: number; content: string; parentId?: number }) => {
      return apiRequest('POST', `/api/comments/scenarios/${scenarioId}`, { content, parent_id: parentId });
    },
    onSuccess: (_, { scenarioId }) => {
      queryClient.invalidateQueries({ queryKey: ['/comments/scenarios', scenarioId] });
    },
  });
}

export function useEditComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, content, scenarioId }: { commentId: number; content: string; scenarioId: number }) => {
      return apiRequest('PATCH', `/api/comments/${commentId}`, { content });
    },
    onSuccess: (_, { scenarioId }) => {
      queryClient.invalidateQueries({ queryKey: ['/comments/scenarios', scenarioId] });
    },
  });
}

export function useDeleteComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, scenarioId }: { commentId: number; scenarioId: number }) => {
      return apiRequest('DELETE', `/api/comments/${commentId}`);
    },
    onSuccess: (_, { scenarioId }) => {
      queryClient.invalidateQueries({ queryKey: ['/comments/scenarios', scenarioId] });
    },
  });
}
