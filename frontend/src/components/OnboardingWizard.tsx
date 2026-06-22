import { useState } from 'react'
import {
  TrendingUp,
  LineChart,
  BookOpen,
  Bot,
  BrainCircuit,
  ArrowRight,
  CheckCircle2,
  X,
} from 'lucide-react'

const STEPS = [
  {
    title: 'Welcome to EchoTrader',
    body: 'EchoTrader is a local-first algorithmic trading platform. Your data stays on your machine. Trade stocks, crypto, and forex with custom strategies, paper bots, and AI market intelligence.',
    icon: TrendingUp,
  },
  {
    title: 'Charts & Indicators',
    body: 'View multi-timeframe charts with SMA, EMA, Bollinger Bands, RSI, MACD, and volume. Toggle overlays, mark trades, and analyze trends directly in the browser.',
    icon: LineChart,
  },
  {
    title: 'Journal & Calendar',
    body: 'Keep a structured trading journal with markdown, mood tracking, and trade linking. The calendar view gives you a monthly heatmap of your activity and PnL.',
    icon: BookOpen,
  },
  {
    title: 'Bots & Backtests',
    body: 'Create paper-trading bots that run 24/7 with risk guards. Run backtests with slippage and commission modeling, then optimize parameters with grid search and walk-forward analysis.',
    icon: Bot,
  },
  {
    title: 'AI Intelligence',
    body: 'Let the agent swarm monitor the market for you: News Prodigy tracks RSS sentiment, Financial Analyst evaluates technical bias, and more agents are on the roadmap.',
    icon: BrainCircuit,
  },
]

export default function OnboardingWizard({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0)

  const next = () => {
    if (step < STEPS.length - 1) setStep(step + 1)
    else finish()
  }

  const finish = () => {
    localStorage.setItem('echotrader_onboarded', '1')
    onDone()
  }

  const current = STEPS[step]
  const Icon = current.icon

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4">
      <div className="bg-surface border border-border rounded-xl w-full max-w-lg shadow-2xl relative overflow-hidden">
        {/* Progress */}
        <div className="flex">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 ${i <= step ? 'bg-accent' : 'bg-border'}`}
            />
          ))}
        </div>

        <button
          onClick={finish}
          className="absolute top-3 right-3 text-muted hover:text-text"
          aria-label="Skip onboarding"
        >
          <X size={18} />
        </button>

        <div className="px-8 pt-10 pb-6 text-center">
          <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto mb-4">
            <Icon size={28} className="text-accent" />
          </div>
          <h2 className="text-xl font-bold mb-2">{current.title}</h2>
          <p className="text-sm text-muted leading-relaxed">{current.body}</p>
        </div>

        <div className="px-8 pb-8 flex items-center justify-between">
          <div className="text-xs text-muted">
            {step + 1} / {STEPS.length}
          </div>
          <div className="flex gap-3">
            {step > 0 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 rounded-md text-sm text-muted hover:text-text"
              >
                Back
              </button>
            )}
            <button
              onClick={next}
              className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light flex items-center gap-1"
            >
              {step === STEPS.length - 1 ? (
                <>
                  <CheckCircle2 size={14} /> Get Started
                </>
              ) : (
                <>
                  Next <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
