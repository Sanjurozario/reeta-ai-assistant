import React, { useEffect, useState } from 'react';
import { useAppStore } from './stores/useAppStore';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AtmosphereBackground } from './components/AtmosphereBackground';
import { StartupSequence } from './components/StartupSequence';
import { CommandCenter } from './pages/CommandCenter';
import { LiveOperations } from './pages/LiveOperations';
import { AgentWorkspace } from './pages/AgentWorkspace';
import { ComputerView } from './pages/ComputerView';
import { MemoryCenter } from './pages/MemoryCenter';
import { Permissions } from './pages/Permissions';
import { TaskHistory } from './pages/TaskHistory';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  const { activeScreen, init } = useAppStore();
  const [showStartup, setShowStartup] = useState<boolean>(true);

  useEffect(() => {
    init();
  }, [init]);

  const renderActiveScreen = () => {
    switch (activeScreen) {
      case 'command':
        return <CommandCenter />;
      case 'operations':
        return <LiveOperations />;
      case 'workspace':
        return <AgentWorkspace />;
      case 'computer':
        return <ComputerView />;
      case 'memory':
        return <MemoryCenter />;
      case 'permissions':
        return <Permissions />;
      case 'history':
        return <TaskHistory />;
      case 'settings':
        return <Settings />;
      default:
        return <CommandCenter />;
    }
  };

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-[#030508] text-slate-100 select-none font-sans">
      {/* Cinematic Startup Boot Sequence */}
      {showStartup && (
        <StartupSequence onComplete={() => setShowStartup(false)} />
      )}

      {/* Atmospheric Ambient Lighting & Particle Canvas */}
      <AtmosphereBackground />

      {/* Main Glassmorphic Operating Interface */}
      <div className="relative z-10 flex h-full w-full overflow-hidden">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Central Operating Workspace */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <Header onTriggerStartup={() => setShowStartup(true)} />
          <main className="flex-1 overflow-hidden flex flex-col">
            {renderActiveScreen()}
          </main>
        </div>
      </div>
    </div>
  );
};

export default App;
