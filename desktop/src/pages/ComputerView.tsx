import React, { useState } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { Monitor, Camera, RefreshCw, AppWindow, Play, ShieldAlert, Cpu } from 'lucide-react';

export const ComputerView: React.FC = () => {
  const { logs, createTaskAndExecute } = useAppStore();
  const [screenshotUri, setScreenshotUri] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [activeWindows, setActiveWindows] = useState<Array<{ title: string; pid?: number }>>([
    { title: 'REETA — responsive executive engine for tasks and automation', pid: 14220 },
    { title: 'Windows PowerShell', pid: 8932 },
    { title: 'Docker Desktop Engine', pid: 4892 },
  ]);

  const handleCaptureScreen = async () => {
    setIsCapturing(true);
    try {
      // Trigger screen capture task
      await createTaskAndExecute('Capture Desktop Screen', 'Use capture_screen to inspect the active Windows 11 desktop display');
    } finally {
      setIsCapturing(false);
    }
  };

  const handleListWindows = async () => {
    await createTaskAndExecute('List Active Windows', 'Use list_windows to enumerate all accessible desktop windows and processes');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-obsidian-950 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center space-x-2">
            <Monitor className="w-5 h-5 text-reeta-cyan" />
            <span>WINDOWS 11 COMPUTER VIEW</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time visual grounding, UI Automation inspection, and controlled desktop interaction.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleListWindows}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded-lg bg-navy-900 border border-navy-700 text-slate-200 hover:border-reeta-cyan transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-reeta-cyan" />
            <span>Scan Windows</span>
          </button>

          <button
            onClick={handleCaptureScreen}
            disabled={isCapturing}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded-lg bg-reeta-cyan/20 border border-reeta-cyan text-reeta-cyan hover:bg-reeta-cyan/30 transition-colors"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>{isCapturing ? 'Capturing...' : 'Capture Screen'}</span>
          </button>
        </div>
      </div>

      {/* Screen Preview & Active Windows Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Virtual Screen Display */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 flex flex-col space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
              <Camera className="w-4 h-4 text-reeta-cyan" />
              <span>DESKTOP DISPLAY BUFFER (1920x1080)</span>
            </h2>
            <span className="text-[10px] font-mono text-slate-500 uppercase">Driver: mss fast-grab</span>
          </div>

          <div className="relative aspect-video rounded-lg bg-obsidian-900 border border-navy-800 flex items-center justify-center overflow-hidden">
            {screenshotUri ? (
              <img src={screenshotUri} alt="Desktop Screen" className="w-full h-full object-contain" />
            ) : (
              <div className="text-center p-6 space-y-3">
                <Monitor className="w-12 h-12 text-slate-700 mx-auto" />
                <p className="text-xs font-mono text-slate-500">Live visual buffer ready.</p>
                <button
                  onClick={handleCaptureScreen}
                  className="px-4 py-2 text-xs font-mono bg-navy-800 hover:bg-navy-700 text-reeta-cyan border border-navy-700 rounded-lg transition-colors"
                >
                  Capture Live Frame
                </button>
              </div>
            )}
            <div className="absolute bottom-2 left-2 px-2 py-1 bg-obsidian-950/80 border border-navy-800 rounded text-[10px] font-mono text-slate-400">
              Zero-Trust Guard: All keyboard/mouse inputs require explicit authorization
            </div>
          </div>
        </div>

        {/* Windows & Application Registry */}
        <div className="p-5 rounded-xl bg-navy-950/80 border border-navy-800/80 flex flex-col space-y-4">
          <h2 className="text-sm font-semibold font-mono text-slate-200 flex items-center space-x-2">
            <AppWindow className="w-4 h-4 text-reeta-cyan" />
            <span>ACCESSIBLE WINDOWS</span>
          </h2>

          <div className="space-y-2 overflow-y-auto max-h-80">
            {activeWindows.map((win, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-navy-900/90 border border-navy-800/80 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-slate-200 truncate pr-2">{win.title}</span>
                  {win.pid && <span className="font-mono text-[10px] text-slate-500">PID {win.pid}</span>}
                </div>
                <div className="flex items-center space-x-2 text-[10px] font-mono text-slate-400">
                  <span className="text-emerald-400">UI Automation: Ready</span>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Launch Control */}
          <div className="pt-3 border-t border-navy-800/80 space-y-2">
            <h3 className="text-xs font-mono text-slate-400">QUICK LAUNCH TOOL</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => createTaskAndExecute('Open Notepad', 'Launch notepad.exe via open_application tool')}
                className="p-2 rounded bg-navy-900 border border-navy-800 text-[11px] font-mono text-slate-300 hover:border-reeta-cyan transition-colors text-left truncate"
              >
                Launch Notepad
              </button>
              <button
                onClick={() => createTaskAndExecute('Open Calculator', 'Launch calc.exe via open_application tool')}
                className="p-2 rounded bg-navy-900 border border-navy-800 text-[11px] font-mono text-slate-300 hover:border-reeta-cyan transition-colors text-left truncate"
              >
                Launch Calc
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

