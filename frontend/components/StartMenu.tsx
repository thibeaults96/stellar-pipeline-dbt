'use client'

import { useState, useEffect } from 'react'

const CRAWL_LINES = [
  { text: "FEDERATION LOGISTICS COMMAND", style: "dim", delay: 0 },
  { text: "OUTER RIM SECTOR // MERIDIAN-9 STATION", style: "dim", delay: 400 },
  { text: "", style: "dim", delay: 800 },
  { text: "YEAR 2847", style: "accent", delay: 1200 },
  { text: "", style: "dim", delay: 1400 },
  { text: "The Federation's cargo tracking system is broken.", style: "normal", delay: 1800 },
  { text: "Raw shipment data is coming in, but nobody's done anything with it.", style: "normal", delay: 2600 },
  { text: "No models. No tests. No reports.", style: "normal", delay: 3400 },
  { text: "The morning briefing is in a few hours.", style: "normal", delay: 4200 },
  { text: "", style: "dim", delay: 4800 },
  { text: "The last analyst, someone named VOSS,", style: "normal", delay: 5200 },
  { text: "set up the project structure and then disappeared.", style: "normal", delay: 6000 },
  { text: "There are flags in the data that nobody can explain.", style: "amber", delay: 6800 },
  { text: "", style: "dim", delay: 7400 },
  { text: "You're Recruit AE-7.", style: "bright", delay: 7800 },
  { text: "You're going to learn dbt.", style: "bright", delay: 8400 },
  { text: "You're going to build the pipeline.", style: "bright", delay: 9000 },
  { text: "And you might figure out what VOSS left behind.", style: "accent", delay: 9600 },
]

const STYLE_MAP: Record<string, string> = {
  dim: "text-stellar-text-dim",
  normal: "text-stellar-text",
  bright: "text-stellar-text-bright",
  accent: "text-accent",
  amber: "text-stellar-amber",
}

type Star = {
  left: string; top: string; width: string; height: string
  animationDelay: string; animationDuration: string; opacity: number
}

export default function StartMenu({ onStart }: { onStart: () => void }) {
  const [visibleLines, setVisibleLines] = useState(0)
  const [showButton, setShowButton] = useState(false)
  // Generate starfield only on the client to avoid SSR/CSR hydration mismatch.
  const [stars, setStars] = useState<Star[]>([])

  useEffect(() => {
    setStars(
      Array.from({ length: 40 }, () => ({
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        width: `${1 + Math.random() * 2}px`,
        height: `${1 + Math.random() * 2}px`,
        animationDelay: `${Math.random() * 4}s`,
        animationDuration: `${2 + Math.random() * 3}s`,
        opacity: 0.3 + Math.random() * 0.5,
      })),
    )
  }, [])

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    for (let i = 0; i < CRAWL_LINES.length; i++) {
      timers.push(setTimeout(() => setVisibleLines(i + 1), CRAWL_LINES[i].delay))
    }

    // Show button after last line
    const lastDelay = CRAWL_LINES[CRAWL_LINES.length - 1].delay
    timers.push(setTimeout(() => setShowButton(true), lastDelay + 1000))

    return () => timers.forEach(clearTimeout)
  }, [])

  // Skip animation on click
  const handleSkip = () => {
    if (!showButton) {
      setVisibleLines(CRAWL_LINES.length)
      setShowButton(true)
    }
  }

  return (
    <div
      className="h-screen w-screen bg-void flex flex-col items-center justify-center overflow-hidden cursor-pointer"
      onClick={handleSkip}
    >
      {/* Starfield background effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {stars.map((s, i) => (
          <div
            key={i}
            className="absolute w-px h-px bg-stellar-text-dim rounded-full animate-pulse-glow"
            style={s}
          />
        ))}
      </div>

      {/* Title */}
      <div className="relative z-10 text-center mb-12">
        <h1 className="font-orbitron text-4xl md:text-5xl tracking-[0.3em] mb-2">
          <span className="text-accent">STELLAR</span>
          <span className="text-stellar-text-dim mx-3">{"//"}</span>
          <span className="text-accent">PIPELINE</span>
        </h1>
        <div className="font-mono-tech text-stellar-text-dim text-xs tracking-widest">
          A DBT TRAINING SIMULATION
        </div>
      </div>

      {/* Intro crawl */}
      <div className="relative z-10 max-w-lg mx-auto px-6 mb-12 min-h-[320px]">
        {CRAWL_LINES.slice(0, visibleLines).map((line, i) => (
          <div
            key={i}
            className={`font-exo text-sm leading-relaxed animate-fade-in ${
              STYLE_MAP[line.style] || "text-stellar-text"
            } ${line.text === "" ? "h-3" : ""}`}
          >
            {line.text}
          </div>
        ))}
      </div>

      {/* Start button */}
      <div className={`relative z-10 transition-all duration-700 ${showButton ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
        <button
          onClick={(e) => { e.stopPropagation(); onStart() }}
          className="group px-8 py-3 border-2 border-accent text-accent font-orbitron text-sm tracking-widest
            rounded hover:bg-accent hover:text-void transition-all duration-300
            hover:shadow-[0_0_20px_rgba(0,212,255,0.3)]"
        >
          BEGIN MISSION
        </button>
        <div className="mt-3 text-center font-mono-tech text-xs text-stellar-text-dim">
          Level 1 // First Day at the Federation
        </div>
      </div>

      {/* Skip hint */}
      {!showButton && visibleLines > 0 && (
        <div className="absolute bottom-6 font-mono-tech text-xs text-stellar-text-dim animate-pulse-glow">
          click to skip
        </div>
      )}
    </div>
  )
}
