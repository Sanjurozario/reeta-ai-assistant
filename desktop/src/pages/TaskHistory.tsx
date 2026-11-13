import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { History, CheckCircle2, XCircle, Clock, AlertCircle, ArrowUpRight } from 'lucide-react';
import { TaskItem } from '../types';

export const TaskHistory: React.FC = () => {
  const { tasks, refreshTasks, setActiveScreen } = useAppStore();
  const [filter, setFilter] = useState<string>('all');

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'all') return true;
    return t.status === filter;
  });

  const getStatusBadge = (status: TaskItem['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>Completed</span>
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      case 'running':
      case 'planning':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-reeta-cyan/15 text-reeta-cyan border border-reeta-cyan/30">
            <Clock className="w-3 h-3 animate-spin" />
            <span>Executing</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-navy-800 text-slate-400 border border-navy-700">
            <AlertCircle className="w-3 h-3" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
            <History className="w-5 h-5 text-reeta-cyan" />
            <span>TASK EXECUTION HISTORY</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Historical audit log of all autonomous objectives, execution plans, step graphs, and outcomes.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1.5 p-1 rounded-lg bg-navy-950 border border-navy-800">
          {['all', 'completed', 'failed', 'running'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1 rounded text-xs font-mono uppercase transition-colors ${
                filter === tab
                  ? 'bg-navy-800 text-reeta-cyan'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Task Records List */}
      <div className="space-y-3">
        {filteredTasks.length === 0 ? (
          <div className="p-10 text-center rounded-xl bg-navy-950/80 border border-navy-800/80">
            <History className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-xs font-mono text-slate-400">No tasks found matching filter: "{filter}".</p>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 hover:border-navy-700 transition-colors space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono text-reeta-cyan font-semibold">
                      [{task.id.slice(0, 8)}]
                    </span>
                    <h3 className="text-sm font-semibold text-slate-200 font-sans">{task.title}</h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{task.objective}</p>
                </div>
                {getStatusBadge(task.status)}
              </div>

              <div className="pt-2 border-t border-navy-800/70 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <div className="flex items-center space-x-4">
                  <span>Steps: {task.steps?.length || 0}</span>
                  <span>Verification: {task.verification_status}</span>
                  <span>Created: {new Date(task.created_at).toLocaleString()}</span>
                </div>
                <button
                  onClick={() => {
                    useAppStore.setState({ activeTask: task });
                    setActiveScreen('operations');
                  }}
                  className="flex items-center space-x-1 text-reeta-cyan hover:underline"
                >
                  <span>View Details</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

