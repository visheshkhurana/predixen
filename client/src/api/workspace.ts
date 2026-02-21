import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { ApiError, safeParseJSON } from '@/lib/errors';

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
      let res: Response;
      try {
        res = await fetch(`/api/workspace/companies/${companyId}/members`, {
          credentials: 'include',
        });
      } catch (error) {
        const networkError = error instanceof Error ? error.message : String(error);
        console.error(`Network error fetching workspace members for company ${companyId}:`, error);
        throw new ApiError(0, `Failed to fetch members: ${networkError}`);
      }

      if (!res.ok) {
        throw new ApiError(res.status, `Failed to fetch members (${res.status})`);
      }

      try {
        return await safeParseJSON(res, 'Failed to parse members response') as TeamMember[];
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        throw new ApiError(res.status, 'Failed to parse members response');
      }
    },
    enabled: !!companyId,
  });
}

export function useWorkspaceInvites(companyId: number) {
  return useQuery<WorkspaceInvite[]>({
    queryKey: ['/workspace/companies', companyId, 'invites'],
    queryFn: async () => {
      let res: Response;
      try {
        res = await fetch(`/api/workspace/companies/${companyId}/invites`, {
          credentials: 'include',
        });
      } catch (error) {
        const networkError = error instanceof Error ? error.message : String(error);
        console.error(`Network error fetching workspace invites for company ${companyId}:`, error);
        throw new ApiError(0, `Failed to fetch invites: ${networkError}`);
      }

      if (!res.ok) {
        throw new ApiError(res.status, `Failed to fetch invites (${res.status})`);
      }

      try {
        return await safeParseJSON(res, 'Failed to parse invites response') as WorkspaceInvite[];
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        throw new ApiError(res.status, 'Failed to parse invites response');
      }
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
      let res: Response;
      try {
        res = await fetch('/api/workspace/notifications/preferences', {
          credentials: 'include',
        });
      } catch (error) {
        const networkError = error instanceof Error ? error.message : String(error);
        console.error('Network error fetching notification preferences:', error);
        throw new ApiError(0, `Failed to fetch notification preferences: ${networkError}`);
      }

      if (!res.ok) {
        throw new ApiError(res.status, `Failed to fetch notification preferences (${res.status})`);
      }

      try {
        return await safeParseJSON(res, 'Failed to parse notification preferences') as NotificationSettings;
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        throw new ApiError(res.status, 'Failed to parse notification preferences');
      }
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
      let res: Response;
      try {
        res = await fetch(`/api/comments/scenarios/${scenarioId}`, {
          credentials: 'include',
        });
      } catch (error) {
        const networkError = error instanceof Error ? error.message : String(error);
        console.error(`Network error fetching comments for scenario ${scenarioId}:`, error);
        throw new ApiError(0, `Failed to fetch comments: ${networkError}`);
      }

      if (!res.ok) {
        throw new ApiError(res.status, `Failed to fetch comments (${res.status})`);
      }

      try {
        return await safeParseJSON(res, 'Failed to parse comments response') as Comment[];
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        throw new ApiError(res.status, 'Failed to parse comments response');
      }
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
