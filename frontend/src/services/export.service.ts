/** Export service — schema, graph, and data export endpoints */
import { apiClient } from './api';

export const exportSchema = (format?: string) =>
  apiClient.get<any>('/export/schema', { params: { format } });

export const exportGraphML = () =>
  apiClient.get<string>('/export/graphml', { responseType: 'text' } as any);

export const exportJSONLD = () =>
  apiClient.get<any>('/export/jsonld');

export const exportCSV = (nodeType?: string) =>
  apiClient.get<string>('/export/csv', { params: { node_type: nodeType }, responseType: 'text' } as any);

export const exportSTEP = () =>
  apiClient.get<string>('/export/step', { responseType: 'text' } as any);

export const exportPlantUML = () =>
  apiClient.get<string>('/export/plantuml', { responseType: 'text' } as any);

export const exportRDF = (format?: string) =>
  apiClient.get<string>('/export/rdf', { params: { format }, responseType: 'text' } as any);

export const exportCytoscape = () =>
  apiClient.get<any>('/export/cytoscape');
