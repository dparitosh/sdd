import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as ontologyService from '@/services/ontology.service';

const KEYS = {
  ontologies: ['ontology', 'list'],
};

/**
 * Hook for ontology ingestion and browsing.
 *
 * Provides:
 * - ontologies list query
 * - ingest mutation (file upload)
 */
export function useOntology() {
  const qc = useQueryClient();

  // ── Queries ──────────────────────────────────────────────────
  const ontologiesQuery = useQuery({
    queryKey: KEYS.ontologies,
    queryFn: () => ontologyService.getOntologies().then((r) => (r as any).data ?? r),
    staleTime: 60_000,
  });

  // ── Mutations ────────────────────────────────────────────────
  const ingestMutation = useMutation({
    mutationFn: (file: File) =>
      ontologyService.ingestOntology(file).then((r) => (r as any).data ?? r),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.ontologies });
    },
  });

  // Build a simple class hierarchy from the ontology data
  const classHierarchy = buildHierarchy(ontologiesQuery.data);

  return {
    ontologies: ontologiesQuery.data ?? [],
    isLoading: ontologiesQuery.isLoading,
    error: ontologiesQuery.error,
    refetch: ontologiesQuery.refetch,
    ingest: ingestMutation.mutateAsync,
    isIngesting: ingestMutation.isPending,
    ingestResult: ingestMutation.data ?? null,
    ingestError: ingestMutation.error,
    classHierarchy,
  };
}

// ── Helpers ────────────────────────────────────────────────────

interface ClassNode {
  uri: string;
  label: string;
  children: ClassNode[];
  properties?: string[];
  description?: string;
}

/**
 * Transform flat ontology list into a class hierarchy tree.
 * Each ontology entry is expected to have { uri, label, parent?, properties?, description? }.
 */
function buildHierarchy(data: any[] | undefined): ClassNode[] {
  if (!data || data.length === 0) return [];

  const nodeMap = new Map<string, ClassNode>();
  const roots: ClassNode[] = [];

  for (const item of data) {
    const node: ClassNode = {
      uri: item.uri ?? item.id ?? '',
      label: item.label ?? item.name ?? item.uri ?? 'Unknown',
      children: [],
      properties: item.properties,
      description: item.description,
    };
    nodeMap.set(node.uri, node);
  }

  for (const item of data) {
    const uri = item.uri ?? item.id ?? '';
    const parentUri = item.parent ?? item.superclass ?? null;
    const node = nodeMap.get(uri);
    if (!node) continue;

    if (parentUri && nodeMap.has(parentUri)) {
      nodeMap.get(parentUri)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}
