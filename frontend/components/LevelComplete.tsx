'use client'

export default function LevelComplete({ badge, xpEarned, onDismiss }: {
  badge: { emoji: string; name: string }; xpEarned: number; onDismiss: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-void/90 backdrop-blur-sm">
      <div className="bg-panel border border-panel-border rounded-lg p-8 max-w-md text-center animate-fade-in">
        <div className="text-6xl mb-4">{badge.emoji}</div>
        <h2 className="font-orbitron text-xl text-accent mb-1">MISSION COMPLETE</h2>
        <h3 className="font-orbitron text-sm text-stellar-text-bright mb-2">{badge.name}</h3>
        <div className="flex items-center justify-center gap-2 mb-6">
          <span className="font-orbitron text-2xl text-accent">+{xpEarned}</span>
          <span className="font-mono-tech text-sm text-stellar-text-dim">XP</span>
        </div>
        <button onClick={onDismiss}
          className="px-4 py-2 bg-accent text-void font-orbitron text-sm rounded hover:bg-accent/80 transition-colors">
          Continue
        </button>
      </div>
    </div>
  )
}
