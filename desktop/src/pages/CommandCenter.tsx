import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Send, Sparkles, Terminal, FileText, Monitor, FolderSync, Bug, Globe, Brain } from 'lucide-react';

export const CommandCenter: React.FC = () => {
  const { createTaskAndExecute, sendUserMessage, logs, isListening } = useAppStore();
  const [prompt, setPrompt] = useState('');

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

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-hidden">
      {/* Central Visual Identity */}
      <div className="flex flex-col items-center justify-center my-auto max-w-3xl mx-auto w-full text-center space-y-4">
        <div className="relative">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-reeta-cyan/20 via-navy-800 to-reeta-blue/20 border border-reeta-cyan/30 flex items-center justify-center shadow-xl shadow-reeta-cyan/10">
            <Sparkles className="w-9 h-9 text-reeta-cyan animate-pulse" />
          </div>
          {isListening && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-reeta-cyan opacity-75"></span>
              <span className="relative inline-flex rounded-full h-4 w-4 bg-reeta-cyan"></span>
            </span>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-slate-100">
            REETA EXECUTIVE CONSOLE
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Autonomous Personal AI Operating System for Windows 11. State your objective to plan, orchestrate, execute tools, and verify outcomes.
          </p>
        </div>

        {/* Primary Prompt Input */}
        <form onSubmit={handleSubmit} className="w-full relative mt-3">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Instruct REETA (e.g., 'Research CRM competitor pricing and generate PDF report')..."
            className="w-full bg-navy-950/80 border border-navy-700/80 rounded-xl px-5 py-3.5 pr-14 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-reeta-cyan focus:ring-1 focus:ring-reeta-cyan shadow-inner"
          />
          <button
            type="submit"
            disabled={!prompt.trim()}
            className="absolute right-2.5 top-2.5 p-2 rounded-lg bg-reeta-cyan/20 hover:bg-reeta-cyan/30 text-reeta-cyan disabled:opacity-40 disabled:hover:bg-reeta-cyan/20 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Action Workflows */}
        <div className="w-full space-y-2 pt-2">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 text-left">
            Integrated Autonomous Workflows
          </div>
          <div className="grid grid-cols-3 gap-2.5 text-left">
            <button
              onClick={() => handleQuickPrompt("Research CRM Competitors & Generate PDF", "Research CRM competitor pricing and generate a styled PDF report")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <FileText className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>PDF Research Report</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Query web & generate validated PDF</p>
            </button>

            <button
              onClick={() => handleQuickPrompt("Open Windows Notepad & Inspect UI", "Open Notepad and inspect active desktop windows")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <Monitor className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>Windows App Automation</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Launch application & verify process</p>
            </button>

            <button
              onClick={() => handleQuickPrompt("Organize Authorized Project Folder", "Organize reports directory into categorized folders")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <FolderSync className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>Organize Project Folder</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Batch organize files by extension</p>
            </button>

            <button
              onClick={() => handleQuickPrompt("Inspect Codebase & Run Tests", "Inspect codebase bug and execute unit test suite")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <Bug className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>Code Debug & Tests</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Locate symbols and execute pytest</p>
            </button>

            <button
              onClick={() => handleQuickPrompt("Browse Web & Extract Data", "Browse Wikipedia and extract structured table data")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <Globe className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>Browser Automation</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Playwright Chromium navigation</p>
            </button>

            <button
              onClick={() => handleQuickPrompt("Save User Preference to Memory", "Remember user preference for dark obsidian UI and cyan accents")}
              className="p-3 rounded-lg bg-navy-950/60 hover:bg-navy-900 border border-navy-800 hover:border-reeta-cyan/40 transition-all group"
            >
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200 group-hover:text-reeta-cyan">
                <Brain className="w-3.5 h-3.5 text-reeta-cyan" />
                <span>Cognitive Memory</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">Store preference in pgvector</p>
            </button>
          </div>
        </div>
      </div>

      {/* Terminal Live Telemetry Stream */}
      <div className="h-44 border border-navy-800 rounded-xl bg-obsidian-900 p-3 flex flex-col font-mono text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-navy-800 text-[10px] text-slate-500 uppercase tracking-wider">
          <div className="flex items-center gap-2">
            <Terminal className="w-3 h-3 text-reeta-cyan" />
            <span>Execution Event Telemetry</span>
          </div>
          <span className="text-reeta-cyan">LIVE STREAM</span>
        </div>
        <div className="flex-1 overflow-y-auto space-y-1 mt-2 text-[11px] text-slate-300">
          {logs.slice(-15).map((log, index) => (
            <div key={index} className="flex gap-2 leading-relaxed">
              <span className="text-slate-600 select-none">&gt;</span>
              <span className={log.includes('[Verification]') ? 'text-reeta-success' : log.includes('[Security]') ? 'text-reeta-warning' : 'text-slate-300'}>
                {log}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
