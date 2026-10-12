import React, { useState } from 'react';
import { 
  Boxes, UploadCloud, Trophy, Grid3X3, Search, SlidersHorizontal, ArrowLeftRight, Activity 
} from 'lucide-react';

import UploadPage from './pages/UploadPage';
import LeaderboardPage from './pages/LeaderboardPage';
import HeatmapPage from './pages/HeatmapPage';
import LookupPage from './pages/LookupPage';
import WhatIfPage from './pages/WhatIfPage';
import ReslotPage from './pages/ReslotPage';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [activeStrategy, setActiveStrategy] = useState('Forecast + Affinity');

  const tabs = [
    { id: 'upload', label: '1. Ingestion & Audit', icon: UploadCloud },
    { id: 'leaderboard', label: '2. Leaderboard', icon: Trophy },
    { id: 'heatmap', label: '3. Warehouse Heatmap', icon: Grid3X3 },
    { id: 'lookup', label: '4. Product Lookup', icon: Search },
    { id: 'whatif', label: '5. What-If Simulator', icon: SlidersHorizontal },
    { id: 'reslot', label: '6. Re-slotting Plan', icon: ArrowLeftRight },
  ];

  const handleApplyStrategy = async (strategyName) => {
    setActiveStrategy(strategyName);
    const key = strategyName === 'Optimal (Hungarian)'
      ? 'optimal'
      : strategyName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    try {
      await fetch(`${API_BASE}/optimize?strategy=${key}`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-50 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Boxes className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">SlotIQ</h1>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/60">
                  AI Slotting Engine
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">Bipartite Matching • Lift Affinity • Holt Forecast</p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-3 font-mono text-xs">
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">Active Engine:</span>
              <span className="text-emerald-400 font-bold">{activeStrategy}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Subnav Tabs */}
      <nav className="border-b border-slate-800/60 bg-slate-950/40 px-6">
        <div className="max-w-7xl mx-auto flex overflow-x-auto space-x-1 py-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main Content View */}
      <main className="max-w-7xl mx-auto w-full p-6 flex-1">
        {activeTab === 'upload' && <UploadPage apiBase={API_BASE} />}
        {activeTab === 'leaderboard' && <LeaderboardPage apiBase={API_BASE} onSelectStrategy={handleApplyStrategy} />}
        {activeTab === 'heatmap' && <HeatmapPage apiBase={API_BASE} />}
        {activeTab === 'lookup' && <LookupPage apiBase={API_BASE} />}
        {activeTab === 'whatif' && <WhatIfPage apiBase={API_BASE} />}
        {activeTab === 'reslot' && <ReslotPage apiBase={API_BASE} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-4 px-6 text-center text-xs font-mono text-slate-500">
        SlotIQ • 2.5-hr Hackathon Optimization Engine • Deterministic Seed 42 • Pure Python Engine + React Vite
      </footer>
    </div>
  );
}
