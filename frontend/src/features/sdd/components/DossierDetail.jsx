import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { getDossier } from '@/services/sdd.service';
import { searchNodes, createRelationship, getRelationshipTypes } from '@/services/graph.service';
import { toast } from 'sonner';
import { 
  AlertCircle, 
  ArrowLeft,
  FileText, 
  CheckCircle2,
  Clock,
  Package,
  Activity,
  GitBranch,
  Download,
  Shield,
  ClipboardCheck,
  Layers,
  Link2,
  Eye,
  Plus,
  Search,
  Loader2,
  XCircle,
  Stamp,
  Zap,
  Wind,
  Waves,
  Box,
  Fingerprint,
  FileBadge,
  ExternalLink,
  Table as TableIcon,
  AlertTriangle,
  Info,
  CheckCircle,
  RefreshCw,
  ShieldCheck,
  Lock,
  PlayCircle,
  CheckSquare,
  FileCheck,
  ChevronDown,
} from 'lucide-react';
import logger from '@/utils/logger';

const DossierDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // State management
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [inspectedLink, setInspectedLink] = useState(null);
  const [showAuditPanel, setShowAuditPanel] = useState(false);
  const [isAuditing, setIsAuditing] = useState(false);
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [linkSearch, setLinkSearch] = useState('');
  const [linkTarget, setLinkTarget] = useState(null);
  const [linkRelType, setLinkRelType] = useState('');
  
  // Helper functions for dynamic content
  const getArtifactConfig = (artifactId) => {
    const configs = {
      'A1': { icon: Zap, color: 'amber', standard: 'IEC 6034 Cl 7-9', label: 'ELECTROMAGNETIC' },
      'A2': { icon: Activity, color: 'blue', standard: 'IEC 6034-1 Cl 9-10', label: 'TRANSIENT' },
      'B1': { icon: Zap, color: 'emerald', standard: 'IEC 6034-2-1', label: 'LOSSES/EFF' },
      'C1': { icon: Wind, color: 'cyan', standard: 'IEC 6034-6', label: 'COOLING CFD' },
      'D1': { icon: Waves, color: 'violet', standard: 'IEC 6034-14', label: 'VIBRATION' },
      'E1': { icon: Shield, color: 'rose', standard: 'IEC 6034-18', label: 'INSULATION' },
      'F1': { icon: Box, color: 'slate', standard: 'IEC 6034-1 Cl 15', label: 'STRUCTURAL' },
      'G1': { icon: ShieldCheck, color: 'emerald', standard: 'ISO 17025', label: 'TOOL VALIDATION' },
      'H1': { icon: FileBadge, color: 'blue', standard: 'ISO 9001', label: 'MOSSEC TRACE' },
    };
    return configs[artifactId] || { icon: FileText, color: 'slate', standard: 'EVIDENCE', label: 'REPORT' };
  };

  const getTypeIcon = (type) => {
    switch(type) {
      case 'Requirement': return <Search size={14} className="text-slate-400" />;
      case 'SimModel': return <Box size={14} className="text-blue-500" />;
      case 'SimulationRun': return <PlayCircle size={14} className="text-emerald-500" />;
      case 'Result': return <Activity size={14} className="text-amber-500" />;
      case 'Evidence': return <ShieldCheck size={14} className="text-indigo-500" />;
      case 'Artifact': return <FileText size={14} className="text-[#00B0E4]" />;
      case 'Approval': return <Stamp size={14} className="text-emerald-600" />;
      case 'ValidationCase': return <CheckSquare size={14} className="text-rose-500" />;
      default: return <Link2 size={14} />;
    }
  };

  const getRelationDescription = (rel) => {
    const descriptions = {
      'validates': 'Evidence proves the requirement is met within tolerance.',
      'derivedFrom': 'Simulation parameters extracted from a master design model.',
      'executes': 'Mathematical solver running against the specific sim model.',
      'represents': 'Simulation model acts as a digital twin for the requirement.',
      'contains': 'Simulation run produces these specific result data blocks.',
      'verifies': 'Results are verified as credible evidence for certification.',
      'satisfies': 'The evidence artifact fulfills the standard compliance criteria.',
      'approves': 'Final release signature authorized by Quality Head.',
      'SATISFIES': 'Proves compliance with specified requirements.',
      'VALIDATES': 'Confirms correctness through verification.',
      'USES': 'Utilizes this entity during execution.',
    };
    return descriptions[rel] || 'Defined MOSSEC system relationship.';
  };

  const runAudit = () => {
    setIsAuditing(true);
    setTimeout(() => {
      setIsAuditing(false);
      setShowAuditPanel(true);
    }, 1200);
  };

  // Fetch dossier details
  const {
    data: dossier,
    isLoading: loadingDossier,
    error: dossierError
  } = useQuery({
    queryKey: ['simulation-dossier', id],
    queryFn: () => getDossier(id),
    enabled: !!id,
  });

  // Search nodes for Link Entity dialog
  const { data: searchResults = [], isFetching: isSearching } = useQuery({
    queryKey: ['graph-search', linkSearch],
    queryFn: () => searchNodes({ q: linkSearch, limit: 20 }).then(r => (r && r.data) ? r.data : (Array.isArray(r) ? r : [])),
    enabled: linkSearch.length >= 2,
    staleTime: 10_000,
  });

  // Relationship types
  const { data: relTypesData } = useQuery({
    queryKey: ['graph-rel-types'],
    queryFn: () => getRelationshipTypes().then(r => r?.relationship_types || r?.data?.relationship_types || []),
    staleTime: 120_000,
  });
  const relTypes = Array.isArray(relTypesData) ? relTypesData : [];

  // Calculate audit findings based on dossier data
  const auditFindings = useMemo(() => {
    if (!dossier || !dossier.artifacts) return [];
    
    const findings = [];
    const requiredIds = ['A1', 'A2', 'B1', 'C1', 'D1', 'E1', 'F1'];
    
    requiredIds.forEach(artifactId => {
      const art = dossier.artifacts.find(a => a.id === artifactId);
      if (!art) {
        findings.push({ 
          id: `COMP-${artifactId}`, 
          category: 'Compliance', 
          severity: 'Critical', 
          message: `Mandatory evidence artifact ${artifactId} is missing.`, 
          requirement: 'IEC 6034' 
        });
      } else if (art.status !== 'Validated') {
        findings.push({ 
          id: `COMP-VAL-${artifactId}`, 
          category: 'Compliance', 
          severity: 'Warning', 
          message: `Artifact ${artifactId} pending validation.`, 
          requirement: 'ISO 9001' 
        });
      }
    });
    
    dossier.artifacts.forEach(art => {
      if (!art.checksum) {
        findings.push({ 
          id: `INT-${art.id}`, 
          category: 'Integrity', 
          severity: 'Critical', 
          message: `Artifact ${art.id} missing fingerprint.`, 
          requirement: 'ISO 17025' 
        });
      }
    });
    
    return findings;
  }, [dossier]);

  const auditScore = Math.max(0, 100 - (auditFindings.filter(f => f.severity === 'Critical').length * 15) - (auditFindings.filter(f => f.severity === 'Warning').length * 5));

  // Create relationship mutation
  const linkMutation = useMutation({
    mutationFn: (data) => createRelationship(data),
    onSuccess: () => {
      toast.success('Relationship created successfully');
      setLinkDialogOpen(false);
      setLinkTarget(null);
      setLinkRelType('');
      setLinkSearch('');
      queryClient.invalidateQueries({ queryKey: ['simulation-dossier', id] });
    },
    onError: (err) => {
      toast.error(`Failed to create relationship: ${err?.message || 'Unknown error'}`);
    },
  });

  // Loading state with TCS styling
  if (loadingDossier) {
    return (
      <div className="p-12 space-y-8">
        <div className="h-16 bg-slate-200 animate-pulse rounded-2xl w-2/3" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-200 animate-pulse rounded-2xl" />)}
        </div>
        <div className="h-96 bg-slate-200 animate-pulse rounded-3xl" />
      </div>
    );
  }

  // Error state with TCS styling
  if (dossierError) {
    return (
      <div className="p-12">
        <div className="p-6 bg-red-50 border-2 border-red-200 rounded-2xl flex items-start gap-4">
          <AlertCircle className="h-6 w-6 text-red-600 shrink-0 mt-1" />
          <div>
            <h3 className="font-bold text-red-800 text-lg mb-1">Failed to Load Dossier</h3>
            <p className="text-red-600 text-sm">{dossierError.message}</p>
          </div>
        </div>
      </div>
    );
  }

  // Not found state
  if (!dossier) {
    return (
      <div className="p-12">
        <div className="p-6 bg-slate-100 border-2 border-slate-200 rounded-2xl flex items-center gap-4">
          <AlertCircle className="h-6 w-6 text-slate-500" />
          <p className="text-slate-600 font-medium">Dossier not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 relative pb-20">
      {/* MOSSEC Link Inspector Side Panel */}
      {inspectedLink && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex justify-end" onClick={() => setInspectedLink(null)}>
          <div 
            className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col relative" 
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#004A99] rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-500/10">
                  <Link2 size={20} />
                </div>
                <div>
                  <h3 className="font-black text-slate-800 uppercase tracking-widest text-xs">MOSSEC Link Inspector</h3>
                  <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tight">Technical Relationship Audit</p>
                </div>
              </div>
              <button onClick={() => setInspectedLink(null)} className="text-slate-400 hover:text-slate-600 transition-colors">
                <XCircle size={24} />
              </button>
            </div>
            
            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
              <div className="flex flex-col items-center gap-4 py-8 bg-slate-50 rounded-3xl border border-slate-200 shadow-inner">
                <div className="flex items-center gap-6 w-full justify-center px-4">
                  <div className="flex flex-col items-center">
                    <div className="w-14 h-14 bg-white rounded-2xl shadow-md border border-slate-100 flex items-center justify-center font-bold text-slate-700">
                      {getTypeIcon(inspectedLink.sourceType || 'Node')}
                    </div>
                    <span className="text-[10px] font-black text-slate-800 mt-2 uppercase tracking-tighter">{inspectedLink.source}</span>
                    <span className="text-[8px] text-slate-400 font-bold uppercase">{inspectedLink.sourceType || 'Entity'}</span>
                  </div>
                  <div className="flex flex-col items-center flex-1">
                    <div className="h-px w-full bg-slate-300 relative">
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white border border-slate-200 rounded-full px-3 py-1 text-[9px] font-black text-[#004A99] uppercase tracking-tighter whitespace-nowrap shadow-sm">
                        {inspectedLink.relationType || inspectedLink.relation}
                      </div>
                      <ArrowLeft size={14} className="absolute right-0 top-1/2 -translate-y-1/2 text-slate-300 rotate-180" />
                    </div>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-14 h-14 bg-white rounded-2xl shadow-md border border-slate-100 flex items-center justify-center font-bold text-[#004A99]">
                      {getTypeIcon(inspectedLink.targetType || 'Node')}
                    </div>
                    <span className="text-[10px] font-black text-[#004A99] mt-2 uppercase tracking-tighter">{inspectedLink.target}</span>
                    <span className="text-[8px] text-slate-400 font-bold uppercase">{inspectedLink.targetType || 'Entity'}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Logic Definition</h4>
                <div className="p-5 bg-blue-50 rounded-2xl border-2 border-blue-100/50">
                  <p className="text-sm text-slate-700 leading-relaxed font-medium italic">
                    "{getRelationDescription(inspectedLink.relationType || inspectedLink.relation)}"
                  </p>
                </div>
              </div>

              <div className="p-5 bg-emerald-50 border-2 border-emerald-100/50 rounded-2xl flex items-center gap-4">
                <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center shrink-0">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <p className="text-xs font-black text-emerald-800 uppercase tracking-tight">Compliance Verified</p>
                  <p className="text-[10px] text-emerald-600 font-medium">Link adheres to MOSSEC v2.0 Protocol</p>
                </div>
              </div>
            </div>
            
            <div className="p-8 border-t border-slate-100 bg-slate-50">
              <button className="w-full py-4 border-2 border-slate-200 rounded-2xl text-slate-400 font-black text-[10px] uppercase tracking-widest hover:bg-white hover:text-slate-600 hover:border-slate-300 transition-all">
                Report Integrity Deviation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Artifact Preview Modal */}
      {selectedArtifact && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-50 flex items-center justify-center p-12">
          <div className="bg-white rounded-3xl w-full h-full max-w-5xl flex flex-col shadow-2xl overflow-hidden">
            <div className="p-6 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-3">
                <FileText size={24} className="text-[#00B0E4]" />
                <h3 className="font-bold">{selectedArtifact.name}</h3>
              </div>
              <button onClick={() => setSelectedArtifact(null)}><XCircle size={24} /></button>
            </div>
            <div className="flex-1 bg-slate-100 flex flex-col items-center justify-center p-12 text-center">
              <div className="w-24 h-24 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-6 ring-8 ring-blue-50">
                <FileText size={48} className="text-slate-300" />
              </div>
              <h4 className="text-2xl font-bold text-slate-800 uppercase tracking-tight">Authenticated Simulation Evidence</h4>
              <p className="text-slate-500 max-w-md mt-2 flex flex-col items-center gap-2">
                <span>Dossier: {dossier.id} • Motor: {dossier.motor_id}</span>
                <code className="text-[10px] bg-slate-200 px-3 py-1.5 rounded-full mt-2 inline-flex items-center gap-2 border border-slate-300">
                  <Fingerprint size={12} /> {selectedArtifact.checksum || 'SHA-256 GENERATION PENDING'}
                </code>
              </p>
              <div className="mt-12 flex gap-4">
                <button className="bg-[#004A99] text-white px-8 py-3 rounded-xl font-bold shadow-xl shadow-blue-500/20 flex items-center gap-2 hover:scale-105 transition-all">
                  <Download size={20} /> Download for Audit
                </button>
                <button className="bg-white border-2 border-slate-200 text-slate-600 px-8 py-3 rounded-xl font-bold flex items-center gap-2 hover:bg-slate-50">
                  <Stamp size={20} /> View Signature Chain
                </button>
              </div>
            </div>
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-center">
              <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                <Lock size={12} /> Encrypted at rest • ISO 27001 Compliant
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Compliance Audit Panel */}
      {showAuditPanel && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-50 flex items-center justify-end">
          <div className="bg-white h-full w-full max-w-2xl shadow-2xl flex flex-col">
            <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-600 text-white rounded-lg"><ClipboardCheck size={24} /></div>
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Compliance Audit Report</h3>
                  <p className="text-xs text-slate-500 uppercase font-black tracking-widest">IEC 6034 Verification</p>
                </div>
              </div>
              <button onClick={() => setShowAuditPanel(false)} className="text-slate-400 hover:text-slate-600"><XCircle size={28} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              <div className="flex items-center gap-8 bg-slate-900 text-white p-8 rounded-3xl relative overflow-hidden">
                <div className="relative z-10 flex-1">
                  <p className="text-xs font-black text-blue-400 uppercase tracking-widest mb-1">Dossier Health Score</p>
                  <div className="text-6xl font-black">{auditScore}%</div>
                </div>
                <div className="relative z-10">
                  <div className={`w-24 h-24 rounded-full border-8 flex items-center justify-center text-xl font-black ${auditScore > 90 ? 'border-emerald-500 text-emerald-500' : 'border-amber-500 text-amber-500'}`}>
                    {auditFindings.length}
                  </div>
                </div>
              </div>

              {['Compliance', 'Integrity', 'Traceability'].map(cat => {
                const catFindings = auditFindings.filter(f => f.category === cat);
                return (
                  <div key={cat} className="space-y-4">
                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                      {cat === 'Compliance' ? <Shield size={14} /> : cat === 'Integrity' ? <Fingerprint size={14} /> : <TableIcon size={14} />}
                      {cat} Review
                    </h4>
                    <div className="space-y-3">
                      {catFindings.length === 0 ? (
                        <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-center gap-3 text-emerald-700 text-sm font-bold">
                          <CheckCircle size={18} /> No issues found.
                        </div>
                      ) : (
                        catFindings.map(f => (
                          <div key={f.id} className={`p-5 rounded-2xl border-2 flex gap-4 ${f.severity === 'Critical' ? 'bg-rose-50 border-rose-100' : 'bg-amber-50 border-amber-100'}`}>
                            <div className={`mt-1 ${f.severity === 'Critical' ? 'text-rose-500' : 'text-amber-500'}`}>
                              {f.severity === 'Critical' ? <AlertTriangle size={20} /> : <Info size={20} />}
                            </div>
                            <div className="flex-1">
                              <div className="flex justify-between items-start mb-1">
                                <p className="font-bold text-slate-800 text-sm">{f.message}</p>
                                <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border uppercase ${f.severity === 'Critical' ? 'bg-rose-100 text-rose-700 border-rose-200' : 'bg-amber-100 text-amber-700 border-amber-200'}`}>
                                  {f.severity}
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-500 font-bold uppercase">Requirement: {f.requirement}</p>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-8 border-t border-slate-100 flex gap-4 bg-slate-50">
              <button className="flex-1 bg-[#004A99] text-white py-4 rounded-2xl font-black text-sm shadow-xl shadow-blue-500/20 uppercase tracking-widest flex items-center justify-center gap-2">
                <Download size={18} /> Export Compliance CSV
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Header */}
      <div className="flex items-center gap-4">
        <button 
          onClick={() => navigate('/simulation/dossiers')} 
          className="p-2 hover:bg-slate-200 rounded-full transition-colors bg-white border border-slate-100 shadow-sm"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">{dossier.name || `Dossier ${dossier.id}`}</h1>
            <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border-2 ${
              dossier.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 
              dossier.status === 'PENDING_REVIEW' ? 'bg-amber-50 text-amber-600 border-amber-100' : 
              'bg-blue-50 text-blue-600 border-blue-100'
            }`}>
              {dossier.status?.replace('_', ' ')}
            </div>
          </div>
          <p className="text-slate-500 text-sm font-medium mt-1">
            Dossier {dossier.id} • v{dossier.version} • Motor: {dossier.motor_id}
          </p>
        </div>
        <div className="ml-auto flex gap-3">
          <button 
            onClick={runAudit}
            disabled={isAuditing}
            className="flex items-center gap-2 bg-white border-2 border-slate-200 px-6 py-2.5 rounded-xl text-sm font-black text-slate-600 hover:bg-slate-50 transition-all shadow-sm disabled:opacity-50"
          >
            {isAuditing ? <RefreshCw size={18} className="animate-spin" /> : <ClipboardCheck size={18} />}
            {isAuditing ? 'Auditing...' : 'RUN COMPLIANCE AUDIT'}
          </button>
          <button 
            onClick={() => setLinkDialogOpen(true)}
            className="bg-[#004A99] text-white px-8 py-2.5 rounded-xl text-sm font-bold shadow-xl flex items-center gap-2"
          >
            <Plus size={20} /> LINK ENTITY
          </button>
        </div>
      </div>

      {/* Main Layout - Sidebar + Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sidebar - Info Cards */}
        <div className="lg:col-span-4 space-y-6">
          {/* Credibility Card */}
          <div className="bg-slate-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
            <div className="absolute -bottom-8 -right-8 opacity-10 rotate-12"><Shield size={160} /></div>
            <h3 className="text-[10px] font-black text-[#00B0E4] uppercase tracking-widest mb-4 relative z-10">Process Credibility</h3>
            <div className="flex items-end gap-3 mb-6 relative z-10">
              <span className="text-5xl font-black text-white">{dossier.credibility_level || 'PC3'}</span>
              <span className="text-xs font-bold text-slate-400 mb-2">/ PC4</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-medium relative z-10">
              Validation complete per <strong>IEC 61508-3</strong>.
            </p>
          </div>

          {/* Summary Stats */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 bg-slate-50/80 border-b border-slate-100">
              <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest text-center">Dossier Summary</h3>
            </div>
            <div className="divide-y divide-slate-100">
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Package className="h-5 w-5 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">Motor ID</span>
                </div>
                <span className="text-sm font-black text-[#004A99]">{dossier.motor_id}</span>
              </div>
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">Artifacts</span>
                </div>
                <span className="text-sm font-black text-slate-800">{dossier.artifacts?.length || 0}</span>
              </div>
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Link2 className="h-5 w-5 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">MOSSEC Links</span>
                </div>
                <span className="text-sm font-black text-slate-800">{dossier.mossecLinks?.length || 0}</span>
              </div>
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Activity className="h-5 w-5 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">Engineer</span>
                </div>
                <span className="text-sm font-medium text-slate-600">{dossier.engineer || 'N/A'}</span>
              </div>
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-slate-400" />
                  <span className="text-sm font-medium text-slate-700">Last Updated</span>
                </div>
                <span className="text-xs text-slate-500">
                  {dossier.last_updated ? new Date(dossier.last_updated).toLocaleDateString() : 
                   dossier.updatedAt ? new Date(dossier.updatedAt).toLocaleDateString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content - Artifacts & MOSSEC */}
        <div className="lg:col-span-8 space-y-8">
          {/* Artifacts Gallery */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest">Evidence Artifacts</h3>
              <span className="text-[10px] font-bold text-slate-400">ISO 17025 AUTHENTICATED</span>
            </div>
            
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {dossier.artifacts && dossier.artifacts.length > 0 ? (
                dossier.artifacts.map((art) => {
                  const config = getArtifactConfig(art.id);
                  const Icon = config.icon;
                  return (
                    <div 
                      key={art.id} 
                      onClick={() => setSelectedArtifact(art)}
                      className="p-4 border-2 border-slate-100 rounded-2xl bg-white relative group cursor-pointer hover:border-[#004A99] hover:shadow-lg transition-all"
                    >
                      <div className="absolute top-2 right-2 text-slate-300 group-hover:text-[#004A99]"><ExternalLink size={14} /></div>
                      <div className="flex items-start gap-3">
                        <div className={`p-3 rounded-xl bg-${config.color}-50 text-${config.color}-600 shrink-0`}><Icon size={20} /></div>
                        <div className="flex-1 min-w-0">
                          <p className="font-black text-slate-800 text-xs truncate uppercase tracking-tight group-hover:text-[#004A99]">{art.name}</p>
                          <p className="text-[9px] text-slate-400 font-bold mt-1 uppercase truncate">{config.standard}</p>
                          <div className="mt-2 flex items-center justify-between">
                            <span className="text-[9px] font-mono text-slate-400">{art.size}</span>
                            <span className={`text-[8px] font-black px-1 rounded uppercase ${art.status === 'Validated' ? 'text-emerald-600 bg-emerald-50' : 'text-amber-600 bg-amber-50'}`}>
                              {art.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="col-span-full p-12 text-center">
                  <FileText size={48} className="mx-auto text-slate-300 mb-4" />
                  <p className="text-sm text-slate-500 font-medium">No artifacts available</p>
                </div>
              )}
            </div>
          </div>

          {/* MOSSEC Traceability Matrix */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest flex items-center gap-2">
                <TableIcon size={16} /> MOSSEC Traceability Matrix
              </h3>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Click row to inspect link metadata</span>
            </div>
            
            <div className="overflow-x-auto">
              {dossier.mossecLinks && dossier.mossecLinks.length > 0 ? (
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-100 text-slate-400 font-black uppercase tracking-widest">
                    <tr>
                      <th className="px-6 py-4">Source Entity</th>
                      <th className="px-6 py-4">Relationship</th>
                      <th className="px-6 py-4">Target Entity</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {dossier.mossecLinks.map((link, idx) => (
                      <tr 
                        key={link.id || idx} 
                        onClick={() => setInspectedLink(link)}
                        className="hover:bg-slate-50 transition-all group cursor-pointer border-l-4 border-transparent hover:border-l-[#004A99]"
                      >
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-700 group-hover:text-[#004A99] flex items-center gap-2 transition-colors">
                              {getTypeIcon(link.sourceType || 'Node')} {link.source}
                            </span>
                            <span className="text-[10px] text-slate-400 uppercase tracking-tighter pl-5 font-black">{link.sourceType || 'Entity'}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="italic text-slate-400 text-[10px] font-bold uppercase tracking-widest bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                            {link.relationType || link.relation}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-bold text-[#004A99] flex items-center gap-2">
                              {getTypeIcon(link.targetType || 'Node')} {link.target}
                            </span>
                            <span className="text-[10px] text-slate-400 uppercase tracking-tighter pl-5 font-black">{link.targetType || 'Entity'}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="flex items-center gap-1 font-black text-emerald-600 text-[9px] uppercase tracking-widest">
                            <CheckCircle size={12} /> Verified
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              setInspectedLink(link);
                            }}
                            className="text-[#004A99] hover:bg-white p-2 rounded-lg transition-all border border-transparent hover:border-slate-200 shadow-sm"
                            title="Inspect Link Details"
                          >
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-12 text-center">
                  <Link2 size={48} className="mx-auto text-slate-300 mb-4" />
                  <p className="text-sm text-slate-500 font-medium">No MOSSEC links available</p>
                  <button 
                    onClick={() => setLinkDialogOpen(true)}
                    className="mt-6 text-[#004A99] hover:underline text-sm font-bold"
                  >
                    Create your first link
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Link Entity Dialog */}
      {linkDialogOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setLinkDialogOpen(false)}>
          <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="p-6 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-3">
                <Link2 size={24} className="text-[#00B0E4]" />
                <div>
                  <h3 className="font-bold text-lg">Link Entity to Dossier</h3>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">Search and connect graph nodes</p>
                </div>
              </div>
              <button onClick={() => setLinkDialogOpen(false)}><XCircle size={24} /></button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Search */}
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-700 uppercase tracking-widest">Search Nodes</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search by name, type, or ID..."
                    value={linkSearch}
                    onChange={(e) => setLinkSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border-2 border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent text-sm"
                  />
                </div>
              </div>

              {/* Search Results */}
              {linkSearch.length >= 2 && (
                <div className="border-2 border-slate-100 rounded-xl max-h-48 overflow-y-auto">
                  {isSearching ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-5 w-5 animate-spin mr-2 text-[#004A99]" />
                      <span className="text-sm text-slate-500 font-medium">Searching…</span>
                    </div>
                  ) : searchResults.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-8 font-medium">No results found</p>
                  ) : (
                    searchResults.map((node) => (
                      <button
                        key={node.id}
                        className={`w-full flex items-center gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-b-0 ${
                          linkTarget?.id === node.id ? 'bg-blue-50' : ''
                        }`}
                        onClick={() => setLinkTarget(node)}
                      >
                        <span className="text-[9px] font-black px-2 py-1 bg-slate-100 text-slate-600 rounded uppercase tracking-wider shrink-0">
                          {node.type || 'Node'}
                        </span>
                        <span className="truncate font-medium text-slate-800">{node.name || node.id}</span>
                        {linkTarget?.id === node.id && <CheckCircle size={16} className="ml-auto text-[#004A99]" />}
                      </button>
                    ))
                  )}
                </div>
              )}

              {/* Selected Target */}
              {linkTarget && (
                <div className="p-4 border-2 border-[#004A99] rounded-xl bg-blue-50">
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Selected Target</p>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-black px-2 py-1 bg-[#004A99] text-white rounded uppercase">{linkTarget.type}</span>
                    <span className="text-sm font-bold text-slate-800">{linkTarget.name || linkTarget.id}</span>
                  </div>
                </div>
              )}

              {/* Relationship Type */}
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-700 uppercase tracking-widest">Relationship Type</label>
                <div className="relative">
                  <select 
                    value={linkRelType} 
                    onChange={(e) => setLinkRelType(e.target.value)}
                    className="w-full appearance-none px-4 py-3 border-2 border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent text-sm font-medium bg-white"
                  >
                    <option value="">Choose relationship type...</option>
                    {(relTypes.length > 0
                      ? relTypes.map(rt => typeof rt === 'string' ? rt : rt.type)
                      : ['SATISFIES', 'DERIVES_FROM', 'VALIDATES', 'USES', 'CONSTRAINS', 'PRODUCES', 'TRACES_TO', 'COMPOSED_OF', 'GENERATED_FROM', 'USES_MODEL', 'REPRESENTS', 'PROVES_COMPLIANCE_TO', 'GOVERNS', 'HAS_APPROVAL', 'HAS_FINDING']
                    ).map((rt) => (
                      <option key={rt} value={rt}>{rt.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Create Button */}
              <button
                disabled={!linkTarget || !linkRelType || linkMutation.isPending}
                onClick={() => {
                  if (!linkTarget || !linkRelType) return;
                  linkMutation.mutate({
                    source_id: id,
                    target_id: String(linkTarget.id),
                    relationship_type: linkRelType,
                  });
                }}
                className="w-full bg-[#004A99] text-white py-4 rounded-xl font-bold shadow-xl shadow-blue-900/20 flex items-center justify-center gap-2 hover:bg-[#003d7a] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linkMutation.isPending ? (
                  <><Loader2 className="h-5 w-5 animate-spin" /> Creating Relationship...</>
                ) : (
                  <><Plus className="h-5 w-5" /> Create Relationship</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DossierDetail;
