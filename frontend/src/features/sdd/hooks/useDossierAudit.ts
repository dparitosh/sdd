import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { runAudit, getAuditFindings } from '@/services/audit.service';

/**
 * Hook wrapping audit.service for a specific dossier.
 * Provides audit findings query + runAudit mutation with auto-invalidation.
 */
export function useDossierAudit(dossierId: string) {
  const queryClient = useQueryClient();

  const findingsQuery = useQuery({
    queryKey: ['audit-findings', dossierId],
    queryFn: () => getAuditFindings(dossierId),
    enabled: !!dossierId,
    staleTime: 30_000,
  });

  const auditMutation = useMutation({
    mutationFn: () => runAudit(dossierId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-findings', dossierId] });
    },
  });

  return {
    /** Audit result data (score, findings, ran_at) */
    auditResult: findingsQuery.data ?? null,
    findings: findingsQuery.data?.findings ?? [],
    score: findingsQuery.data?.score ?? null,
    isLoading: findingsQuery.isLoading,
    error: findingsQuery.error,
    /** Trigger a new audit run */
    runAudit: auditMutation.mutate,
    isRunning: auditMutation.isPending,
    runError: auditMutation.error,
  };
}
