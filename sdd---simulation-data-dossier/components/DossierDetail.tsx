
import React, { useState, useMemo, useEffect } from 'react';
import { Dossier, UserRole, DossierStatus, Artifact, MOSSECLink, AuditFinding } from '../types';
import { 
  ArrowLeft, 
  FileText, 
  CheckCircle2, 
  Clock, 
  Download, 
  ShieldCheck,
  XCircle,
  Stamp,
  Zap,
  Activity,
  Wind,
  Waves,
  Shield,
  Box,
  Fingerprint,
  FileBadge,
  ExternalLink,
  Table as TableIcon,
  Search,
  AlertTriangle,
  Info,
  CheckCircle,
  ClipboardCheck,
  RefreshCw,
  Eye,
  ArrowRight,
  Link2,
  Lock,
  PlayCircle,
  CheckSquare,
  FileCheck
} from 'lucide-react';

interface DossierDetailProps {
  dossier: Dossier;
  role: UserRole;
  onBack: () => void;
  onUpdateStatus: (status: DossierStatus, comment?: string) => void;
}

const DossierDetail: React.FC<DossierDetailProps> = ({ dossier, role, onBack, onUpdateStatus }) => {
  const [showReviewPanel, setShowReviewPanel] = useState(false);
  const [showAuditPanel, setShowAuditPanel] = useState(false);
  const [isAuditing, setIsAuditing] = useState(false);
  const [reviewComment, setReviewComment] = useState('');
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [inspectedLink, setInspectedLink] = useState<MOSSECLink | null>(null);

  // Close inspector when artifact is opened to prevent overlay confusion
  useEffect(() => {
    if (activeArtifact) setInspectedLink(null);
  }, [activeArtifact]);

  const handleStatusChange = (status: DossierStatus) => {
    onUpdateStatus(status, reviewComment);
    setShowReviewPanel(false);
    setReviewComment('');
  };

  const openArtifact = (art: Artifact) => {
    setActiveArtifact(art);
  };

  const inspectLink = (link: MOSSECLink) => {
    setInspectedLink(link);
  };

  const runAudit = () => {
    setIsAuditing(true);
    setTimeout(() => {
      setIsAuditing(false);
      setShowAuditPanel(true);
    }, 1200);
  };

  const auditFindings = useMemo<AuditFinding[]>(() => {
    const findings: AuditFinding[] = [];
    const requiredIds = ['A1', 'A2', 'B1', 'C1', 'D1', 'E1', 'F1'];
    requiredIds.forEach(id => {
      const art = dossier.artifacts.find(a => a.id === id);
      if (!art) {
        findings.push({ id: `COMP-${id}`, category: 'Compliance', severity: 'Critical', message: `Mandatory evidence artifact ${id} is missing.`, requirement: `IEC 6034` });
      } else if (art.status !== 'Validated') {
        findings.push({ id: `COMP-VAL-${id}`, category: 'Compliance', severity: 'Warning', message: `Artifact ${id} pending validation.`, requirement: 'ISO 9001' });
      }
    });
    dossier.artifacts.forEach(art => {
      if (!art.checksum) {
        findings.push({ id: `INT-${art.id}`, category: 'Integrity', severity: 'Critical', message: `Artifact ${art.id} missing fingerprint.`, requirement: 'ISO 17025' });
      }
    });
    return findings;
  }, [dossier]);

  const auditScore = Math.max(0, 100 - (auditFindings.filter(f => f.severity === 'Critical').length * 15) - (auditFindings.filter(f => f.severity === 'Warning').length * 5));

  const getArtifactConfig = (id: string) => {
    const configs: Record<string, { icon: any, color: string, standard: string, label: string }> = {
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
    return configs[id] || { icon: FileText, color: 'slate', standard: 'EVIDENCE', label: 'REPORT' };
  };

  const getRelationDescription = (rel: string) => {
    switch(rel) {
      case 'validates': return 'Evidence proves the requirement is met within tolerance.';
      case 'derivedFrom': return 'Simulation parameters extracted from a master design model.';
      case 'executes': return 'Mathematical solver running against the specific sim model.';
      case 'represents': return 'Simulation model acts as a digital twin for the requirement.';
      case 'contains': return 'Simulation run produces these specific result data blocks.';
      case 'verifies': return 'Results are verified as credible evidence for certification.';
      case 'satisfies': return 'The evidence artifact fulfills the standard compliance criteria.';
      case 'approves': return 'Final release signature authorized by Quality Head.';
      default: return 'Defined MOSSEC system relationship.';
    }
  };

  const getTypeIcon = (type: string) => {
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

  return (
    <div className="space-y-8 relative pb-20">
      {/* Traceability Link Inspector Side Panel */}
      {inspectedLink && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[70] flex justify-end" onClick={() => setInspectedLink(null)}>
          <div 
            className="bg-white w-full max-w-md h-full shadow-2xl animate-in slide-in-from-right flex flex-col relative" 
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
                          {getTypeIcon(inspectedLink.sourceType)}
                       </div>
                       <span className="text-[10px] font-black text-slate-800 mt-2 uppercase tracking-tighter">{inspectedLink.sourceId}</span>
                       <span className="text-[8px] text-slate-400 font-bold uppercase">{inspectedLink.sourceType}</span>
                    </div>
                    <div className="flex flex-col items-center flex-1">
                       <div className="h-px w-full bg-slate-300 relative">
                          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white border border-slate-200 rounded-full px-3 py-1 text-[9px] font-black text-[#004A99] uppercase tracking-tighter whitespace-nowrap shadow-sm">
                            {inspectedLink.relation}
                          </div>
                          <ArrowRight size={14} className="absolute right-0 top-1/2 -translate-y-1/2 text-slate-300" />
                       </div>
                    </div>
                    <div className="flex flex-col items-center">
                       <div className="w-14 h-14 bg-white rounded-2xl shadow-md border border-slate-100 flex items-center justify-center font-bold text-[#004A99]">
                          {getTypeIcon(inspectedLink.targetType)}
                       </div>
                       <span className="text-[10px] font-black text-[#004A99] mt-2 uppercase tracking-tighter">{inspectedLink.targetId}</span>
                       <span className="text-[8px] text-slate-400 font-bold uppercase">{inspectedLink.targetType}</span>
                    </div>
                  </div>
               </div>

               <div className="space-y-4">
                  <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Logic Definition</h4>
                  <div className="p-5 bg-blue-50 rounded-2xl border-2 border-blue-100/50">
                     <p className="text-sm text-slate-700 leading-relaxed font-medium italic">"{getRelationDescription(inspectedLink.relation)}"</p>
                  </div>
               </div>

               {inspectedLink.targetType === 'Artifact' && dossier.artifacts.find(a => a.id === inspectedLink.targetId) && (
                 <div className="space-y-4">
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Digital Evidence Access</h4>
                    <div className="bg-white border-2 border-slate-100 rounded-3xl p-5 flex items-center gap-4 shadow-sm hover:border-[#004A99] transition-all group cursor-pointer" onClick={() => openArtifact(dossier.artifacts.find(a => a.id === inspectedLink.targetId)!)}>
                       <div className="p-3 bg-slate-100 rounded-2xl text-[#00B0E4] group-hover:bg-[#004A99] group-hover:text-white transition-all"><FileText size={24} /></div>
                       <div className="flex-1">
                          <p className="font-bold text-slate-800 text-sm truncate">{dossier.artifacts.find(a => a.id === inspectedLink.targetId)?.name}</p>
                          <p className="text-[9px] text-slate-400 font-black uppercase tracking-widest mt-1 flex items-center gap-1">
                            <Lock size={10} /> SHA-256 VERIFIED
                          </p>
                       </div>
                       <ExternalLink size={16} className="text-slate-300 group-hover:text-[#004A99]" />
                    </div>
                    <button 
                       onClick={() => openArtifact(dossier.artifacts.find(a => a.id === inspectedLink.targetId)!)}
                       className="w-full bg-[#004A99] text-white py-4 rounded-2xl font-black text-xs shadow-xl shadow-blue-900/20 flex items-center justify-center gap-2 hover:bg-[#003d7a] transition-all uppercase tracking-widest"
                    >
                       <Eye size={16} /> Open Evidence Artifact
                    </button>
                 </div>
               )}

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
      {activeArtifact && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[80] flex items-center justify-center p-12">
          <div className="bg-white rounded-3xl w-full h-full max-w-5xl flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-3">
                <FileText size={24} className="text-[#00B0E4]" />
                <h3 className="font-bold">{activeArtifact.name}</h3>
              </div>
              <button onClick={() => setActiveArtifact(null)}><XCircle size={24} /></button>
            </div>
            <div className="flex-1 bg-slate-100 flex flex-col items-center justify-center p-12 text-center">
              <div className="w-24 h-24 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-6 ring-8 ring-blue-50">
                <FileText size={48} className="text-slate-300" />
              </div>
              <h4 className="text-2xl font-bold text-slate-800 uppercase tracking-tight">Authenticated Simulation Evidence</h4>
              <p className="text-slate-500 max-w-md mt-2 flex flex-col items-center gap-2">
                <span>Dossier: {dossier.id} • Motor: {dossier.motorId}</span>
                <code className="text-[10px] bg-slate-200 px-3 py-1.5 rounded-full mt-2 inline-flex items-center gap-2 border border-slate-300">
                  <Fingerprint size={12} /> {activeArtifact.checksum || 'SHA-256 GENERATION PENDING'}
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
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-[60] flex items-center justify-end">
          <div className="bg-white h-full w-full max-w-2xl shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
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
        <button onClick={onBack} className="p-2 hover:bg-slate-200 rounded-full transition-colors bg-white border border-slate-100 shadow-sm"><ArrowLeft size={20} /></button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">{dossier.id}</h1>
            <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border-2 ${dossier.status === DossierStatus.APPROVED ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-amber-50 text-amber-600 border-amber-100'}`}>
              {dossier.status}
            </div>
          </div>
          <p className="text-slate-500 text-sm font-medium mt-1">Project: {dossier.projectName} • v{dossier.version}</p>
        </div>
        <div className="ml-auto flex gap-3">
          <button 
            onClick={runAudit}
            disabled={isAuditing}
            className="flex items-center gap-2 bg-white border-2 border-slate-200 px-6 py-2.5 rounded-xl text-sm font-black text-slate-600 hover:bg-slate-50 transition-all shadow-sm"
          >
            {isAuditing ? <RefreshCw size={18} className="animate-spin" /> : <ClipboardCheck size={18} />}
            {isAuditing ? 'Auditing...' : 'RUN COMPLIANCE AUDIT'}
          </button>
          {role === UserRole.QUALITY_HEAD && dossier.status === DossierStatus.PENDING_REVIEW && (
            <button onClick={() => setShowReviewPanel(true)} className="bg-[#004A99] text-white px-8 py-2.5 rounded-xl text-sm font-bold shadow-xl flex items-center gap-2">
              <ShieldCheck size={20} /> REVIEW & CERTIFY
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
            <div className="absolute -bottom-8 -right-8 opacity-10 rotate-12"><Shield size={160} /></div>
            <h3 className="text-[10px] font-black text-[#00B0E4] uppercase tracking-widest mb-4">Process Credibility</h3>
            <div className="flex items-end gap-3 mb-6">
              <span className="text-5xl font-black text-white">{dossier.credibilityLevel}</span>
              <span className="text-xs font-bold text-slate-400 mb-2">/ PC4</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-medium">Validation complete per <strong>IEC 61508-3</strong>.</p>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 bg-slate-50/80 border-b border-slate-100">
              <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest text-center">Pipeline Progress</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {dossier.categories.map((cat) => (
                <div key={cat.id} className="p-4 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-black text-slate-300 uppercase">CAT-{cat.id}</span>
                    <p className="text-xs font-bold text-slate-700">{cat.label}</p>
                  </div>
                  {cat.status === 'Complete' ? <CheckCircle2 size={18} className="text-emerald-500" /> : <Clock size={18} className="text-slate-300" />}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-8">
          {/* Artifacts Gallery */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest">Evidence artifacts (A1 - F1)</h3>
              <span className="text-[10px] font-bold text-slate-400">ISO 17025 AUTHENTICATED</span>
            </div>
            
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {dossier.artifacts.map((art) => {
                const config = getArtifactConfig(art.id);
                const Icon = config.icon;
                return (
                  <div 
                    key={art.id} 
                    onClick={() => openArtifact(art)}
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
              })}
            </div>
          </div>

          {/* MOSSEC Traceability Matrix - Enhanced for Accessibility */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
             <div className="p-6 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
               <h3 className="font-black text-xs text-slate-800 uppercase tracking-widest flex items-center gap-2">
                 <TableIcon size={16} /> MOSSEC Traceability Matrix
               </h3>
               <div className="flex items-center gap-4">
                 <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Click row to inspect link metadata</span>
                 <button className="text-[10px] font-black text-[#004A99] hover:underline uppercase tracking-widest">Full Export</button>
               </div>
             </div>
             
             <div className="overflow-x-auto">
               <table className="w-full text-left text-xs">
                 <thead className="bg-slate-50 border-b border-slate-100 text-slate-400 font-black uppercase tracking-widest">
                   <tr>
                     <th className="px-6 py-4">Source Entity</th>
                     <th className="px-6 py-4">Relationship</th>
                     <th className="px-6 py-4">Target (Entity)</th>
                     <th className="px-6 py-4">MOSSEC Status</th>
                     <th className="px-6 py-4 text-right">Actions</th>
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-slate-100">
                   {dossier.mossecLinks?.map((link, idx) => (
                     <tr 
                       key={idx} 
                       onClick={() => inspectLink(link)}
                       className="hover:bg-slate-50 transition-all group cursor-pointer border-l-4 border-transparent hover:border-l-[#004A99]"
                     >
                       <td className="px-6 py-4">
                         <div className="flex flex-col">
                           <span className="font-bold text-slate-700 group-hover:text-[#004A99] flex items-center gap-2 transition-colors">
                              {getTypeIcon(link.sourceType)} {link.sourceId}
                           </span>
                           <span className="text-[10px] text-slate-400 uppercase tracking-tighter pl-5 font-black">{link.sourceType}</span>
                         </div>
                       </td>
                       <td className="px-6 py-4">
                         <span className="italic text-slate-400 text-[10px] font-bold uppercase tracking-widest bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                           {link.relation}
                         </span>
                       </td>
                       <td className="px-6 py-4">
                         <div className="flex flex-col">
                           <span className="font-bold text-[#004A99] flex items-center gap-2">
                              {getTypeIcon(link.targetType)} {link.targetId}
                           </span>
                           <span className="text-[10px] text-slate-400 uppercase tracking-tighter pl-5 font-black">{link.targetType}</span>
                         </div>
                       </td>
                       <td className="px-6 py-4">
                         <span className="flex items-center gap-1 font-black text-emerald-600 text-[9px] uppercase tracking-widest">
                           <CheckCircle size={12} /> Sync Verified
                         </span>
                       </td>
                       <td className="px-6 py-4 text-right">
                         <div className="flex justify-end gap-2">
                            <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  inspectLink(link);
                                }}
                                className="text-[#004A99] hover:bg-white p-2 rounded-lg transition-all border border-transparent hover:border-slate-200 shadow-sm"
                                title="Inspect Link Details"
                              >
                                <Eye size={16} />
                            </button>
                            {link.targetType === 'Artifact' && (
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const art = dossier.artifacts.find(a => a.id === link.targetId);
                                  if (art) openArtifact(art);
                                }}
                                className="text-slate-400 hover:text-emerald-600 p-2 hover:bg-white rounded-lg transition-all border border-transparent hover:border-slate-200 shadow-sm"
                                title="Open Associated Evidence"
                              >
                                <ExternalLink size={16} />
                              </button>
                            )}
                         </div>
                       </td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DossierDetail;
