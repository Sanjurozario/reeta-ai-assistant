import React, { useEffect } from 'react';
import { useAppStore } from '../stores/useAppStore';
import * as api from '../services/api';
import { Activity, CheckCircle, Clock, XCircle, AlertTriangle, StopCircle, RefreshCw, ShieldAlert, ArrowRight } from 'lucide-react';

export const LiveOperations: React.FC = () => {
  const { activeTask, refreshTasks, setActiveScreen } = useAppStore();

  useEffect(() => {
    if (activeTask && (activeTask.status === 'running' || activeTask.status === 'planning')) {
      const interval = setInterval(() => {
        refreshTasks();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [activeTask?.status, refreshTasks]);

  const handleCancel = async () => {
    if (activeTask) {
      await api.cancelTask(activeTask.id);
      await refreshTasks();
    }
  };

  if (!activeTask) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-transparent p-6 text-center">
        <Activity className="w-12 h-12 text-slate-600 mb-3" />
        <h2 className="text-sm font-mono text-slate-300">NO ACTIVE OPERATION</h2>
        <p className="text-xs text-slate-500 mt-1">Submit an instruction in Command Center to initiate autonomous execution.</p>
      </div>
    );
  }

  const steps = activeTask.steps || [];
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const progressPercent =
    activeTask.status === 'completed'
      ? 100
      : steps.length > 0
      ? Math.round((completedSteps / steps.length) * 100)
      : 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-transparent p-6 overflow-y-auto select-none">
      {/* Operation Header */}
      <div className="border border-navy-800/80 rounded-2xl bg-[#070C18]/85 backdrop-blur-xl p-5 mb-5 flex items-start justify-between shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-base font-bold font-mono text-slate-100">{activeTask.title}</h2>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase ${
                activeTask.status === 'completed'
                  ? 'bg-reeta-success/15 text-reeta-success border-reeta-success/40'
                  : activeTask.status === 'running'
                  ? 'bg-reeta-cyan/15 text-reeta-cyan border-reeta-cyan/40 animate-pulse'
                  : activeTask.status === 'waiting_approval'
                  ? 'bg-reeta-warning/15 text-reeta-warning border-reeta-warning/40'
                  : activeTask.status === 'cancelled'
                  ? 'bg-slate-700/30 text-slate-400 border-slate-700'
                  : 'bg-reeta-danger/15 text-reeta-danger border-reeta-danger/40'
              }`}
            >
              {activeTask.status.replace('_', ' ')}
            </span>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-1 max-w-2xl">{activeTask.objective}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={refreshTasks}
            className="p-2 rounded-xl bg-navy-950/80 hover:bg-navy-900 text-slate-300 border border-navy-800 transition-colors"
            title="Refresh status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {activeTask.status === 'running' && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-reeta-danger/10 hover:bg-reeta-danger/25 text-reeta-danger border border-reeta-danger/40 text-xs font-semibold transition-all shadow-sm shadow-reeta-danger/10"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>CANCEL TASK</span>
            </button>
          )}
        </div>
      </div>

      {/* Security Approval Required Alert */}
      {activeTask.status === 'waiting_approval' && (
        <div className="mb-5 border border-reeta-warning/40 bg-reeta-warning/10 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 text-reeta-warning shrink-0" />
            <div>
              <h3 className="text-xs font-bold font-mono text-reeta-warning">SECURITY AUTHORIZATION REQUIRED</h3>
              <p className="text-xs text-slate-300 mt-0.5">
                This task has invoked a consequential operation requiring explicit operator approval under Zero-Trust policy.
              </p>
            </div>
          </div>
          <button
            onClick={() => setActiveScreen('permissions')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reeta-warning/20 hover:bg-reeta-warning/30 text-reeta-warning border border-reeta-warning/40 text-xs font-semibold shrink-0"
          >
            <span>Review Ticket</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Task Failure Alert */}
      {activeTask.status === 'failed' && (
        <div className="mb-5 border border-reeta-danger/40 bg-reeta-danger/10 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-reeta-danger shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-bold font-mono text-reeta-danger">TASK EXECUTION HALTED</h3>
            <p className="text-xs text-slate-300 mt-0.5">
              {activeTask.error_detail?.error ||
                activeTask.error_detail?.unhandled_exception ||
                'Verification evidence did not satisfy required criteria. Execution was aborted safely.'}
            </p>
          </div>
        </div>
      )}

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
              className={`p-4 rounded-xl border backdrop-blur-md transition-all ${
                isRunning
                  ? 'bg-[#080E1E]/90 border-reeta-cyan/50 shadow-lg shadow-reeta-cyan/15 ring-1 ring-reeta-cyan/30'
                  : isDone
                  ? 'bg-[#070B16]/80 border-navy-800/80 hover:border-navy-700'
                  : 'bg-[#050812]/50 border-navy-900/60 opacity-60'
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

