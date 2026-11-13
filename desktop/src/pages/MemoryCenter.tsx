import React, { useState, useEffect } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Brain, Search, Plus, Trash2, Database, Eraser, Check, Sparkles } from 'lucide-react';
import { MemoryItem } from '../types';

export const MemoryCenter: React.FC = () => {
  const { memories, refreshMemories, createMemory, deleteMemory, forgetMemory } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [forgetPrompt, setForgetPrompt] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState('user_preference');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    refreshMemories();
  }, [refreshMemories]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    setIsSubmitting(true);
    await createMemory(newContent.trim(), 'preference', newCategory);
    setNewContent('');
    setIsSubmitting(false);
  };

  const handleForget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgetPrompt.trim()) return;
    await forgetMemory(forgetPrompt.trim());
    setForgetPrompt('');
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
          Vector semantic retrieval powered by PostgreSQL pgvector, working memory caching, and persistent user preferences.
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
          <span>PostgreSQL pgvector: 1536-dim indexed</span>
        </div>
      </div>

      {/* Main Grid: Store Memory & Memory Records */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Memory Records List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
              Stored Long-Term Memories ({filteredMemories.length})
            </h2>
            <button
              onClick={() => refreshMemories()}
              className="text-[11px] font-mono text-reeta-cyan hover:underline"
            >
              Refresh
            </button>
          </div>

          <div className="space-y-3">
            {filteredMemories.length === 0 ? (
              <div className="p-8 rounded-xl bg-navy-950/40 border border-navy-900 text-center font-mono text-xs text-slate-500">
                No memories found. Store a preference below or tell REETA "Remember that I prefer..."
              </div>
            ) : (
              filteredMemories.map((mem) => (
                <div
                  key={mem.id}
                  className="p-4 rounded-xl bg-navy-950/80 border border-navy-800/80 hover:border-navy-700 transition-colors space-y-2 group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-navy-800 text-reeta-cyan border border-navy-700">
                        {mem.category}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{mem.memory_type}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {mem.similarity_score !== undefined && (
                        <span className="text-[10px] font-mono text-emerald-400">
                          Score: {(mem.similarity_score * 100).toFixed(0)}%
                        </span>
                      )}
                      <button
                        onClick={() => deleteMemory(mem.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition-all rounded"
                        title="Delete this memory record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed font-sans">{mem.content}</p>
                  <div className="text-[10px] font-mono text-slate-500">
                    ID: {mem.id.slice(0, 8)} | Stored at: {new Date(mem.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Sidebar: Add Memory & Semantic Forget */}
        <div className="space-y-6">
          {/* Store New Preference */}
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
                  rows={3}
                  placeholder="e.g. User prefers dark mode theme and concise executive summaries..."
                  className="w-full bg-navy-900 border border-navy-800 rounded p-2.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-reeta-cyan resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !newContent.trim()}
                className="w-full py-2 bg-reeta-cyan/20 hover:bg-reeta-cyan/30 disabled:opacity-40 border border-reeta-cyan text-reeta-cyan text-xs font-mono rounded transition-colors"
              >
                Index Into pgvector
              </button>
            </form>
          </div>

          {/* Semantic Forget Form */}
          <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-3">
            <h2 className="text-xs font-semibold font-mono text-slate-300 flex items-center space-x-2">
              <Eraser className="w-4 h-4 text-amber-400" />
              <span>SEMANTIC FORGET ("FORGET THIS")</span>
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              Searches pgvector for matching concept and deletes records with cosine distance &lt; 0.25.
            </p>
            <form onSubmit={handleForget} className="space-y-2">
              <input
                type="text"
                value={forgetPrompt}
                onChange={(e) => setForgetPrompt(e.target.value)}
                placeholder="e.g. Forget my preferred theme"
                className="w-full bg-navy-900 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-amber-400"
              />
              <button
                type="submit"
                disabled={!forgetPrompt.trim()}
                className="w-full py-1.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-mono rounded transition-colors disabled:opacity-40"
              >
                Forget Matching Memories
              </button>
            </form>
          </div>

          {/* Cognitive State Box */}
          <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-2 text-xs font-mono">
            <span className="text-slate-400 block font-semibold">WORKING CONTEXT BUFFER</span>
            <div className="bg-obsidian-950 p-2.5 rounded border border-navy-800 text-[11px] text-slate-400 space-y-1">
              <p><span className="text-reeta-cyan">active_workspace:</span> e:/PROJECTS/reeta...</p>
              <p><span className="text-reeta-cyan">vector_table:</span> public.memories</p>
              <p><span className="text-reeta-cyan">distance_metric:</span> cosine_distance (&lt;=&gt;)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
