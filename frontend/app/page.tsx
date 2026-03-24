'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import StartMenu from '@/components/StartMenu'

const GameShell = dynamic(() => import('@/components/GameShell'), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-screen flex items-center justify-center bg-void">
      <div className="text-center">
        <div className="font-orbitron text-accent text-2xl mb-2 tracking-widest">
          STELLAR <span className="text-stellar-text-dim">{"//"}</span> PIPELINE
        </div>
        <div className="font-exo text-stellar-text-dim text-sm">
          Initializing systems...
        </div>
      </div>
    </div>
  ),
})

export default function Home() {
  const [started, setStarted] = useState(false)

  if (!started) {
    return <StartMenu onStart={() => setStarted(true)} />
  }

  return <GameShell />
}
