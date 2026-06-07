'use client'

import { useState } from 'react'
import type { Quiz } from '@/hooks/useGameApi'

export default function QuizModal({
  quiz,
  onContinue,
  onSkip,
  continueLabel,
}: {
  quiz: Quiz
  onContinue: () => void
  onSkip: () => void
  continueLabel?: string
}) {
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [reveal, setReveal] = useState(false)
  const [score, setScore] = useState(0)

  const total = quiz.questions.length
  const q = quiz.questions[index]
  const isLast = index === total - 1

  const submit = () => {
    if (selected === null) return
    if (selected === q.correct) setScore(s => s + 1)
    setReveal(true)
  }

  const next = () => {
    setIndex(i => i + 1)
    setSelected(null)
    setReveal(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-void/90 backdrop-blur-sm">
      <div className="bg-panel border border-panel-border rounded-lg p-8 max-w-xl w-full mx-4 animate-fade-in">
        <div className="flex items-center justify-between mb-4">
          <div className="font-orbitron text-xs text-stellar-text-dim tracking-widest">
            CHECK FOR UNDERSTANDING
          </div>
          <div className="font-mono-tech text-xs text-stellar-text-dim">
            {index + 1} / {total}
          </div>
        </div>

        <h2 className="font-orbitron text-lg text-accent mb-1">{quiz.levelTitle}</h2>
        <p className="font-exo text-sm text-stellar-text-bright mb-6 leading-relaxed">
          {q.question}
        </p>

        <div className="space-y-2 mb-6">
          {q.options.map((opt, i) => {
            const isSelected = selected === i
            const isCorrect = reveal && i === q.correct
            const isWrong = reveal && isSelected && i !== q.correct
            const base =
              'w-full text-left px-4 py-3 rounded border font-exo text-sm transition-colors'
            const cls = isCorrect
              ? 'border-stellar-green bg-stellar-green/10 text-stellar-green'
              : isWrong
                ? 'border-stellar-red bg-stellar-red/10 text-stellar-red'
                : isSelected
                  ? 'border-accent bg-accent/10 text-stellar-text-bright'
                  : 'border-panel-border text-stellar-text hover:border-accent hover:text-stellar-text-bright'
            return (
              <button
                key={i}
                disabled={reveal}
                onClick={() => setSelected(i)}
                className={`${base} ${cls} ${reveal ? 'cursor-default' : ''}`}
              >
                <span className="font-mono-tech text-xs text-stellar-text-dim mr-2">
                  {String.fromCharCode(65 + i)}.
                </span>
                {opt}
              </button>
            )
          })}
        </div>

        {reveal && q.explanation && (
          <div className="mb-6 p-3 border-l-2 border-accent bg-deep">
            <p className="font-exo text-xs text-stellar-text leading-relaxed">
              {q.explanation}
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            onClick={onSkip}
            className="px-3 py-2 text-stellar-text-dim font-mono-tech text-xs hover:text-stellar-text transition-colors"
          >
            Skip quiz
          </button>

          {!reveal ? (
            <button
              onClick={submit}
              disabled={selected === null}
              className="px-4 py-2 bg-accent text-void font-orbitron text-sm rounded hover:bg-accent/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Submit
            </button>
          ) : !isLast ? (
            <button
              onClick={next}
              className="px-4 py-2 bg-accent text-void font-orbitron text-sm rounded hover:bg-accent/80 transition-colors"
            >
              Next question ▶
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="font-mono-tech text-xs text-stellar-text-dim">
                Score: {score} / {total}
              </span>
              <button
                onClick={onContinue}
                className="px-4 py-2 bg-accent text-void font-orbitron text-sm rounded hover:bg-accent/80 transition-colors"
              >
                {continueLabel ?? 'Continue ▶'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
