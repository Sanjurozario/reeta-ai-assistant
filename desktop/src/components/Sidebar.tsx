import React from 'react';
import { useAppStore } from '../stores/useAppStore';
import { ScreenType } from '../types';
import {
  Terminal,
  Activity,
  Layers,
  Monitor,
  Brain,
  ShieldCheck,
  History,
  Sliders,
} from 'lucide-react';

interface NavItem {
  id: ScreenType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export const Sidebar: React.FC = () => {
  const { activeScreen, setActiveScreen, pendingApprovals } = useAppStore();

  const navItems: NavItem[] = [
    { id: 'command', label: 'Command Center', icon: Terminal },
    { id: 'operations', label: 'Live Operations', icon: Activity },
    { id: 'workspace', label: 'Agent Workspace', icon: Layers },
    { id: 'computer', label: 'Computer View', icon: Monitor },
    { id: 'memory', label: 'Memory Center', icon: Brain },
    { id: 'permissions', label: 'Permissions', icon: ShieldCheck, badge: pendingApprovals.length },
    { id: 'history', label: 'Task History', icon: History },
    { id: 'settings', label: 'Settings', icon: Sliders },
  ];

  return (
    <aside className="w-56 border-r border-navy-800 bg-obsidian-950 flex flex-col justify-between py-4 select-none">
      <nav className="px-3 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-mono tracking-wider text-slate-500 uppercase">
          Operating Modules
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeScreen === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveScreen(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-navy-900 text-reeta-cyan border border-navy-700 shadow-sm shadow-navy-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-navy-950/60'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-reeta-cyan' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-reeta-warning text-obsidian-950 font-bold animate-pulse">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* System Telemetry Footer */}
      <div className="px-4 py-3 mx-3 rounded-lg bg-navy-950/70 border border-navy-900 text-[10px] font-mono text-slate-500 space-y-1">
        <div className="flex justify-between">
          <span>HOST:</span>
          <span className="text-slate-400">WIN11 DESKTOP</span>
        </div>
        <div className="flex justify-between">
          <span>ENGINE:</span>
          <span className="text-reeta-cyan">LANGGRAPH</span>
        </div>
        <div className="flex justify-between">
          <span>SECURITY:</span>
          <span className="text-reeta-success">ZERO-TRUST</span>
        </div>
      </div>
    </aside>
  );
};
