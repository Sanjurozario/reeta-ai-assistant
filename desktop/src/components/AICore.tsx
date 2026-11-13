import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../stores/useAppStore';
import { Sparkles, ShieldAlert, CheckCircle2, AlertTriangle, Play, Mic } from 'lucide-react';

interface AICoreProps {
  onCoreClick?: () => void;
}

export const AICore: React.FC<AICoreProps> = ({ onCoreClick }) => {
  const { isListening, activeTask, toggleVoiceListening, audioLevel } = useAppStore();

  const taskStatus = activeTask?.status;
  const isExecuting = taskStatus === 'running';
  const isThinking = taskStatus === 'planning';
  const isCompleted = taskStatus === 'completed';
  const isWaitingApproval = taskStatus === 'waiting_approval';
  const isFailed = taskStatus === 'failed';

  // Compute overall progress if steps exist
  const steps = activeTask?.steps || [];
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const progressPercent = isCompleted ? 100 : steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 0;

  // Determine core visual mode
  const currentMode = isWaitingApproval
    ? 'approval'
    : isFailed
    ? 'failed'
    : isCompleted
    ? 'completed'
    : isExecuting
    ? 'executing'
    : isThinking
    ? 'thinking'
    : isListening
    ? 'listening'
    : 'idle';

  // Color mappings
  const colors = {
    idle: { primary: '#06B6D4', secondary: '#3B82F6', aura: 'rgba(6, 182, 212, 0.25)' },
    listening: { primary: '#22D3EE', secondary: '#06B6D4', aura: 'rgba(34, 211, 238, 0.45)' },
    thinking: { primary: '#818CF8', secondary: '#06B6D4', aura: 'rgba(129, 140, 248, 0.4)' },
    executing: { primary: '#38BDF8', secondary: '#60A5FA', aura: 'rgba(56, 189, 248, 0.35)' },
    completed: { primary: '#10B981', secondary: '#06B6D4', aura: 'rgba(16, 185, 129, 0.35)' },
    approval: { primary: '#F59E0B', secondary: '#EF4444', aura: 'rgba(245, 158, 11, 0.45)' },
    failed: { primary: '#EF4444', secondary: '#F43F5E', aura: 'rgba(239, 68, 68, 0.45)' },
  }[currentMode];

  const handleCoreClick = () => {
    if (onCoreClick) {
      onCoreClick();
    } else {
      toggleVoiceListening();
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center select-none py-4">
      {/* Outer Glow Halo */}
      <motion.div
        className="absolute w-[340px] h-[340px] rounded-full pointer-events-none blur-3xl transition-colors duration-700"
        style={{ background: colors.aura }}
        animate={{
          scale: isListening ? (1.05 + audioLevel * 0.4) : isExecuting ? [1, 1.15, 1] : [1, 1.08, 1],
          opacity: isListening ? (0.6 + audioLevel * 0.3) : 0.45,
        }}
        transition={{
          duration: isListening ? 0.15 : isExecuting ? 2 : 4,
          repeat: isListening ? 0 : Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Interactive Holographic Core Container */}
      <div
        onClick={handleCoreClick}
        className="relative w-64 h-64 sm:w-72 sm:h-72 flex items-center justify-center cursor-pointer group"
        title={isListening ? 'Click to mute voice' : 'Click to activate voice listening'}
      >
        {/* Layer 1: Outermost Orbital Ring (Counter-Clockwise) */}
        <motion.div
          className="absolute inset-0 rounded-full border border-dashed border-reeta-cyan/20 group-hover:border-reeta-cyan/40 transition-colors"
          animate={{ rotate: -360 }}
          transition={{
            duration: isThinking || isExecuting ? 14 : 36,
            repeat: Infinity,
            ease: 'linear',
          }}
        >
          {/* Orbital Satellite Node */}
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-reeta-cyan shadow-md shadow-reeta-cyan/80" />
          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-reeta-blue/60" />
        </motion.div>

        {/* Layer 2: Segmented Holographic Arcs Ring (Clockwise) */}
        <motion.div
          className="absolute inset-4 sm:inset-5 rounded-full pointer-events-none"
          animate={{ rotate: 360 }}
          transition={{
            duration: isThinking ? 6 : isExecuting ? 10 : 22,
            repeat: Infinity,
            ease: 'linear',
          }}
        >
          <svg className="w-full h-full" viewBox="0 0 100 100">
            {/* Arc 1 */}
            <circle
              cx="50"
              cy="50"
              r="47"
              fill="none"
              stroke={colors.primary}
              strokeWidth="1.2"
              strokeDasharray="28 45"
              strokeDashoffset="10"
              strokeOpacity={0.65}
            />
            {/* Arc 2 */}
            <circle
              cx="50"
              cy="50"
              r="47"
              fill="none"
              stroke={colors.secondary}
              strokeWidth="1.2"
              strokeDasharray="18 55"
              strokeDashoffset="65"
              strokeOpacity={0.45}
            />
          </svg>
        </motion.div>

        {/* Layer 3: Inner Telemetry Ring with Pulse */}
        <motion.div
          className="absolute inset-10 sm:inset-12 rounded-full border border-reeta-cyan/30 flex items-center justify-center pointer-events-none"
          animate={{
            rotate: isThinking || isExecuting ? -360 : -180,
            scale: isListening ? [1, 1.04, 0.98, 1] : [1, 1.02, 1],
          }}
          transition={{
            rotate: { duration: 16, repeat: Infinity, ease: 'linear' },
            scale: { duration: isListening ? 0.6 : 3, repeat: Infinity, ease: 'easeInOut' },
          }}
        >
          {/* Coordinate Tick Marks */}
          <div className="absolute top-0 w-0.5 h-2 bg-reeta-cyan/50" />
          <div className="absolute bottom-0 w-0.5 h-2 bg-reeta-cyan/50" />
          <div className="absolute left-0 w-2 h-0.5 bg-reeta-cyan/50" />
          <div className="absolute right-0 w-2 h-0.5 bg-reeta-cyan/50" />
        </motion.div>

        {/* Layer 4: Central Singularity Core Spherical Orb */}
        <motion.div
          className="relative w-28 h-28 sm:w-32 sm:h-32 rounded-full flex flex-col items-center justify-center shadow-2xl overflow-hidden transition-all duration-700"
          style={{
            background: `radial-gradient(circle at 35% 35%, #FFFFFF 0%, ${colors.primary} 30%, ${colors.secondary} 70%, #030712 100%)`,
            boxShadow: `0 0 35px ${colors.aura}, inset 0 0 20px rgba(255,255,255,0.4)`,
          }}
          animate={{
            scale: isListening ? (1.02 + audioLevel * 0.25) : isExecuting ? [1, 1.06, 1] : [1, 1.04, 1],
          }}
          transition={{
            duration: isListening ? 0.1 : isExecuting ? 1.8 : 3.5,
            repeat: isListening ? 0 : Infinity,
            ease: 'easeInOut',
          }}
        >
          {/* Inner Light Flare / Corona */}
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent pointer-events-none" />

          {/* Core Content Overlay based on State */}
          <div className="relative z-10 flex flex-col items-center justify-center text-center p-2 text-obsidian-950 font-mono">
            {isExecuting ? (
              <>
                <span className="text-xl sm:text-2xl font-black tracking-tight">{progressPercent}%</span>
                <span className="text-[9px] font-bold uppercase tracking-wider opacity-85">EXEC</span>
              </>
            ) : isThinking ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                >
                  <Sparkles className="w-6 h-6 text-obsidian-950" />
                </motion.div>
                <span className="text-[9px] font-bold uppercase tracking-wider mt-1 opacity-90">REASON</span>
              </>
            ) : isCompleted ? (
              <>
                <CheckCircle2 className="w-7 h-7 text-obsidian-950" />
                <span className="text-[9px] font-bold uppercase tracking-wider mt-0.5">READY</span>
              </>
            ) : isWaitingApproval ? (
              <>
                <ShieldAlert className="w-7 h-7 text-obsidian-950 animate-bounce" />
                <span className="text-[9px] font-bold uppercase tracking-wider mt-0.5">AUTH</span>
              </>
            ) : isFailed ? (
              <>
                <AlertTriangle className="w-7 h-7 text-obsidian-950" />
                <span className="text-[9px] font-bold uppercase tracking-wider mt-0.5">ALERT</span>
              </>
            ) : isListening ? (
              <>
                <Mic className="w-7 h-7 text-obsidian-950 animate-pulse" />
                <span className="text-[9px] font-bold uppercase tracking-wider mt-0.5">HEARING</span>
              </>
            ) : (
              <>
                <div className="w-3.5 h-3.5 rounded-full bg-obsidian-950/70 mb-1 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                </div>
                <span className="text-[10px] font-black tracking-widest uppercase">REETA</span>
              </>
            )}
          </div>
        </motion.div>
      </div>

      {/* Holographic Status Readout Banner */}
      <div className="mt-4 flex flex-col items-center space-y-1.5 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-950/70 border border-navy-800 shadow-inner">
          <span
            className="w-1.5 h-1.5 rounded-full animate-ping"
            style={{ backgroundColor: colors.primary }}
          />
          <span className="text-[11px] font-mono tracking-widest text-slate-300 uppercase">
            {isWaitingApproval
              ? 'ZERO-TRUST INTERVENTION // AUTHORIZATION REQUIRED'
              : isFailed
              ? 'DAG HALTED // VERIFICATION FAILED'
              : isCompleted
              ? 'DAG COMPLETED // VERIFICATION EVIDENCE SEALED'
              : isExecuting
              ? `AUTONOMOUS EXECUTION IN PROGRESS // ${progressPercent}%`
              : isThinking
              ? 'DECOMPOSING OBJECTIVE // NEURAL REASONING'
              : isListening
              ? 'VOICE SENSOR ENGAGED // LISTENING ("HEY REETA")'
              : 'REETA COGNITIVE CORE // ONLINE & READY'}
          </span>
        </div>

        {/* Active Objective Title Subtitle */}
        {activeTask && (isExecuting || isThinking || isWaitingApproval) && (
          <p className="text-xs font-mono text-reeta-cyan max-w-lg truncate px-4">
            &gt; {activeTask.title}
          </p>
        )}
      </div>
    </div>
  );
};

