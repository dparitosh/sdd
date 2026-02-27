
import React, { useState } from 'react';
import { UserRole, Dossier, DossierStatus } from './types';
import Sidebar from './components/Sidebar';
import DashboardEngineer from './components/DashboardEngineer';
import ProductSpecs from './components/ProductSpecs';
import SimulationWorkspace from './components/SimulationWorkspace';
import QualityDashboard from './components/QualityDashboard';
import MyDossiers from './components/MyDossiers';
import DossierDetail from './components/DossierDetail';
import Chatbot from './components/Chatbot';
import { 
  LogOut, 
  Bell, 
  ChevronDown, 
  UserCircle2, 
  RotateCw,
  Search
} from 'lucide-react';
import { MOCK_DOSSIERS } from './constants';

const App: React.FC = () => {
  const [role, setRole] = useState<UserRole | null>(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dossiers, setDossiers] = useState<Dossier[]>(MOCK_DOSSIERS);
  const [selectedDossierId, setSelectedDossierId] = useState<string | null>(null);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const handleDossierSelect = (id: string) => {
    setSelectedDossierId(id);
    setActiveTab('dossier_detail');
  };

  const handleBackToList = () => {
    setSelectedDossierId(null);
    setActiveTab(role === UserRole.SIMULATION_ENGINEER ? 'dossiers' : 'approvals');
  };

  const updateDossierStatus = (id: string, status: DossierStatus, comment?: string) => {
    setDossiers(prev => prev.map(d => {
      if (d.id === id) {
        const newLog = {
          status,
          timestamp: new Date().toISOString().split('T')[0],
          reviewer: role === UserRole.QUALITY_HEAD ? 'Maria Garcia' : 'Alex Rivera',
          comment
        };
        return { 
          ...d, 
          status, 
          lastUpdated: newLog.timestamp,
          decisionHistory: [...(d.decisionHistory || []), newLog]
        };
      }
      return d;
    }));
  };

  if (!role) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 bg-[url('https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center">
        <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-md"></div>
        <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10 relative z-10 border border-white/20 overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-[#004A99]"></div>
          <div className="flex flex-col items-center mb-10">
            <div className="flex items-center gap-2 mb-6">
               <div className="w-12 h-12 bg-[#004A99] rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                 <span className="text-white font-black text-xl tracking-tighter">TCS</span>
               </div>
               <div className="h-8 w-px bg-slate-200"></div>
               <span className="text-slate-800 font-black text-sm uppercase tracking-widest">Simulation Digital Thread</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-800 text-center leading-tight">Simulation Data Dossier Application</h1>
            <p className="text-slate-500 text-xs mt-3 text-center uppercase font-black tracking-widest opacity-60">Enterprise Compliance System</p>
          </div>

          <div className="space-y-4">
            <button
              onClick={() => { setRole(UserRole.SIMULATION_ENGINEER); setActiveTab('dashboard'); }}
              className="w-full flex flex-col p-5 border-2 border-slate-100 rounded-2xl hover:border-[#004A99] hover:bg-blue-50/50 transition-all group text-left"
            >
              <div className="flex justify-between items-center w-full mb-1">
                <span className="font-bold text-slate-800 group-hover:text-[#004A99]">Simulation Engineer</span>
                <div className="w-6 h-6 rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-[#004A99] group-hover:text-white transition-colors">
                  <ChevronDown className="-rotate-90" size={14} />
                </div>
              </div>
              <span className="text-xs text-slate-400">Run solvers, verify artifacts, and manage MOSSEC traces.</span>
            </button>

            <button
              onClick={() => { setRole(UserRole.QUALITY_HEAD); setActiveTab('approvals'); }}
              className="w-full flex flex-col p-5 border-2 border-slate-100 rounded-2xl hover:border-[#004A99] hover:bg-blue-50/50 transition-all group text-left"
            >
              <div className="flex justify-between items-center w-full mb-1">
                <span className="font-bold text-slate-800 group-hover:text-[#004A99]">Quality Head</span>
                <div className="w-6 h-6 rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-[#004A99] group-hover:text-white transition-colors">
                  <ChevronDown className="-rotate-90" size={14} />
                </div>
              </div>
              <span className="text-xs text-slate-400">Perform compliance audits and authorize release.</span>
            </button>
          </div>

          <div className="mt-10 pt-6 border-t border-slate-100 flex justify-between items-center text-[9px] text-slate-400 font-black uppercase tracking-widest">
            <span>v4.1.0-ENTERPRISE</span>
            <span>Compliance: ISO 17025 / MOSSEC</span>
          </div>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    const selectedDossier = dossiers.find(d => d.id === selectedDossierId);

    switch (activeTab) {
      case 'dashboard': return <DashboardEngineer dossiers={dossiers} />;
      case 'specs': return <ProductSpecs />;
      case 'workspace': return <SimulationWorkspace />;
      case 'dossiers': return <MyDossiers dossiers={dossiers} onSelectDossier={handleDossierSelect} />;
      case 'approvals': return <QualityDashboard dossiers={dossiers} onSelectDossier={handleDossierSelect} />;
      case 'dossier_detail': 
        return selectedDossier ? 
          <DossierDetail 
            dossier={selectedDossier} 
            role={role} 
            onBack={handleBackToList} 
            onUpdateStatus={(status, comment) => updateDossierStatus(selectedDossier.id, status, comment)}
          /> : 
          <DashboardEngineer dossiers={dossiers} />;
      case 'reports': return (
        <div className="p-20 text-center bg-white rounded-2xl border-2 border-dashed border-slate-200">
           <RotateCw className="mx-auto text-slate-300 animate-spin-slow mb-4" size={48} />
           <h3 className="text-slate-500 font-bold">Generating Live Analytics...</h3>
           <p className="text-slate-400 text-sm">Aggregating cross-dossier CSV reports for regulatory submission.</p>
        </div>
      );
      default: return <DashboardEngineer dossiers={dossiers} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar role={role} activeTab={activeTab} setActiveTab={(tab) => {
        setActiveTab(tab);
        setSelectedDossierId(null);
      }} dossiers={dossiers} />
      
      <main className="flex-1 ml-64 min-h-screen flex flex-col">
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#004A99]" size={16} />
              <input 
                type="text" 
                placeholder="Search dossiers, requirements, or motor IDs..." 
                className="pl-10 pr-4 py-2 bg-slate-100 border-none rounded-full text-sm w-80 focus:ring-2 focus:ring-[#004A99] focus:bg-white transition-all outline-none" 
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <button 
              onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              className="relative p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-white"></span>
            </button>

            <div className="flex items-center gap-3 border-l border-slate-200 pl-6">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold text-slate-800">
                  {role === UserRole.SIMULATION_ENGINEER ? 'Alex Rivera' : 'Maria Garcia'}
                </p>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                  {role.replace('_', ' ')}
                </p>
              </div>
              <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
                <UserCircle2 size={24} className="text-slate-500" />
              </div>
              <button 
                onClick={() => setRole(null)}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors ml-2"
                title="Switch Role / Logout"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </header>

        <div className="p-8 max-w-[1600px] w-full mx-auto animate-in fade-in slide-in-from-bottom-2 duration-500">
          {renderContent()}
        </div>

        <Chatbot context={{ 
          activeRole: role, 
          motorId: 'HDIM-250-A', 
          dossiers: dossiers,
          lastSimulation: 'Thermal Analysis (IEC 6034 compliant)' 
        }} />
      </main>
    </div>
  );
};

export default App;
