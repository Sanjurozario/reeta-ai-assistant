import React from 'react';
import { useAppStore } from '../stores/useAppStore';
import { ShieldAlert, Cpu, Database, Activity, Mic, MicOff, Sparkles } from 'lucide-react';

interface HeaderProps {
  onTriggerStartup?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onTriggerStartup }) => {
  const { health, wsConnected, isListening, toggleVoiceListening, triggerEmergencyStop } = useAppStore();

  return (
    <header className="h-14 border-b border-navy-800/80 bg-[#050814]/80 backdrop-blur-xl px-5 flex items-center justify-between select-none z-20 transition-all">
      {/* Brand Identity with Awakening Spark */}
      <div className="flex items-center gap-3">
        <button
          onClick={onTriggerStartup}
          className="relative w-8 h-8 rounded-lg bg-gradient-to-tr from-reeta-cyan via-sky-500 to-reeta-blue flex items-center justify-center shadow-lg shadow-reeta-cyan/25 hover:scale-105 active:scale-95 transition-all group"
          title="Click to replay REETA cinematic activation sequence"
        >
          <span className="font-mono font-black text-obsidian-950 text-sm">R</span>
          <div className="absolute inset-0 rounded-lg bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold tracking-wider text-slate-100 text-sm">REETA</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-reeta-cyan/10 text-reeta-cyan border border-reeta-cyan/30 shadow-sm shadow-reeta-cyan/10">
              v1.0 OS
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-sans leading-none">Responsive Executive Engine</p>
        </div>
      </div>

      {/* Holographic Status Indicators */}
      <div className="flex items-center gap-3 text-xs font-mono">
        {/* Model Provider / Mock Mode Indicator */}
        {health?.active_provider === 'mock' || !health?.active_provider ? (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-300 shadow-sm shadow-amber-500/10 cursor-help"
            title="MOCK MODE ACTIVE: No OpenAI API key detected. Set OPENAI_API_KEY in backend/.env to connect live reasoning models."
          >
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span className="text-[11px] font-bold tracking-wide">MOCK MODE</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy-950/80 border border-navy-800 text-slate-300 shadow-inner">
            <Cpu className="w-3.5 h-3.5 text-reeta-cyan" />
            <span className="text-[11px] font-semibold tracking-wide">
              {health.active_provider.toUpperCase()}
            </span>
          </div>
        )}

        {/* Database pgvector */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy-950/80 border border-navy-800 text-slate-300 shadow-inner">
          <Database
            className={`w-3.5 h-3.5 ${
              health?.database === 'connected' ? 'text-reeta-success' : 'text-reeta-danger'
            }`}
          />
          <span className="text-[11px] tracking-wide">PGVECTOR</span>
        </div>

        {/* WebSocket Event Stream */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy-950/80 border border-navy-800 text-slate-300 shadow-inner">
          <Activity
            className={`w-3.5 h-3.5 ${wsConnected ? 'text-reeta-cyan animate-pulse' : 'text-slate-500'}`}
          />
          <span className="text-[11px] tracking-wide">
            {wsConnected ? 'STREAM LIVE' : 'CONNECTING'}
          </span>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2.5">
        {/* Voice Listening Toggle */}
        <button
          onClick={toggleVoiceListening}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isListening
              ? 'bg-reeta-cyan text-obsidian-950 shadow-md shadow-reeta-cyan/40 font-bold animate-pulse'
              : 'bg-navy-900/90 text-slate-300 hover:text-slate-100 hover:bg-navy-800 border border-navy-700/80'
          }`}
          title={isListening ? 'Voice listening engaged' : 'Activate voice listening'}
        >
          {isListening ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
          <span className="font-mono text-[11px]">{isListening ? 'LISTENING' : 'VOICE OFF'}</span>
        </button>

        {/* Emergency Stop Kill Switch */}
        <button
          onClick={triggerEmergencyStop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reeta-danger/10 hover:bg-reeta-danger/25 text-reeta-danger border border-reeta-danger/40 transition-all text-xs font-semibold shadow-sm shadow-reeta-danger/10"
          title="Emergency Stop: Abort all active tasks and child processes immediately"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span className="font-mono text-[11px]">KILL SWITCH</span>
        </button>
      </div>
    </header>
  );
};
