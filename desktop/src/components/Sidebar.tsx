import React, { useState } from 'react';
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
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface NavItem {
  id: ScreenType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export const Sidebar: React.FC = () => {
  const { activeScreen, setActiveScreen, pendingApprovals } = useAppStore();
  const [collapsed, setCollapsed] = useState<boolean>(false);

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
    <aside
      className={`relative border-r border-navy-800/80 bg-[#040712]/80 backdrop-blur-xl flex flex-col justify-between py-3 select-none transition-all duration-300 z-20 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      <div>
        {/* Navigation Category Label & Collapse Button */}
        <div className="px-3 pb-2 flex items-center justify-between">
          {!collapsed && (
            <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase">
              MODULES
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg text-slate-500 hover:text-reeta-cyan hover:bg-navy-900/60 transition-colors mx-auto"
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Navigation Item Buttons */}
        <nav className="px-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveScreen(item.id)}
                title={collapsed ? item.label : undefined}
                className={`relative w-full flex items-center ${
                  collapsed ? 'justify-center py-2.5' : 'justify-between px-3 py-2'
                } rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-navy-900/90 text-reeta-cyan border border-reeta-cyan/40 shadow-md shadow-reeta-cyan/10 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-navy-900/40 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive ? 'text-reeta-cyan' : 'text-slate-400'
                    }`}
                  />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </div>

                {/* Badge Notification */}
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`${
                      collapsed
                        ? 'absolute top-1 right-1 w-2 h-2 rounded-full bg-reeta-warning animate-ping'
                        : 'px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-reeta-warning text-obsidian-950 font-bold animate-pulse'
                    }`}
                  >
                    {!collapsed && item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Futuristic Telemetry Footer */}
      {!collapsed ? (
        <div className="px-3.5 py-2.5 mx-2.5 rounded-xl bg-navy-950/70 border border-navy-900 text-[10px] font-mono text-slate-500 space-y-1 backdrop-blur-sm">
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
      ) : (
        <div className="flex flex-col items-center gap-2 pb-2 text-[9px] font-mono text-slate-600">
          <span className="w-1.5 h-1.5 rounded-full bg-reeta-success" title="Zero-Trust Active" />
          <span className="w-1.5 h-1.5 rounded-full bg-reeta-cyan" title="LangGraph Ready" />
        </div>
      )}
    </aside>
  );
};
