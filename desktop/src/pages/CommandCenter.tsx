import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { AICore } from '../components/AICore';
import { AudioWaveform } from '../components/AudioWaveform';
import {
  Send,
  Mic,
  MicOff,
  Monitor,
  FolderPlus,
  Globe,
  Trash2,
  Brain,
  Code2,
  Terminal,
  Activity,
  ArrowRight,
  ChevronUp,
  ChevronDown,
  Info,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const CommandCenter: React.FC = () => {
  const {
    createTaskAndExecute,
    activeTask,
    setActiveScreen,
    logs,
    isListening,
    partialTranscript,
    isMockMode,
    toggleVoiceListening,
  } = useAppStore();

  const [prompt, setPrompt] = useState('');
  const [telemetryOpen, setTelemetryOpen] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    const title = prompt.length > 50 ? prompt.slice(0, 47) + '...' : prompt;
    createTaskAndExecute(title, prompt.trim());
    setPrompt('');
  };

  const handleQuickPrompt = (title: string, objective: string) => {
    createTaskAndExecute(title, objective);
  };

  const activeStatus = activeTask?.status;
  const isTaskActive = activeTask && (activeStatus === 'running' || activeStatus === 'planning' || activeStatus === 'waiting_approval');

  // Grounded Part-1 Autonomous Demonstrations
  const demonstrationChips = [
    {
      title: 'Open Notepad Note',
      objective: 'Hey REETA, open Notepad and write a short note saying hello',
      short: '1. Notepad Automation',
      icon: Monitor,
    },
    {
      title: 'Projects/Test Directory',
      objective: 'Create a folder called Projects/Test and put a file named notes.txt in it',
      short: '2. Folder & File Creation',
      icon: FolderPlus,
    },
    {
      title: 'Web News & Sources',
      objective: 'Search the web for the latest news on a topic and summarise it with sources',
      short: '3. Web Research & Sources',
      icon: Globe,
    },
    {
      title: 'Recycle Bin Deletion',
      objective: 'Delete that file',
      short: '4. Tier 2 Recycle Bin',
      icon: Trash2,
    },
    {
      title: 'Cognitive Preference Store',
      objective: 'Remember that I prefer dark mode',
      short: '5. Vector Memory Store',
      icon: Brain,
    },
    {
      title: 'Python Script Execution',
      objective: 'create a small python script in workspace, run it, report real output',
      short: '6. Python Code Runner',
      icon: Code2,
    },
  ];

  return (
    <div className="relative flex-1 flex flex-col h-full overflow-hidden px-6 py-4 select-none">
      {/* Mock Mode Alert Banner if no OpenAI Key is Configured */}
      {isMockMode && (
        <div className="max-w-2xl mx-auto w-full mb-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs font-mono text-amber-300 shadow-sm shadow-amber-500/5">
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>
              <strong>MOCK MODE:</strong> Running deterministic local simulation. Add <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">OPENAI_API_KEY</code> to <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">backend/.env</code> for live cloud reasoning.
            </span>
          </div>
        </div>
      )}

      {/* Central Visual Focus: Animated AI Energy Core */}
      <div className="flex-1 flex flex-col items-center justify-center max-w-4xl mx-auto w-full -mt-2">
        <AICore onCoreClick={toggleVoiceListening} />

        {/* Audio-Reactive Waveform when Voice Active */}
        <div className="h-12 flex items-center justify-center mt-1">
          <AudioWaveform isListening={isListening} />
        </div>

        {/* Real-time Streaming Transcript when Voice Active */}
        {isListening && partialTranscript && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs font-mono text-reeta-cyan bg-navy-950/80 px-4 py-1 rounded-full border border-reeta-cyan/40 shadow-md shadow-reeta-cyan/20 animate-pulse my-1"
          >
            "{partialTranscript}"
          </motion.div>
        )}

        {/* Active Task Mini HUD Card (Visible when operation is in progress) */}
        {isTaskActive && activeTask && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            onClick={() => setActiveScreen('operations')}
            className="w-full max-w-xl mx-auto my-3 px-4 py-2.5 rounded-xl bg-navy-950/80 border border-reeta-cyan/40 shadow-lg shadow-reeta-cyan/10 backdrop-blur-md flex items-center justify-between cursor-pointer hover:border-reeta-cyan transition-all group"
          >
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-2 h-2 rounded-full bg-reeta-cyan animate-ping shrink-0" />
              <div className="truncate">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-slate-100 truncate">
                    {activeTask.title}
                  </span>
                  <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-reeta-cyan/15 text-reeta-cyan border border-reeta-cyan/30">
                    {activeStatus}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 truncate">
                  {activeTask.objective}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 pl-3">
              <span className="text-xs font-mono text-reeta-cyan group-hover:underline">
                View DAG
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-reeta-cyan group-hover:translate-x-0.5 transition-transform" />
            </div>
          </motion.div>
        )}

        {/* Cinematic Floating Glassmorphic Command Input Bar */}
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-2xl relative mt-3 group"
        >
          {/* Subtle Ambient Input Glow */}
          <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-reeta-cyan/20 via-sky-500/20 to-reeta-blue/20 blur-md opacity-40 group-focus-within:opacity-100 transition-opacity pointer-events-none" />

          <div className="relative flex items-center bg-[#070C18]/90 border border-navy-700/80 focus-within:border-reeta-cyan/80 rounded-2xl px-4 py-2.5 shadow-2xl backdrop-blur-xl transition-all">
            {/* Left Voice Toggle inside input capsule */}
            <button
              type="button"
              onClick={toggleVoiceListening}
              className={`p-2 rounded-xl transition-all mr-2 shrink-0 ${
                isListening
                  ? 'bg-reeta-cyan text-obsidian-950 shadow-md shadow-reeta-cyan/50 animate-pulse'
                  : 'bg-navy-900/80 text-slate-400 hover:text-reeta-cyan hover:bg-navy-800'
              }`}
              title={isListening ? 'Voice listening active' : 'Click to activate voice'}
            >
              {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
            </button>

            {/* Input Element */}
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={
                isListening
                  ? 'Listening for voice instruction or type here...'
                  : 'Instruct REETA (e.g., "Research latest news with sources")...'
              }
              className="flex-1 bg-transparent text-sm font-sans text-slate-100 placeholder-slate-500 focus:outline-none"
            />

            {/* Submit Arrow Button */}
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="p-2 rounded-xl bg-reeta-cyan text-obsidian-950 disabled:opacity-30 disabled:bg-navy-800 disabled:text-slate-500 hover:shadow-lg hover:shadow-reeta-cyan/30 transition-all ml-2 shrink-0"
              title="Execute Autonomous Objective"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>

        {/* Holographic Tactical Workflow Chips */}
        <div className="w-full max-w-3xl mt-5">
          <div className="flex items-center justify-between pb-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
              Verified Autonomous Demonstrations
            </span>
            <span className="text-[10px] font-mono text-reeta-cyan/70">
              1-CLICK EXECUTION
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {demonstrationChips.map((chip, idx) => {
              const Icon = chip.icon;
              return (
                <button
                  key={idx}
                  onClick={() => handleQuickPrompt(chip.title, chip.objective)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-[#080D1A]/70 hover:bg-navy-900/80 border border-navy-800 hover:border-reeta-cyan/40 text-left transition-all duration-200 group shadow-sm"
                >
                  <div className="p-1.5 rounded-lg bg-navy-950 border border-navy-800 group-hover:border-reeta-cyan/50 text-reeta-cyan group-hover:text-reeta-cyan transition-colors">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-semibold text-slate-200 group-hover:text-reeta-cyan transition-colors truncate">
                      {chip.short}
                    </div>
                    <div className="text-[10px] font-mono text-slate-500 truncate">
                      {chip.title}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Futuristic Telemetry HUD Strip at Bottom */}
      <div className="w-full max-w-4xl mx-auto mt-2">
        <div className="border border-navy-800/80 rounded-xl bg-[#070B16]/85 backdrop-blur-md overflow-hidden">
          {/* Header Bar */}
          <div
            onClick={() => setTelemetryOpen(!telemetryOpen)}
            className="flex items-center justify-between px-3.5 py-1.5 cursor-pointer hover:bg-navy-900/50 transition-colors"
          >
            <div className="flex items-center gap-2 font-mono text-[10px] text-slate-400">
              <Terminal className="w-3 h-3 text-reeta-cyan" />
              <span className="tracking-widest uppercase text-slate-300">
                SYSTEM TELEMETRY
              </span>
              <span className="text-slate-600">//</span>
              <span className="text-slate-400 truncate max-w-xs sm:max-w-md">
                {logs[logs.length - 1] || 'Real-time telemetry stream active.'}
              </span>
            </div>

            <div className="flex items-center gap-2 text-slate-500 hover:text-slate-300">
              <span className="text-[9px] font-mono uppercase">
                {telemetryOpen ? 'MINIMIZE' : 'EXPAND'}
              </span>
              {telemetryOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </div>
          </div>

          {/* Expandable Log Drawer */}
          <AnimatePresence>
            {telemetryOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 130, opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="border-t border-navy-800/80 p-3 overflow-y-auto font-mono text-[11px] space-y-1 bg-obsidian-950/90"
              >
                {logs.slice(-15).map((log, index) => (
                  <div key={index} className="flex gap-2 leading-relaxed">
                    <span className="text-slate-600 select-none">&gt;</span>
                    <span
                      className={
                        log.includes('[Verification]')
                          ? 'text-reeta-success'
                          : log.includes('[Security]')
                          ? 'text-reeta-warning'
                          : log.includes('[Task Created]')
                          ? 'text-reeta-cyan'
                          : 'text-slate-300'
                      }
                    >
                      {log}
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
