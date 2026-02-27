import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';
import * as oslcService from '@/services/oslc.service';

const KEYS = {
  rootServices: ['oslc', 'rootServices'],
  catalog:      ['oslc', 'catalog'],
  trsBase:      ['oslc', 'trs', 'base'],
  trsChangelog: ['oslc', 'trs', 'changelog'],
  trs:          ['oslc', 'trs'],
};

/**
 * Hook for all OSLC resource browsing & TRS feed interaction.
 *
 * Provides:
 * - rootServices / catalog / provider queries
 * - TRS base & changelog queries
 * - connect + query mutations
 * - refreshTRS helper
 */
export function useOSLC() {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);

  // ── Queries ──────────────────────────────────────────────────
  const rootServices = useQuery({
    queryKey: KEYS.rootServices,
    queryFn: async () => {
      try {
        const response = await oslcService.getRootServices();
        return response.data ?? null;
      } catch {
        return null;
      }
    },
    enabled: false,
  });

  const catalog = useQuery({
    queryKey: KEYS.catalog,
    queryFn: async () => {
      try {
        const response = await oslcService.getCatalog();
        return response.data ?? null;
      } catch {
        return null;
      }
    },
    enabled: false,
  });

  const trsBase = useQuery({
    queryKey: KEYS.trsBase,
    queryFn: async () => {
      try {
        const response = await oslcService.getTRSBase();
        return response.data ?? { resources: [], nextPage: null };
      } catch {
        return { resources: [], nextPage: null };
      }
    },
    staleTime: 30_000,
  });

  const trsChangelog = useQuery({
    queryKey: KEYS.trsChangelog,
    queryFn: async () => {
      try {
        const response = await oslcService.getTRSChangelog();
        return response.data ?? { changes: [] };
      } catch {
        return { changes: [] };
      }
    },
    staleTime: 30_000,
  });

  // ── Mutations ────────────────────────────────────────────────
  const connectMutation = useMutation({
    mutationFn: (data: Parameters<typeof oslcService.connectOSLC>[0]) =>
      oslcService.connectOSLC(data).then((r) => r.data),
    onSuccess: () => {
      setConnected(true);
      rootServices.refetch();
      catalog.refetch();
    },
  });

  const queryMutation = useMutation({
    mutationFn: (params: Parameters<typeof oslcService.queryOSLC>[0]) =>
      oslcService.queryOSLC(params).then((r) => r.data),
  });

  // ── Helpers ──────────────────────────────────────────────────
  const refreshTRS = useCallback(() => {
    qc.invalidateQueries({ queryKey: KEYS.trsBase });
    qc.invalidateQueries({ queryKey: KEYS.trsChangelog });
  }, [qc]);

  const getProvider = useCallback(
    (id: string) => oslcService.getProvider(id).then((r) => r.data),
    []
  );

  // ── Derived: serviceTree ─────────────────────────────────────
  // Build a browseable tree from rootServices + catalog data.
  const serviceTree = buildServiceTree(rootServices.data, catalog.data);

  return {
    // state
    connected,
    // queries
    rootServices: rootServices.data,
    catalog: catalog.data,
    serviceTree,
    trsBase: trsBase.data,
    trsChangelog: trsChangelog.data,
    isLoading: rootServices.isLoading || catalog.isLoading,
    isLoadingTRS: trsBase.isLoading || trsChangelog.isLoading,
    error: rootServices.error || catalog.error || null,
    // mutations
    connect: connectMutation.mutateAsync,
    isConnecting: connectMutation.isPending,
    connectError: connectMutation.error,
    query: queryMutation.mutateAsync,
    isQuerying: queryMutation.isPending,
    // helpers
    refreshTRS,
    getProvider,
    fetchRootServices: rootServices.refetch,
    fetchCatalog: catalog.refetch,
  };
}

// ── Helpers ──────────────────────────────────────────────────
interface TreeNode {
  uri?: string;
  title?: string;
  name?: string;
  type?: string;
  children?: TreeNode[];
  dialogs?: { type: string; uri?: string; url?: string }[];
}

/**
 * Build a service tree from rootServices and catalog data.
 * Handles both RDF-parsed objects and plain JSON payloads gracefully.
 */
function buildServiceTree(rootData: any, catalogData: any): TreeNode[] {
  const tree: TreeNode[] = [];

  // rootServices node
  if (rootData) {
    const rsNode: TreeNode = {
      uri: rootData.uri ?? rootData.about ?? 'rootservices',
      title: rootData.title ?? rootData.label ?? 'Root Services',
      type: 'RootServices',
      children: [],
    };
    // If rootData has catalog references, add them
    if (Array.isArray(rootData.catalogs)) {
      rsNode.children = rootData.catalogs.map((c: any) => ({
        uri: c.uri ?? c.url,
        title: c.title ?? c.label ?? c.uri ?? 'Catalog',
        type: 'Catalog',
        children: [],
      }));
    }
    tree.push(rsNode);
  }

  // catalog / service providers
  if (catalogData) {
    const providers = Array.isArray(catalogData)
      ? catalogData
      : catalogData.serviceProviders ?? catalogData.providers ?? [];

    if (providers.length > 0) {
      const catNode: TreeNode = {
        uri: catalogData.uri ?? 'catalog',
        title: catalogData.title ?? 'Service Provider Catalog',
        type: 'Catalog',
        children: providers.map((sp: any) => {
          const spNode: TreeNode = {
            uri: sp.uri ?? sp.url ?? sp.id,
            title: sp.title ?? sp.label ?? sp.name ?? sp.id ?? 'Provider',
            type: 'ServiceProvider',
            children: [],
            dialogs: Array.isArray(sp.dialogs) ? sp.dialogs : [],
          };
          if (Array.isArray(sp.services)) {
            spNode.children = sp.services.map((svc: any) => ({
              uri: svc.uri ?? svc.url,
              title: svc.title ?? svc.label ?? svc.uri ?? 'Service',
              type: 'Service',
              children: [],
            }));
          }
          return spNode;
        }),
      };
      // Avoid duplicate if rootData already included it
      if (!rootData) tree.push(catNode);
      else tree[0].children = [...(tree[0].children ?? []), catNode];
    }
  }

  return tree;
}
