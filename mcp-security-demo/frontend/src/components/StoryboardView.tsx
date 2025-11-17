import { STORYBOARD_STAGES } from '../data/storyboard'
import { StoryboardStageCard } from './StoryboardStageCard'

export function StoryboardView() {
  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-slate-900 to-black p-6 text-slate-100 shadow-xl shadow-emerald-900/20">
        <h2 className="text-2xl font-semibold">Guided Storyboard</h2>
        <p className="mt-2 text-slate-300">
          Clone the repo, run the demo, and click through each stage. Every panel weaves the narratives in
          <span className="font-semibold text-emerald-300"> future_state.md</span> into live telemetry you can replay on demand.
        </p>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Launch scenarios directly from each stage—no manual choreography required.</li>
          <li>Watch the audit feed render in the same card so the “shock moment” is inseparable from the narrative.</li>
          <li>Use the code pointers and docs links to tweak policies, rerun, and teach with source-in-hand.</li>
        </ul>
      </div>

      {STORYBOARD_STAGES.map((stage) => (
        <StoryboardStageCard key={stage.id} stage={stage} />
      ))}
    </div>
  )
}

