import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn(), eject: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn() },
  },
};

vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => mockClient),
    },
  };
});

let apiService: any;

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();

    mockClient.get.mockReset();
    mockClient.post.mockReset();
    mockClient.put.mockReset();
    mockClient.delete.mockReset();

    // Mock localStorage
    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
      length: 0,
      key: vi.fn(),
    };
  });

  beforeEach(async () => {
    ({ apiService } = await import('../api'));
  });

  describe('Health & Statistics', () => {
    it('should fetch health status', async () => {
      const mockResponse = { status: 'healthy', version: '2.0.0' };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getHealth();
      expect(result).toEqual(mockResponse);
    });

    it('should fetch system statistics', async () => {
      const mockStats = {
        total_nodes: 4275,
        total_relationships: 10048,
        node_types: { Requirement: 100, Part: 200 },
        relationship_types: { SATISFIES: 50 },
      };
      
      mockClient.get.mockResolvedValue({ data: mockStats });

      const result = await apiService.getStatistics();
      expect(result.total_nodes).toBe(4275);
      expect(result.node_types).toHaveProperty('Requirement');
    });
  });

  describe('Artifacts', () => {
    it('should search artifacts with parameters', async () => {
      const mockArtifacts = [
        { id: '1', type: 'Package', name: 'Test Package' },
        { id: '2', type: 'Class', name: 'Test Class' },
      ];
      
      mockClient.get.mockResolvedValue({ data: mockArtifacts });

      const result = await apiService.searchArtifacts({ 
        type: 'Package', 
        limit: 10 
      });
      expect(result).toHaveLength(2);
    });

    it('should reject getArtifact with missing parameters', async () => {
      await expect(apiService.getArtifact('', 'id')).rejects.toThrow();
      await expect(apiService.getArtifact('type', '')).rejects.toThrow();
    });
  });

  describe('SMRL API', () => {
    it('should get SMRL resource', async () => {
      const mockResource = {
        uid: 'REQ-001',
        name: 'Test Requirement',
        type: 'Requirement',
      };
      
      mockClient.get.mockResolvedValue({ data: mockResource });

      const result = await apiService.smrl.getResource('Requirement', 'REQ-001');
      expect(result.uid).toBe('REQ-001');
    });

    it('should list SMRL resources with pagination', async () => {
      const mockList = [
        { uid: 'REQ-001' },
        { uid: 'REQ-002' },
      ];
      
      mockClient.get.mockResolvedValue({ data: mockList });

      const result = await apiService.smrl.listResources('Requirement', {
        limit: 100,
        offset: 0,
      });
      expect(result).toHaveLength(2);
    });

    it('should create SMRL resource', async () => {
      const newResource = { name: 'New Requirement', text: 'Test' };
      const created = { uid: 'REQ-003', ...newResource };
      
      mockClient.post.mockResolvedValue({ data: created });

      const result = await apiService.smrl.createResource('Requirement', newResource);
      expect(result.uid).toBe('REQ-003');
    });

    it('should update SMRL resource', async () => {
      const updated = { uid: 'REQ-001', name: 'Updated' };
      
      mockClient.put.mockResolvedValue({ data: updated });

      const result = await apiService.smrl.updateResource('Requirement', 'REQ-001', updated);
      expect(result.name).toBe('Updated');
    });

    it('should delete SMRL resource', async () => {
      mockClient.delete.mockResolvedValue({ data: { success: true } });

      const result = await apiService.smrl.deleteResource('Requirement', 'REQ-001');
      expect(result.success).toBe(true);
    });
  });

  describe('AP239 Requirements', () => {
    it('should fetch requirements list', async () => {
      const mockRequirements = [
        { uid: 'REQ-001', name: 'Test Req' },
      ];

      mockClient.get.mockResolvedValue({ data: mockRequirements });

      const result = await apiService.ap239.getRequirements();
      expect(result).toHaveLength(1);
    });

    it('should fetch requirement traceability', async () => {
      const mockTraceability = {
        uid: 'REQ-001',
        satisfied_by: ['PART-001'],
        derived_from: ['REQ-000'],
      };
      
      mockClient.get.mockResolvedValue({ data: mockTraceability });

      const result = await apiService.ap239.getRequirementTraceability('REQ-001');
      expect(result.satisfied_by).toHaveLength(1);
    });
  });
});
