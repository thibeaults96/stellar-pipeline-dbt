'use client'
import { useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

export default function CodeEditor({ filePath, content, language, readOnly, onSave }: {
  filePath: string; content: string; language: string; readOnly: boolean; onSave: (content: string) => void
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const editorRef = useRef<any>(null)

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMount = useCallback((editor: any, monaco: any) => {
    editorRef.current = editor
    editor.addAction({
      id: 'save-file', label: 'Save File',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
      run: () => onSave(editor.getValue()),
    })
    monaco.editor.defineTheme('stellar-dark', {
      base: 'vs-dark', inherit: true,
      rules: [
        { token: 'keyword', foreground: '569cd6' },
        { token: 'string', foreground: 'ce9178' },
        { token: 'comment', foreground: '4a6070', fontStyle: 'italic' },
      ],
      colors: {
        'editor.background': '#080b14',
        'editor.foreground': '#c8d8e8',
        'editorLineNumber.foreground': '#4a6070',
        'editor.selectionBackground': '#1e3a4a',
        'editor.lineHighlightBackground': '#0d1220',
      },
    })
    monaco.editor.setTheme('stellar-dark')
  }, [onSave])

  const handleBlur = useCallback(() => {
    if (editorRef.current && !readOnly) onSave(editorRef.current.getValue())
  }, [onSave, readOnly])

  return (
    <div className="h-full relative" onBlur={handleBlur}>
      {readOnly && (
        <div className="absolute top-2 right-2 z-10 bg-stellar-amber/20 text-stellar-amber text-xs px-2 py-0.5 rounded font-mono-tech">
          READ ONLY
        </div>
      )}
      <MonacoEditor
        key={filePath}
        defaultValue={content} language={language} theme="stellar-dark"
        onMount={handleMount}
        options={{
          fontSize: 12, fontFamily: "'Share Tech Mono', monospace",
          minimap: { enabled: false }, scrollBeyondLastLine: false, wordWrap: 'on',
          readOnly, lineNumbers: 'on', padding: { top: 8 }, automaticLayout: true,
        }}
      />
    </div>
  )
}
