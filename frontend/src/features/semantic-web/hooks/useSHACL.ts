import { useMutation } from '@tanstack/react-query';
import * as validationService from '@/services/validation.service';

/**
 * Hook for SHACL shape validation.
 *
 * Provides:
 * - validate mutation (data + optional shapeName)
 * - result, isValidating, error
 */
export function useSHACL() {
  const mutation = useMutation({
    mutationFn: ({ data, shapeName }: { data: any; shapeName?: string }) =>
      validationService.validateSHACL(data, shapeName).then((r) => (r as any).data ?? r),
  });

  return {
    validate: mutation.mutateAsync,
    result: mutation.data ?? null,
    isValidating: mutation.isPending,
    error: mutation.error,
    reset: mutation.reset,
  };
}
