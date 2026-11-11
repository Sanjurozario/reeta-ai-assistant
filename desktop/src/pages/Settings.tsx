import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Settings as SettingsIcon, Cpu, Mic, Shield, HardDrive, Check, Save } from 'lucide-react';

export const Settings: React.FC = () => {
  const { health } = useAppStore();
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [whisperModel, setWhisperModel] = useState('base');
  const [ttsProvider, setTtsProvider] = useState('piper');
  const [zeroTrustStrict, setZeroTrustStrict] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
            <SettingsIcon className="w-5 h-5 text-reeta-cyan" />
            <span>SYSTEM & RUNTIME SETTINGS</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure multi-provider LLM gateway, local Ollama endpoints, voice synthesis, and security parameters.
          </p>
        </div>

        {saved && (
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
            <Check className="w-4 h-4" />
            <span>Settings saved successfully</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6 max-w-4xl">
        {/* Model Gateway Configuration */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-reeta-cyan" />
            <span>AI MODEL GATEWAY & REASONING PROVIDER</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1.5">Primary Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full bg-navy-900 border border-navy-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
              >
                <option value="openai">OpenAI (GPT-4o, o1-mini)</option>
                <option value="gemini">Google Gemini (Gemini 1.5 Pro/Flash)</option>
                <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
                <option value="ollama">Ollama (Local Llama 3 / Mistral)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1.5">Default Reasoning Model</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full bg-navy-900 border border-navy-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-mono text-slate-400 block mb-1.5">Ollama Server Endpoint</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="w-full bg-navy-900 border border-navy-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
              />
            </div>
          </div>
        </div>

        {/* Voice & Speech Engine */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <Mic className="w-4 h-4 text-reeta-cyan" />
            <span>SPEECH RECOGNITION & VOICE SYNTHESIS (WORKSTREAM F)</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1.5">faster-whisper Model</label>
              <select
                value={whisperModel}
                onChange={(e) => setWhisperModel(e.target.value)}
                className="w-full bg-navy-900 border border-navy-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
              >
                <option value="tiny">tiny (Ultra-fast, lowest VRAM)</option>
                <option value="base">base (Balanced for RTX 2050)</option>
                <option value="small">small (High accuracy)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1.5">TTS Engine</label>
              <select
                value={ttsProvider}
                onChange={(e) => setTtsProvider(e.target.value)}
                className="w-full bg-navy-900 border border-navy-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-reeta-cyan"
              >
                <option value="piper">Piper (Offline ONNX Neural TTS)</option>
                <option value="cloud">Cloud Neural TTS</option>
              </select>
            </div>

            <div className="md:col-span-2 flex items-center space-x-3 pt-2">
              <input
                type="checkbox"
                id="wakeword"
                checked={wakeWordEnabled}
                onChange={(e) => setWakeWordEnabled(e.target.checked)}
                className="rounded border-navy-800 bg-navy-900 text-reeta-cyan focus:ring-0"
              />
              <label htmlFor="wakeword" className="text-xs font-mono text-slate-300">
                Enable Wake-Word Detection ("Hey Reeta") with background Voice Activity Detection (VAD)
              </label>
            </div>
          </div>
        </div>

        {/* Security & Zero-Trust Policies */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <Shield className="w-4 h-4 text-reeta-cyan" />
            <span>ZERO-TRUST PERMISSION POLICIES</span>
          </h2>

          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="zerotrust"
                checked={zeroTrustStrict}
                onChange={(e) => setZeroTrustStrict(e.target.checked)}
                className="rounded border-navy-800 bg-navy-900 text-reeta-cyan focus:ring-0"
              />
              <label htmlFor="zerotrust" className="text-xs font-mono text-slate-300">
                Enforce Strict 3-Tier Security (Tier 2 requires manual approval before tool execution)
              </label>
            </div>
            <p className="text-[11px] text-slate-500 font-mono pl-6">
              Actions like powershell_execute, open_application, and file writes outside workspace will pause execution.
            </p>
          </div>
        </div>

        <button
          type="submit"
          className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-reeta-cyan hover:bg-reeta-cyanDim text-obsidian-950 font-mono font-bold text-xs transition-colors shadow-lg shadow-reeta-cyan/20"
        >
          <Save className="w-4 h-4" />
          <span>Save Runtime Configuration</span>
        </button>
      </form>
    </div>
  );
};
