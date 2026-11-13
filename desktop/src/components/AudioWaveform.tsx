import React from 'react';
import { motion } from 'framer-motion';

interface AudioWaveformProps {
  isListening: boolean;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({ isListening }) => {
  // Symmetrical bar counts and baseline heights
  const bars = [12, 18, 26, 38, 54, 72, 88, 100, 88, 72, 54, 38, 26, 18, 12];

  if (!isListening) return null;

  return (
    <div className="flex items-center justify-center gap-1.5 h-12 px-6 py-2 rounded-full bg-navy-950/60 border border-reeta-cyan/40 shadow-lg shadow-reeta-cyan/15 backdrop-blur-md">
      <span className="text-[10px] font-mono tracking-widest text-reeta-cyan uppercase mr-2 flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-reeta-cyan animate-ping inline-block" />
        VOICE SENSOR
      </span>

      <div className="flex items-center gap-[3px] h-8">
        {bars.map((maxHeight, i) => (
          <motion.div
            key={i}
            className="w-[3px] rounded-full bg-gradient-to-t from-reeta-cyan to-reeta-electric shadow-sm shadow-reeta-cyan/50"
            animate={{
              height: [
                `${Math.max(6, maxHeight * 0.2)}%`,
                `${maxHeight}%`,
                `${Math.max(6, maxHeight * 0.4)}%`,
              ],
            }}
            transition={{
              duration: 0.45 + (i % 5) * 0.08,
              repeat: Infinity,
              repeatType: 'reverse',
              ease: 'easeInOut',
              delay: (i * 0.04) % 0.3,
            }}
          />
        ))}
      </div>

      <span className="text-[10px] font-mono text-slate-400 uppercase ml-2">
        "HEY REETA"
      </span>
    </div>
  );
};

