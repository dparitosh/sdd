import i18n from '../i18n';

const GRAPHQL_ENDPOINT = '/api/graphql';

type GraphQLError = {
  message: string;
};

type GraphQLResponse<T> = {
  data?: T;
  errors?: GraphQLError[];
};

export async function graphqlRequest<TData, TVariables extends Record<string, unknown> | undefined = undefined>(
  query: string,
  variables?: TVariables
): Promise<TData> {
  const apiKey = import.meta.env.VITE_API_KEY;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const response = await fetch(GRAPHQL_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, variables }),
  });

  const payload = (await response.json()) as GraphQLResponse<TData>;

  if (!response.ok) {
    if (!apiKey && (response.status === 401 || response.status === 403)) {
      throw new Error(i18n.t('errors.apiKeyNotConfigured'));
    }
    const message = payload.errors?.[0]?.message || `GraphQL request failed (${response.status})`;
    throw new Error(message);
  }

  if (payload.errors && payload.errors.length > 0) {
    throw new Error(payload.errors[0].message);
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
