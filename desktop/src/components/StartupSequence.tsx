import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ShieldCheck, Database, Cpu, Activity } from 'lucide-react';

interface StartupSequenceProps {
  onComplete: () => void;
}

export const StartupSequence: React.FC<StartupSequenceProps> = ({ onComplete }) => {
  const [stage, setStage] = useState<number>(0);

  const telemetryLines = [
    { id: 1, text: 'CORE KERNEL // INITIALIZED', icon: Cpu },
    { id: 2, text: 'PGVECTOR MEMORY REPOSITORY // LINKED', icon: Database },
    { id: 3, text: 'ZERO-TRUST SECURITY MATRIX // ARMED', icon: ShieldCheck },
    { id: 4, text: 'LANGGRAPH STATE MACHINE // SYNCHRONIZED', icon: Activity },
    { id: 5, text: 'REETA OPERATING SYSTEM // ONLINE', icon: Sparkles },
  ];

  useEffect(() => {
    const timer1 = setTimeout(() => setStage(1), 300);
    const timer2 = setTimeout(() => setStage(2), 650);
    const timer3 = setTimeout(() => setStage(3), 1050);
    const timer4 = setTimeout(() => setStage(4), 1450);
    const timer5 = setTimeout(() => setStage(5), 1850);
    const timerEnd = setTimeout(() => onComplete(), 2400);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        onComplete();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      clearTimeout(timer5);
      clearTimeout(timerEnd);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onComplete]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0, scale: 1.05 }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
        onClick={onComplete}
        className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#030508] text-slate-100 select-none overflow-hidden cursor-pointer"
      >
        {/* Background Grid & Lighting Flare */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(6, 182, 212, 0.5) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(6, 182, 212, 0.5) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
          }}
        />

        <div className="absolute w-[500px] h-[500px] rounded-full bg-cyan-500/10 blur-[130px] pointer-events-none" />

        {/* Central Awakening Core */}
        <div className="relative flex flex-col items-center">
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: [0, 1.2, 1], rotate: 0 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-36 h-36 rounded-full flex items-center justify-center"
          >
            {/* Outer Expanding Shockwave Ring */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: [0.8, 1.8, 2.2], opacity: [0, 0.6, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
              className="absolute inset-0 rounded-full border border-reeta-cyan/40"
            />

            {/* Concentric Rotating Dash Ring */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-0 rounded-full border border-dashed border-reeta-cyan/60 shadow-lg shadow-reeta-cyan/20"
            />

            {/* Glowing Singularity Orb */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="w-20 h-20 rounded-full bg-gradient-to-tr from-reeta-cyan via-sky-400 to-white shadow-2xl shadow-reeta-cyan/80 flex items-center justify-center"
            >
              <span className="font-mono font-black text-2xl text-obsidian-950">R</span>
            </motion.div>
          </motion.div>

          {/* System Identity Title */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-6 text-center"
          >
            <h1 className="text-2xl font-bold font-mono tracking-widest text-slate-100 flex items-center justify-center gap-2">
              <span className="text-reeta-cyan">REETA</span>
              <span className="text-xs px-2 py-0.5 rounded bg-navy-800 text-slate-300 border border-navy-700">
                v1.0 OS
              </span>
            </h1>
            <p className="text-xs font-mono tracking-wider text-slate-500 mt-1 uppercase">
              Responsive Executive Engine for Tasks and Automation
            </p>
          </motion.div>

          {/* Sequential Telemetry Boot Lines */}
          <div className="mt-8 w-80 space-y-2">
            {telemetryLines.map((line, idx) => {
              const Icon = line.icon;
              const isVisible = stage >= line.id;
              return (
                <motion.div
                  key={line.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: isVisible ? 1 : 0.15, x: isVisible ? 0 : -10 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center justify-between text-xs font-mono px-3 py-1.5 rounded bg-navy-950/60 border border-navy-900"
                >
                  <div className="flex items-center gap-2 text-slate-300">
                    <Icon className={`w-3.5 h-3.5 ${isVisible ? 'text-reeta-cyan' : 'text-slate-600'}`} />
                    <span className="text-[11px]">{line.text}</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold ${
                      isVisible ? 'text-reeta-success' : 'text-slate-600'
                    }`}
                  >
                    {isVisible ? 'OK' : '...'}
                  </span>
                </motion.div>
              );
            })}
          </div>

          <p className="mt-6 text-[10px] font-mono text-slate-600 tracking-wider uppercase">
            Click anywhere or press Esc to skip
          </p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

