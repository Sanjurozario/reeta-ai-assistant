import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Bot, FileText, CheckCircle2, AlertTriangle, ExternalLink, Code2, Cpu, Globe, FolderTree, Calendar } from 'lucide-react';

export const AgentWorkspace: React.FC = () => {
  const { activeTask, tasks } = useAppStore();
  const [selectedAgent, setSelectedAgent] = useState<string>('all');

  const agents = [
    { id: 'research', name: 'Research Agent', icon: Globe, desc: 'Web research, fact synthesis, ReportLab PDF generation' },
    { id: 'coding', name: 'Coding Agent', icon: Code2, desc: 'AST/regex code search, diff patching, automated testing' },
    { id: 'computer', name: 'Computer Agent', icon: Cpu, desc: 'Windows UI automation, window listing, screen capture' },
    { id: 'browser', name: 'Browser Agent', icon: Globe, desc: 'Playwright Chromium navigation, DOM table extraction' },
    { id: 'file', name: 'File Management Agent', icon: FolderTree, desc: 'Extension organization, disk search, I/O verification' },
    { id: 'productivity', name: 'Productivity Agent', icon: Calendar, desc: 'Schedule management, reminder registration' },
  ];

  const artifacts = activeTask?.result?.artifacts || [];

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
          <Bot className="w-5 h-5 text-reeta-cyan" />
          <span>SPECIALIZED AGENT WORKSPACE</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Inspect autonomous workers, executed capabilities, produced artifacts, and empirical verification receipts.
        </p>
      </div>

      {/* Agents Roster */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isSelected = selectedAgent === agent.id;
          return (
            <div
              key={agent.id}
              onClick={() => setSelectedAgent(selectedAgent === agent.id ? 'all' : agent.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-navy-900 border-reeta-cyan shadow-md shadow-reeta-cyan/10'
                  : 'bg-navy-950/70 border-navy-800/80 hover:border-navy-700'
              }`}
            >
              <div className="flex items-center space-x-3 mb-2">
                <div className="p-2 rounded-lg bg-navy-800 border border-navy-700 text-reeta-cyan">
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-200">{agent.name}</h3>
                  <span className="text-[10px] text-reeta-cyan font-mono uppercase">Zero-Trust Guarded</span>
                </div>
              </div>
              <p className="text-xs text-slate-400">{agent.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Artifacts and Verification Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generated Artifacts */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <FileText className="w-4 h-4 text-reeta-cyan" />
            <span>GENERATED ARTIFACTS ({artifacts.length})</span>
          </h2>

          {artifacts.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-navy-800 rounded-lg">
              <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No artifacts generated for the active task yet.</p>
              <p className="text-[11px] text-slate-600 mt-1">Execute a Research, PDF, or Coding task to generate artifacts.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {artifacts.map((art, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-navy-900/90 border border-navy-800"
                >
                  <div className="flex items-center space-x-3 truncate">
                    <FileText className="w-4 h-4 text-reeta-cyan shrink-0" />
                    <div className="truncate">
                      <p className="text-xs font-mono text-slate-200 truncate">{art.path}</p>
                      <span className="text-[10px] uppercase font-mono text-slate-500">{art.type}</span>
                    </div>
                  </div>
                  <span className="text-[10px] text-reeta-success font-mono px-2 py-0.5 rounded bg-reeta-success/10 border border-reeta-success/20">
                    Verified
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Task Steps & Evidence */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-reeta-success" />
            <span>EMPIRICAL VERIFICATION RECEIPTS</span>
          </h2>

          {!activeTask || !activeTask.steps || activeTask.steps.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-navy-800 rounded-lg">
              <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No verification receipts yet.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {activeTask.steps.map((st, i) => (
                <div key={i} className="p-3 rounded-lg bg-navy-900/80 border border-navy-800 text-xs font-mono">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-reeta-cyan font-semibold">Step {st.step_number}: {st.title}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                        st.status === 'completed'
                          ? 'bg-reeta-success/15 text-reeta-success'
                          : st.status === 'failed'
                          ? 'bg-reeta-danger/15 text-reeta-danger'
                          : 'bg-navy-800 text-slate-400'
                      }`}
                    >
                      {st.status}
                    </span>
                  </div>
                  {st.output_payload?.verification ? (
                    <div className="mt-2 text-[11px] text-slate-300 bg-obsidian-950 p-2 rounded border border-navy-800/60">
                      <p className="text-slate-400">Evidence:</p>
                      <pre className="text-[10px] text-emerald-400 whitespace-pre-wrap mt-0.5">
                        {JSON.stringify(st.output_payload.verification.evidence || st.output_payload.verification, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

