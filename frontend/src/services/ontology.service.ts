/** Ontology service — OWL/RDF ontology ingestion */
import { apiClient } from './api';

export const ingestOntology = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post<{ status: string; triples: number }>(
    '/ontology/ingest',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
};

export const getOntologies = () =>
  apiClient.get<any[]>('/ontology');
