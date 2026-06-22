import { useEffect, useState } from 'react'
import {
  listBrokerConnections,
  createBrokerConnection,
  deleteBrokerConnection,
  testBrokerConnection,
  getBrokerWizardRecommend,
} from '@/services/api'
import {
  Settings,
  Plus,
  Trash2,
  Shield,
  ShieldAlert,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Wallet,
  Landmark,
  Bitcoin,
  Globe,
  HelpCircle,
} from 'lucide-react'

interface BrokerConnection {
  id: number
  broker_name: string
  user_label?: string
  is_paper: boolean
  is_active: boolean
  created_at?: string
  encrypted?: boolean
}

const BROKER_ICONS: Record<string, React.ElementType> = {
  alpaca: Landmark,
  binance: Bitcoin,
  oanda: Globe,
  ibkr: Wallet,
}

export default function SettingsPage() {
  const [connections, setConnections] = useState<BrokerConnection[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [showWizard, setShowWizard] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [testResult, setTestResult] = useState<any>(null)

  // Add form
  const [addBroker, setAddBroker] = useState('alpaca')
  const [addLabel, setAddLabel] = useState('')
  const [addKey, setAddKey] = useState('')
  const [addSecret, setAddSecret] = useState('')
  const [addPassphrase, setAddPassphrase] = useState('')
  const [addPaper, setAddPaper] = useState(true)
  const [addPassword, setAddPassword] = useState('')

  // Wizard state
  const [wizLocation, setWizLocation] = useState('us')
  const [wizAsset, setWizAsset] = useState('stock')
  const [wizCapital, setWizCapital] = useState('small')
  const [wizFee, setWizFee] = useState(false)
  const [wizResult, setWizResult] = useState<any>(null)

  const fetchConnections = async () => {
    try {
      const data = await listBrokerConnections()
      setConnections(data || [])
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchConnections()
  }, [])

  const handleAdd = async () => {
    try {
      await createBrokerConnection({
        broker_name: addBroker,
        user_label: addLabel || undefined,
        api_key: addKey || undefined,
        api_secret: addSecret || undefined,
        passphrase: addPassphrase || undefined,
        is_paper: addPaper,
        master_password: addPassword || undefined,
      })
      setShowAdd(false)
      resetAddForm()
      fetchConnections()
    } catch (e) {
      console.error(e)
    }
  }

  const resetAddForm = () => {
    setAddBroker('alpaca')
    setAddLabel('')
    setAddKey('')
    setAddSecret('')
    setAddPassphrase('')
    setAddPaper(true)
    setAddPassword('')
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Remove this connection?')) return
    try {
      await deleteBrokerConnection(id)
      fetchConnections()
    } catch (e) {
      console.error(e)
    }
  }

  const handleTest = async (id: number) => {
    setTestingId(id)
    setTestResult(null)
    try {
      const result = await testBrokerConnection(id)
      setTestResult(result)
    } catch (e) {
      setTestResult({ success: false, error: String(e) })
    } finally {
      setTestingId(null)
    }
  }

  const handleWizard = async () => {
    try {
      const result = await getBrokerWizardRecommend({
        location: wizLocation,
        asset_class: wizAsset,
        capital: wizCapital,
        fee_sensitive: String(wizFee),
      })
      setWizResult(result)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="p-8">
      <header className="mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Settings size={24} className="text-accent" />
          Settings
        </h2>
        <p className="text-sm text-muted mt-1">Manage broker connections and platform preferences</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Broker connections */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted">Broker Connections</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setShowWizard(true)}
                className="flex items-center gap-1.5 bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              >
                <HelpCircle size={12} />
                Broker Wizard
              </button>
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-1.5 bg-accent/10 text-accent hover:bg-accent/20 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              >
                <Plus size={12} />
                Add Connection
              </button>
            </div>
          </div>

          {connections.map((conn) => {
            const Icon = BROKER_ICONS[conn.broker_name] || Wallet
            return (
              <div
                key={conn.id}
                className="bg-elevated border border-border rounded-lg p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center">
                    <Icon size={18} className="text-accent" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">
                      {conn.user_label || conn.broker_name.toUpperCase()}
                    </div>
                    <div className="text-[11px] text-muted flex items-center gap-2">
                      <span className="capitalize">{conn.broker_name}</span>
                      {conn.is_paper && <span className="text-accent">Paper</span>}
                      {conn.encrypted ? (
                        <span className="flex items-center gap-0.5 text-accent">
                          <Shield size={10} /> Encrypted
                        </span>
                      ) : (
                        <span className="flex items-center gap-0.5 text-warning">
                          <ShieldAlert size={10} /> Plain
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTest(conn.id)}
                    disabled={testingId === conn.id}
                    className="text-xs bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-2 py-1 rounded transition-colors disabled:opacity-50"
                  >
                    {testingId === conn.id ? 'Testing...' : 'Test'}
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    className="text-muted hover:text-danger p-1 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}

          {testResult && (
            <div
              className={`bg-surface border rounded-lg p-3 flex items-center gap-2 text-sm ${
                testResult.success ? 'border-accent/30 text-accent' : 'border-danger/30 text-danger'
              }`}
            >
              {testResult.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
              {testResult.success
                ? `Connected — account status: ${testResult.account || 'ok'}`
                : testResult.error || `Failed (status ${testResult.status_code})`}
            </div>
          )}

          {connections.length === 0 && (
            <div className="text-center py-8 text-muted">
              <Wallet size={24} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">No broker connections configured.</p>
              <p className="text-xs mt-1">Add a connection to enable live or paper trading.</p>
            </div>
          )}
        </div>

        {/* Info panel */}
        <div className="bg-elevated border border-border rounded-lg p-5 h-fit">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3">Security Notes</h3>
          <div className="space-y-3 text-xs text-muted">
            <p>
              API keys are stored locally in SQLite. You can encrypt them with a master password using Fernet encryption, or store them in plain text with a warning.
            </p>
            <p>
              <strong className="text-text">Recommended:</strong> Always use a master password for live trading keys. Paper trading keys are lower risk.
            </p>
            <p>
              EchoTrader never transmits keys to external servers. All broker communication happens directly from your machine.
            </p>
          </div>
        </div>
      </div>

      {/* Add Connection Modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-border rounded-xl w-full max-w-md shadow-xl">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">Add Broker Connection</h3>
            </div>
            <div className="p-6 space-y-3">
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Broker</label>
                <select
                  value={addBroker}
                  onChange={(e) => setAddBroker(e.target.value)}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                >
                  <option value="alpaca">Alpaca Markets (Stocks/ETFs)</option>
                  <option value="binance">Binance (Crypto)</option>
                  <option value="oanda">OANDA (Forex)</option>
                  <option value="ibkr">Interactive Brokers (Multi-asset)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Label (optional)</label>
                <input
                  value={addLabel}
                  onChange={(e) => setAddLabel(e.target.value)}
                  placeholder="My Alpaca Paper"
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">API Key</label>
                <input
                  value={addKey}
                  onChange={(e) => setAddKey(e.target.value)}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">API Secret</label>
                <input
                  type="password"
                  value={addSecret}
                  onChange={(e) => setAddSecret(e.target.value)}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent"
                />
              </div>
              {(addBroker === 'binance') && (
                <div>
                  <label className="text-xs text-muted uppercase block mb-1">Passphrase (if required)</label>
                  <input
                    type="password"
                    value={addPassphrase}
                    onChange={(e) => setAddPassphrase(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent"
                  />
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  id="paper"
                  type="checkbox"
                  checked={addPaper}
                  onChange={(e) => setAddPaper(e.target.checked)}
                  className="accent-accent"
                />
                <label htmlFor="paper" className="text-sm text-muted">Paper / Sandbox account</label>
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Master Password (optional — leave blank to store plain)</label>
                <input
                  type="password"
                  value={addPassword}
                  onChange={(e) => setAddPassword(e.target.value)}
                  placeholder="Encrypt keys at rest"
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
                {!addPassword && (
                  <p className="text-[10px] text-warning mt-1">Warning: storing API keys without encryption</p>
                )}
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-border bg-surface/50">
              <button
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 rounded-md text-sm text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light"
              >
                Save Connection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Broker Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-border rounded-xl w-full max-w-lg shadow-xl max-h-[90vh] overflow-auto">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 className="text-lg font-semibold">Broker Wizard</h3>
              <button onClick={() => { setShowWizard(false); setWizResult(null); }} className="text-muted hover:text-text">
                ✕
              </button>
            </div>
            <div className="p-6 space-y-4">
              {!wizResult ? (
                <>
                  <div>
                    <label className="text-xs text-muted uppercase block mb-1">Where are you located?</label>
                    <select
                      value={wizLocation}
                      onChange={(e) => setWizLocation(e.target.value)}
                      className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                    >
                      <option value="us">United States</option>
                      <option value="ca">Canada</option>
                      <option value="eu">Europe</option>
                      <option value="uk">United Kingdom</option>
                      <option value="au">Australia</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted uppercase block mb-1">Primary asset class</label>
                    <select
                      value={wizAsset}
                      onChange={(e) => setWizAsset(e.target.value)}
                      className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                    >
                      <option value="stock">US Stocks / ETFs</option>
                      <option value="crypto">Cryptocurrency</option>
                      <option value="forex">Forex (FX)</option>
                      <option value="commodity">Commodities</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted uppercase block mb-1">Capital size</label>
                    <select
                      value={wizCapital}
                      onChange={(e) => setWizCapital(e.target.value)}
                      className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                    >
                      <option value="small">Under $25K</option>
                      <option value="medium">$25K – $100K</option>
                      <option value="large">Over $100K</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      id="fee"
                      type="checkbox"
                      checked={wizFee}
                      onChange={(e) => setWizFee(e.target.checked)}
                      className="accent-accent"
                    />
                    <label htmlFor="fee" className="text-sm text-muted">I am fee-sensitive (prefer commission-free)</label>
                  </div>
                  <button
                    onClick={handleWizard}
                    className="w-full bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light"
                  >
                    Get Recommendations
                  </button>
                </>
              ) : (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold">Recommended for you</h4>
                  {(wizResult.recommendations || []).map((rec: any, idx: number) => (
                    <div key={idx} className="bg-elevated border border-border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold text-sm">{rec.name}</div>
                        <a
                          href={rec.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-accent text-xs flex items-center gap-1 hover:underline"
                        >
                          Sign up <ExternalLink size={10} />
                        </a>
                      </div>
                      <p className="text-xs text-muted">{rec.why}</p>
                      <div className="flex gap-2 mt-2">
                        {rec.paper && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">Free paper trading</span>
                        )}
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-muted">{rec.broker}</span>
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={() => setWizResult(null)}
                    className="text-xs text-muted hover:text-text"
                  >
                    ← Back to questions
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
