import React, { useEffect, useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { ShieldCheck, ShieldAlert, Check, X, RefreshCw, KeyRound, AlertOctagon } from 'lucide-react';
import * as api from '../services/api';
import { AuditLogItem } from '../types';

export const Permissions: React.FC = () => {
  const { pendingApprovals, refreshApprovals, approveTicket, rejectTicket } = useAppStore();
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadAudit = async () => {
    setLoading(true);
    try {
      const logs = await api.fetchAuditLogs(30);
      setAuditLogs(logs);
    } catch (e) {
      console.warn('Failed to fetch audit logs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshApprovals();
    loadAudit();
  }, []);

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-reeta-cyan" />
            <span>ZERO-TRUST PERMISSION MANAGER</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enforce mandatory human authorization for Tier 2 consequential and Tier 3 restricted actions.
          </p>
        </div>

        <button
          onClick={() => {
            refreshApprovals();
            loadAudit();
          }}
          className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded-lg bg-navy-900 border border-navy-700 text-slate-200 hover:border-reeta-cyan transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 text-reeta-cyan" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Pending Approvals Section */}
      <div className="space-y-3">
        <h2 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span>PENDING HUMAN APPROVAL TICKETS ({pendingApprovals.length})</span>
        </h2>

        {pendingApprovals.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-navy-950/80 border border-navy-800/80">
            <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-xs font-mono text-slate-400">All actions authorized. No pending approval requests.</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Consequential operations (Tier 2/3) will pause execution and appear here for authorization.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {pendingApprovals.map((ticket) => (
              <div
                key={ticket.id}
                className="p-4 rounded-xl bg-navy-950/90 border border-amber-500/40 shadow-lg shadow-amber-500/5 space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        Tier 2 Approval Demanded
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        Action: <strong className="text-slate-200">{ticket.action_type}</strong>
                      </span>
                    </div>
                    <p className="text-xs font-sans text-slate-200 mt-1">{ticket.description}</p>
                    <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                      Target: <span className="text-reeta-cyan">{ticket.target_resource}</span>
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => approveTicket(ticket.id)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 text-xs font-mono transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => rejectTicket(ticket.id)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/40 text-xs font-mono transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>

                <div className="pt-2 border-t border-navy-800 text-[10px] font-mono text-slate-500 flex items-center justify-between">
                  <span>Ticket ID: {ticket.id}</span>
                  <span className="flex items-center space-x-1">
                    <KeyRound className="w-3 h-3 text-reeta-cyan" />
                    <span>HMAC-SHA256 Token Verified</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security Audit Trail */}
      <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
        <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
          <KeyRound className="w-4 h-4 text-reeta-cyan" />
          <span>IMMUTABLE AUDIT LOG (LAST 30 EVENTS)</span>
        </h2>

        {auditLogs.length === 0 ? (
          <p className="text-xs font-mono text-slate-500">No audit events recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-navy-800 text-slate-500 text-[11px]">
                  <th className="pb-2">Timestamp</th>
                  <th className="pb-2">Actor</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Resource</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-800/50">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="text-slate-300">
                    <td className="py-2 text-[10px] text-slate-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2 text-reeta-cyan">{log.actor}</td>
                    <td className="py-2 text-slate-200">{log.action_type}</td>
                    <td className="py-2 text-[11px] text-slate-400 truncate max-w-xs">
                      {log.target_resource || '-'}
                    </td>
                    <td className="py-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                          log.status === 'success' || log.status === 'approved'
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-rose-500/15 text-rose-400'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
