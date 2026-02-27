import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useDebounce } from 'use-debounce';
import { getDossiers, getDossierStatistics, createDossier } from '@/services/sdd.service';
import { 
  AlertCircle, 
  FileText, 
  Search, 
  Plus, 
  ChevronRight,
  Clock,
  CheckCircle,
  FileBox,
  X,
  Loader2,
  Package,
  Activity,
  TrendingUp,
} from 'lucide-react';
import logger from '@/utils/logger';

const getStatusStyle = (status) => {
  switch(status) {
    case 'APPROVED': return 'bg-emerald-100 text-emerald-700';
    case 'PENDING_REVIEW': return 'bg-amber-100 text-amber-700';
    case 'REJECTED': return 'bg-rose-100 text-rose-700';
    case 'IN_PROGRESS': return 'bg-blue-100 text-blue-700';
    default: return 'bg-slate-100 text-slate-600';
  }
};

const getStatusIcon = (status) => {
  switch(status) {
    case 'APPROVED': return CheckCircle;
    case 'PENDING_REVIEW': return Clock;
    case 'REJECTED': return AlertCircle;
    default: return Activity;
  }
};

const DossierList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Create dossier modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [newDossier, setNewDossier] = useState({
    name: '',
    type: 'simulation',
    description: '',
    linkedPart: '',
    linkedRequirement: '',
  });

  // Create dossier mutation
  const createMutation = useMutation({
    mutationFn: (data) => createDossier(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['simulation-dossiers'] });
      queryClient.invalidateQueries({ queryKey: ['simulation-statistics'] });
      setCreateOpen(false);
      setNewDossier({ name: '', type: 'simulation', description: '', linkedPart: '', linkedRequirement: '' });
      // Navigate to the newly created dossier if we got an id back
      if (result?.id) {
        navigate(`/simulation/dossiers/${result.id}`);
      }
    },
  });

  const handleCreateSubmit = () => {
    if (!newDossier.name.trim()) return;
    createMutation.mutate({
      name: newDossier.name,
      type: newDossier.type,
      description: newDossier.description,
      linkedPart: newDossier.linkedPart || undefined,
      linkedRequirement: newDossier.linkedRequirement || undefined,
    });
  };

  // Fetch dossiers
  const {
    data: dossiersData,
    isLoading: loadingDossiers,
    error: dossiersError,
    refetch: refetchDossiers
  } = useQuery({
    queryKey: ['simulation-dossiers', statusFilter],
    queryFn: () => {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      return getDossiers(params);
    },
    refetchInterval: 30000,
  });

  // Fetch statistics
  const { data: statsData } = useQuery({
    queryKey: ['simulation-statistics'],
    queryFn: () => getDossierStatistics(),
    refetchInterval: 60000,
  });

  const dossiers = dossiersData?.dossiers || [];
  const filteredDossiers = dossiers.filter(d => 
    !debouncedSearchQuery || 
    d.name?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
    d.id?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
    d.motor_id?.toLowerCase().includes(debouncedSearchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">My Simulation Dossiers</h1>
          <p className="text-slate-500 text-sm">Manage and track certification evidence packages</p>
        </div>
        <button 
          onClick={() => setCreateOpen(true)}
          className="bg-[#004A99] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-[#003d7a] transition-colors"
        >
          + Create New Dossier
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
              <Package size={20} />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-800">{statsData?.total_dossiers || 0}</div>
          <div className="text-xs font-medium text-slate-500 mt-1">Total Dossiers</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600">
              <FileText size={20} />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-800">{statsData?.total_artifacts || 0}</div>
          <div className="text-xs font-medium text-slate-500 mt-1">Artifacts</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="p-2.5 rounded-xl bg-violet-50 text-violet-600">
              <Activity size={20} />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-800">{statsData?.total_evidence_categories || 0}</div>
          <div className="text-xs font-medium text-slate-500 mt-1">Evidence Categories</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
              <TrendingUp size={20} />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-800">{statsData?.total_requirements || 0}</div>
          <div className="text-xs font-medium text-slate-500 mt-1">Traced Requirements</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, ID, or motor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent bg-white"
        >
          <option value="all">All Statuses</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {/* Error Alert */}
      {dossiersError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800">Failed to load dossiers</p>
            <p className="text-xs text-red-700 mt-1">{dossiersError.message}</p>
          </div>
        </div>
      )}

      {/* Dossiers Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="font-bold text-sm text-slate-800">Dossiers ({filteredDossiers.length})</h3>
            <p className="text-xs text-slate-500 mt-0.5">MOSSEC-compliant evidence packages</p>
          </div>
        </div>

        {loadingDossiers ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Dossier ID</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Name</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Motor ID</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Version</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Credibility</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">Engineer</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDossiers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-slate-500 text-sm">
                      No dossiers found
                    </td>
                  </tr>
                ) : (
                  filteredDossiers.map((dossier) => {
                    const StatusIcon = getStatusIcon(dossier.status);
                    return (
                      <tr key={dossier.id} className="hover:bg-slate-50/80 transition-colors group">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-slate-100 rounded text-slate-500 group-hover:bg-[#00B0E4] group-hover:text-white transition-colors">
                              <FileBox size={16} />
                            </div>
                            <span className="font-bold text-slate-700">{dossier.id}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600 font-medium">{dossier.name}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{dossier.motor_id || '-'}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{dossier.version || 'v1.0'}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${getStatusStyle(dossier.status)}`}>
                            <StatusIcon size={10} />
                            {dossier.status?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold uppercase bg-purple-100 text-purple-700">
                            {dossier.credibility_level || 'PC2'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">{dossier.engineer || '-'}</td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => navigate(`/engineer/simulation/dossiers/${dossier.id}`)}
                            className="text-[#004A99] hover:text-[#003d7a] font-bold text-sm flex items-center gap-1 ml-auto transition-colors"
                          >
                            View Details <ChevronRight size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Dossier Modal */}
      {createOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setCreateOpen(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-800">Create New Dossier</h2>
                <p className="text-xs text-slate-500 mt-0.5">Create a MOSSEC-compliant evidence package</p>
              </div>
              <button
                onClick={() => setCreateOpen(false)}
                className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X size={18} className="text-slate-400" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-4 space-y-4">
              <div className="space-y-2">
                <label htmlFor="dossier-name" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Name *
                </label>
                <input
                  id="dossier-name"
                  type="text"
                  placeholder="Enter dossier name"
                  value={newDossier.name}
                  onChange={(e) => setNewDossier((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="dossier-type" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Type
                </label>
                <select
                  id="dossier-type"
                  value={newDossier.type}
                  onChange={(e) => setNewDossier((prev) => ({ ...prev, type: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent bg-white"
                >
                  <option value="simulation">Simulation</option>
                  <option value="test">Test</option>
                  <option value="analysis">Analysis</option>
                  <option value="certification">Certification</option>
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="dossier-desc" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Description
                </label>
                <textarea
                  id="dossier-desc"
                  placeholder="Describe the purpose of this dossier…"
                  rows={3}
                  value={newDossier.description}
                  onChange={(e) => setNewDossier((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent resize-none"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="linked-part" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Linked Part (optional)
                </label>
                <input
                  id="linked-part"
                  type="text"
                  placeholder="Search for a part to link…"
                  value={newDossier.linkedPart}
                  onChange={(e) => setNewDossier((prev) => ({ ...prev, linkedPart: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="linked-req" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Linked Requirement (optional)
                </label>
                <input
                  id="linked-req"
                  type="text"
                  placeholder="Search for a requirement to link…"
                  value={newDossier.linkedRequirement}
                  onChange={(e) => setNewDossier((prev) => ({ ...prev, linkedRequirement: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent"
                />
              </div>

              {createMutation.isError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">
                    {createMutation.error?.message || 'Failed to create dossier'}
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setCreateOpen(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSubmit}
                disabled={createMutation.isPending || !newDossier.name.trim()}
                className="px-4 py-2 rounded-lg text-sm font-bold text-white bg-[#004A99] hover:bg-[#003d7a] disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Create Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DossierList;
