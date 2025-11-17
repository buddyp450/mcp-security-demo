import { StoryboardView } from './components/StoryboardView'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 p-6 text-slate-100">
      <header className="space-y-4 border-b border-slate-800 pb-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-semibold">MCP Security Demo</h1>
        </div>
      </header>

      <section className="mt-6">
        <StoryboardView />
      </section>
    </div>
  )
}

export default App
