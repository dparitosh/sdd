import i18n from '../i18n';
import { apiClient } from './api';

type GraphQLError = {
  message: string;
};

type GraphQLResponse<T> = {
  data?: T;
  errors?: GraphQLError[];
};

/**
 * Execute a GraphQL request via the shared apiClient.
 *
 * Using apiClient ensures the JWT Bearer token and X-API-Key header are
 * automatically injected by the axios request interceptor, and all error/
 * retry logic from the response interceptor applies.
 */
export async function graphqlRequest<TData, TVariables extends Record<string, unknown> | undefined = undefined>(
  query: string,
  variables?: TVariables
): Promise<TData> {
  const payload: GraphQLResponse<TData> = await apiClient.post('/graphql', { query, variables });

  if ((payload as any).errors && (payload as any).errors.length > 0) {
    throw new Error((payload as any).errors[0].message);
  }

  if (!payload.data) {
    throw new Error('GraphQL response missing data');
  }

  return payload.data;
}

export type Statistics = {
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
};

export const graphqlService = {
  async getStatistics(): Promise<Statistics> {
    const data = await graphqlRequest<{ statistics: Statistics }>(`
      query GetStatistics {
        statistics
      }
    `);

    return data.statistics;
  },
};
