import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submitApproval, getApprovalHistory, type ApprovalPayload } from '@/services/approval.service';

/**
 * Hook wrapping approval.service for a specific dossier.
 * Provides approval history query + submit mutation with optimistic updates.
 */
export function useApproval(dossierId: string) {
  const queryClient = useQueryClient();

  const historyQuery = useQuery({
    queryKey: ['approval-history', dossierId],
    queryFn: () => getApprovalHistory(dossierId),
    enabled: !!dossierId,
    staleTime: 30_000,
  });

  const approvalMutation = useMutation({
    mutationFn: (payload: ApprovalPayload) => submitApproval(dossierId, payload),
    // Optimistic update: append the new decision immediately
    onMutate: async (payload: ApprovalPayload) => {
      await queryClient.cancelQueries({ queryKey: ['approval-history', dossierId] });
      const previous = queryClient.getQueryData(['approval-history', dossierId]);

      const optimistic = {
        id: `temp-${Date.now()}`,
        dossier_id: dossierId,
        decision: payload.decision,
        approver: payload.approver,
        rationale: payload.rationale,
        decided_at: new Date().toISOString(),
      };

      queryClient.setQueryData(['approval-history', dossierId], (old: any) => {
        if (Array.isArray(old)) return [optimistic, ...old];
        if (old?.records) return { ...old, records: [optimistic, ...old.records] };
        return [optimistic];
      });

      return { previous };
    },
    onError: (_err: unknown, _vars: ApprovalPayload, context: { previous?: unknown } | undefined) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(['approval-history', dossierId], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-history', dossierId] });
      queryClient.invalidateQueries({ queryKey: ['simulation-dossier', dossierId] });
    },
  });

  const rawData = historyQuery.data as any;
  const history = Array.isArray(rawData)
    ? rawData
    : rawData?.history || rawData?.records || [];

  return {
    /** Approval history records */
    history,
    isLoading: historyQuery.isLoading,
    error: historyQuery.error,
    /** Submit an approval decision: { decision, approver, rationale } */
    submitApproval: approvalMutation.mutate,
    isSubmitting: approvalMutation.isPending,
    submitError: approvalMutation.error,
    submitSuccess: approvalMutation.isSuccess,
  };
}
