import React from 'react';
import { useAppStore } from '../stores/useAppStore';
import { ShieldAlert, Cpu, Database, Activity, Mic, MicOff } from 'lucide-react';

export const Header: React.FC = () => {
  const { health, wsConnected, isListening, toggleVoiceListening, triggerEmergencyStop } = useAppStore();

  return (
    <header className="h-14 border-b border-navy-800 bg-obsidian-900/90 backdrop-blur px-5 flex items-center justify-between select-none z-20">
      {/* Brand Identity */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-reeta-cyan to-reeta-blue flex items-center justify-center shadow-lg shadow-reeta-cyan/20">
          <span className="font-mono font-bold text-obsidian-950 text-sm">R</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold tracking-wider text-slate-100 text-sm">REETA</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-reeta-cyan/10 text-reeta-cyan border border-reeta-cyan/30">
              v1.0 OS
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-sans leading-none">Responsive Executive Engine</p>
        </div>
      </div>

      {/* Telemetry Status Indicators */}
      <div className="flex items-center gap-4 text-xs font-mono">
        {/* Model Provider */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-navy-900 border border-navy-800 text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-reeta-cyan" />
          <span>{health?.active_provider?.toUpperCase() || 'HYBRID LLM'}</span>
        </div>

        {/* Database */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-navy-900 border border-navy-800 text-slate-300">
          <Database className={`w-3.5 h-3.5 ${health?.database === 'connected' ? 'text-reeta-success' : 'text-reeta-danger'}`} />
          <span>PGVECTOR</span>
        </div>

        {/* Event Bus */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-navy-900 border border-navy-800 text-slate-300">
          <Activity className={`w-3.5 h-3.5 ${wsConnected ? 'text-reeta-cyan' : 'text-slate-500'}`} />
          <span>{wsConnected ? 'LIVE STREAM' : 'CONNECTING'}</span>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-3">
        {/* Voice Toggle */}
        <button
          onClick={toggleVoiceListening}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isListening
              ? 'bg-reeta-cyan/20 text-reeta-cyan border border-reeta-cyan/40 shadow-sm shadow-reeta-cyan/30 animate-pulse'
              : 'bg-navy-900 text-slate-300 hover:text-slate-100 border border-navy-800 hover:border-navy-700'
          }`}
        >
          {isListening ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
          <span>{isListening ? 'LISTENING' : 'VOICE OFF'}</span>
        </button>

        {/* Emergency Stop Kill Switch */}
        <button
          onClick={triggerEmergencyStop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reeta-danger/10 hover:bg-reeta-danger/20 text-reeta-danger border border-reeta-danger/40 transition-colors text-xs font-semibold"
          title="Emergency Stop: Abort all active tasks and child processes immediately"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>KILL SWITCH</span>
        </button>
      </div>
    </header>
  );
};
