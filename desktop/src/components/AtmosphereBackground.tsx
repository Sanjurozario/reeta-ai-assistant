import React, { useEffect, useRef } from 'react';

export const AtmosphereBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    // Particle field definition
    const PARTICLE_COUNT = 36;
    const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.4 + 0.1,
      vx: (Math.random() - 0.5) * 0.25,
      vy: -Math.random() * 0.35 - 0.1,
      color: Math.random() > 0.4 ? '6, 182, 212' : '96, 165, 250', // Electric cyan or sky blue
    }));

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Render subtle particle network
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        p.x += p.vx;
        p.y += p.vy;

        // Wrap around borders
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color}, ${p.alpha})`;
        ctx.shadowBlur = 8;
        ctx.shadowColor = `rgba(${p.color}, 0.6)`;
        ctx.fill();

        // Connect nearby particles with subtle hairline filaments
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            const lineAlpha = (1 - dist / 100) * 0.12;
            ctx.strokeStyle = `rgba(6, 182, 212, ${lineAlpha})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
      {/* Deep Obsidian Background with Radial Ambient Glow */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#05070D] via-[#070B14] to-[#030508]" />

      {/* Primary Cyan Ambient Light Cone at Top-Center */}
      <div
        className="absolute -top-[15%] left-1/2 -translate-x-1/2 w-[900px] h-[550px] rounded-full blur-[140px] opacity-25 pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(6,182,212,0.45) 0%, rgba(59,130,246,0.15) 50%, transparent 75%)',
        }}
      />

      {/* Secondary Teal/Indigo Base Reflection */}
      <div
        className="absolute -bottom-[20%] left-1/2 -translate-x-1/2 w-[1100px] h-[600px] rounded-full blur-[160px] opacity-15 pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(14,165,233,0.3) 0%, rgba(15,23,42,0.6) 60%, transparent 80%)',
        }}
      />

      {/* Futuristic Subtle Perspective Grid */}
      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(6, 182, 212, 0.4) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(6, 182, 212, 0.4) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 65% 55% at 50% 45%, black 40%, transparent 85%)',
          WebkitMaskImage: 'radial-gradient(ellipse 65% 55% at 50% 45%, black 40%, transparent 85%)',
        }}
      />

      {/* Floating Starlight / Particle Canvas */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full opacity-60" />
    </div>
  );
};

