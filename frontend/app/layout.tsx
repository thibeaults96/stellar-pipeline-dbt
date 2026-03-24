import type { Metadata } from 'next'
import { Orbitron, Share_Tech_Mono, Exo_2 } from 'next/font/google'
import './globals.css'

const orbitron = Orbitron({ subsets: ['latin'], variable: '--font-orbitron', weight: ['400', '700'] })
const shareTechMono = Share_Tech_Mono({ subsets: ['latin'], variable: '--font-mono-tech', weight: '400' })
const exo2 = Exo_2({ subsets: ['latin'], variable: '--font-exo' })

export const metadata: Metadata = {
  title: 'Stellar Pipeline — Learn dbt through a sci-fi narrative',
  description: 'Learn dbt through a sci-fi narrative, powered by real dbt + DuckDB',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${orbitron.variable} ${shareTechMono.variable} ${exo2.variable} bg-void`}>
        {children}
      </body>
    </html>
  )
}
