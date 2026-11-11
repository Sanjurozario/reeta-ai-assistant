import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Brain, Search, Plus, Sparkles, Database, Key, Check } from 'lucide-react';
import { MemoryItem } from '../types';

export const MemoryCenter: React.FC = () => {
  const { logs } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState('user_preference');
  const [memories, setMemories] = useState<MemoryItem[]>([
    {
      id: 'mem-001',
      content: 'User prefers dark obsidian UI themes and concise terminal summaries over verbose reports.',
      memory_type: 'preference',
      category: 'user_preference',
      similarity_score: 0.94,
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
    {
      id: 'mem-002',
      content: 'Workspace root is "e:/PROJECTS/reeta — responsive executive engine for tasks and automation" on Windows 11.',
      memory_type: 'semantic',
      category: 'environment',
      similarity_score: 0.88,
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    },
    {
      id: 'mem-003',
      content: 'Docker PostgreSQL instance runs on mapped port 5433 with pgvector extension enabled.',
      memory_type: 'procedural',
      category: 'database',
      similarity_score: 0.82,
      created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    },
  ]);

  const handleAddMemory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    const newItem: MemoryItem = {
      id: `mem-${Date.now().toString().slice(-4)}`,
      content: newContent.trim(),
      memory_type: 'preference',
      category: newCategory,
      created_at: new Date().toISOString(),
    };

    setMemories([newItem, ...memories]);
    setNewContent('');
  };

  const filteredMemories = searchQuery
    ? memories.filter((m) =>
        m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.category.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : memories;

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
          <Brain className="w-5 h-5 text-reeta-cyan" />
          <span>COGNITIVE MEMORY SYSTEM</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Vector semantic retrieval powered by PostgreSQL pgvector, working memory caching, and user preference persistence.
        </p>
      </div>

      {/* Top Controls: Search & Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search semantic memory by cosine vector similarity..."
            className="w-full bg-navy-950/90 border border-navy-800 rounded-lg pl-9 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-reeta-cyan"
          />
        </div>

        <div className="flex items-center space-x-3 px-4 py-2 rounded-lg bg-navy-950/80 border border-navy-800 text-xs font-mono text-slate-300">
          <Database className="w-4 h-4 text-reeta-cyan" />
          <span>pgvector: 1536-dim vectors indexed</span>
        </div>
      </div>

      {/* Main Grid: Store Memory & Memory Records */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Memory Records List */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
            Stored Long-Term Memories ({filteredMemories.length})
          </h2>

          <div className="space-y-3">
            {filteredMemories.map((mem) => (
              <div
                key={mem.id}
                className="p-4 rounded-xl bg-navy-950/80 border border-navy-800/80 hover:border-navy-700 transition-colors space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-navy-800 text-reeta-cyan border border-navy-700">
                      {mem.category}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{mem.memory_type}</span>
                  </div>
                  {mem.similarity_score && (
                    <span className="text-[10px] font-mono text-emerald-400">
                      Score: {(mem.similarity_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-sans">{mem.content}</p>
                <div className="text-[10px] font-mono text-slate-500">
                  Stored at: {new Date(mem.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Add Memory Form & Working Memory Cache */}
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
            <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
              <Plus className="w-4 h-4 text-reeta-cyan" />
              <span>STORE NEW PREFERENCE</span>
            </h2>

            <form onSubmit={handleAddMemory} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full bg-navy-900 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
                >
                  <option value="user_preference">User Preference</option>
                  <option value="system_rule">System Rule</option>
                  <option value="workspace">Workspace Context</option>
                  <option value="workflow">Procedural Workflow</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Memory Content</label>
                <textarea
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  rows={4}
                  placeholder="e.g. Always generate ReportLab PDF reports using the dark obsidian palette..."
                  className="w-full bg-navy-900 border border-navy-800 rounded p-2.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-reeta-cyan resize-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-reeta-cyan/20 hover:bg-reeta-cyan/30 border border-reeta-cyan text-reeta-cyan text-xs font-mono rounded transition-colors"
              >
                Index Into pgvector
              </button>
            </form>
          </div>

          {/* Cognitive State Box */}
          <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-2 text-xs font-mono">
            <span className="text-slate-400 block font-semibold">WORKING MEMORY BUFFER</span>
            <div className="bg-obsidian-950 p-2.5 rounded border border-navy-800 text-[11px] text-slate-400 space-y-1">
              <p><span className="text-reeta-cyan">active_workspace:</span> e:/PROJECTS/reeta...</p>
              <p><span className="text-reeta-cyan">agent_mode:</span> autonomous_supervised</p>
              <p><span className="text-reeta-cyan">active_os:</span> Windows 11 Desktop</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
