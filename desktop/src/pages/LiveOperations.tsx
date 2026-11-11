import React from 'react';
import { useAppStore } from '../stores/useAppStore';
import * as api from '../services/api';
import { Activity, CheckCircle, Clock, XCircle, AlertTriangle, StopCircle, RefreshCw } from 'lucide-react';

export const LiveOperations: React.FC = () => {
  const { activeTask, refreshTasks } = useAppStore();

  const handleCancel = async () => {
    if (activeTask) {
      await api.cancelTask(activeTask.id);
      await refreshTasks();
    }
  };

  if (!activeTask) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-obsidian-950 p-6 text-center">
        <Activity className="w-12 h-12 text-slate-600 mb-3" />
        <h2 className="text-sm font-mono text-slate-300">NO ACTIVE OPERATION</h2>
        <p className="text-xs text-slate-500 mt-1">Submit an instruction in Command Center to initiate autonomous execution.</p>
      </div>
    );
  }

  const steps = activeTask.steps || [];
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const progressPercent = steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto">
      {/* Operation Header */}
      <div className="border border-navy-800 rounded-xl bg-obsidian-900 p-5 mb-5 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-base font-bold font-mono text-slate-100">{activeTask.title}</h2>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase ${
                activeTask.status === 'completed'
                  ? 'bg-reeta-success/10 text-reeta-success border-reeta-success/30'
                  : activeTask.status === 'running'
                  ? 'bg-reeta-cyan/10 text-reeta-cyan border-reeta-cyan/30 animate-pulse'
                  : activeTask.status === 'waiting_approval'
                  ? 'bg-reeta-warning/10 text-reeta-warning border-reeta-warning/30'
                  : activeTask.status === 'cancelled'
                  ? 'bg-slate-700/30 text-slate-400 border-slate-700'
                  : 'bg-reeta-danger/10 text-reeta-danger border-reeta-danger/30'
              }`}
            >
              {activeTask.status.replace('_', ' ')}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">{activeTask.objective}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={refreshTasks}
            className="p-2 rounded-lg bg-navy-900 hover:bg-navy-800 text-slate-300 border border-navy-800"
            title="Refresh status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {activeTask.status === 'running' && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reeta-danger/10 hover:bg-reeta-danger/20 text-reeta-danger border border-reeta-danger/30 text-xs font-semibold"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>CANCEL TASK</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6 space-y-1.5">
        <div className="flex justify-between text-xs font-mono text-slate-400">
          <span>DAG EXECUTION PROGRESS</span>
          <span>{progressPercent}%</span>
        </div>
        <div className="w-full h-2 bg-navy-900 rounded-full overflow-hidden border border-navy-800">
          <div
            className="h-full bg-gradient-to-r from-reeta-cyan to-reeta-blue transition-all duration-500 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Visual DAG Step Flow */}
      <div className="space-y-3">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
          Execution Plan & Empirical Verification
        </div>

        {steps.map((step, idx) => {
          const isDone = step.status === 'completed';
          const isRunning = step.status === 'running';
          const isFailed = step.status === 'failed';

          return (
            <div
              key={step.id || idx}
              className={`p-4 rounded-xl border transition-all ${
                isRunning
                  ? 'bg-navy-950/80 border-reeta-cyan/40 shadow-sm shadow-reeta-cyan/10'
                  : isDone
                  ? 'bg-obsidian-900/60 border-navy-800'
                  : 'bg-obsidian-900/30 border-navy-900 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {isDone ? (
                      <CheckCircle className="w-4 h-4 text-reeta-success" />
                    ) : isRunning ? (
                      <Clock className="w-4 h-4 text-reeta-cyan animate-spin" />
                    ) : isFailed ? (
                      <XCircle className="w-4 h-4 text-reeta-danger" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-600 flex items-center justify-center text-[9px] font-mono text-slate-500">
                        {step.step_number}
                      </div>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-200">{step.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-navy-900 text-slate-400 border border-navy-800 uppercase">
                        {step.agent_type}
                      </span>
                    </div>

                    {/* Verification Evidence */}
                    {step.output_payload && Object.keys(step.output_payload).length > 0 && (
                      <div className="mt-2 text-[11px] font-mono bg-obsidian-950/80 border border-navy-900 rounded p-2 text-slate-300">
                        <span className="text-reeta-cyan font-semibold">Result / Evidence: </span>
                        <span>{JSON.stringify(step.output_payload).slice(0, 200)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <span className="text-[10px] font-mono text-slate-500 uppercase">{step.status}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
