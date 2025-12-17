'use client';

import { useEffect, useState, useRef } from 'react';
import Sidebar from '../components/Layout/Sidebar';
import StatCard from '../components/Dashboard/StatCard';
import SignalCard from '../components/Dashboard/SignalCard';
import AutomationRow from '../components/Dashboard/AutomationRow';
import { Wallet, Bell, Search, DollarSign, Activity, BarChart3, Fingerprint, RefreshCw } from 'lucide-react';

// ➤ ARCHITECTURE FIX 1: Configurable API URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Automation {
  id: string;
  name: string;
  slug: string;
  status: string;
  description: string;
  config: any;
}

interface Signal {
  id: string;
  symbol: string;
  timestamp: string;
  score: number;
  status: string;
  payload: any;
  realized_slippage?: number;
}

export default function Home() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); // ➤ ARCHITECTURE FIX 2: Explicit Error State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAuto, setNewAuto] = useState({ name: '', slug: '', description: '' });

  // Use refs to prevent state updates on unmounted component
  const mounted = useRef(true);

  const fetchAutomations = async (signal?: AbortSignal) => {
    try {
      const res = await fetch(`${API_URL}/automations`, { signal });
      if (!res.ok) throw new Error(`Server Error: ${res.status} ${res.statusText}`);

      const data = await res.json();
      if (mounted.current) {
        setAutomations(data);
        setError(null);
      }
      return data;
    } catch (e: any) {
      if (e.name === 'AbortError') return [];

      console.error("API Fetch Error Details:", e);
      if (mounted.current) {
        // Detect connection refused
        if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
          setError(`API Disconnected. Is the backend running at ${API_URL}?`);
        } else {
          setError(e.message);
        }
      }
      return [];
    }
  };

  const fetchSignals = async (autoId: string, signal?: AbortSignal) => {
    try {
      const res = await fetch(`${API_URL}/automations/${autoId}/signals`, { signal });
      if (!res.ok) throw new Error('Failed to fetch signals');

      const data = await res.json();
      if (mounted.current) setSignals(data);
    } catch (e: any) {
      if (e.name !== 'AbortError') console.error(e);
    }
  };

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();

    const init = async () => {
      setLoading(true);
      const autos = await fetchAutomations(controller.signal);
      if (autos.length > 0) {
        await fetchSignals(autos[0].id, controller.signal);
      }
      if (mounted.current) setLoading(false);
    };

    init();

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      // Only poll if no error to avoid console spam
      if (!error && mounted.current) {
        fetchAutomations(controller.signal).then(autos => {
          if (autos.length > 0) fetchSignals(autos[0].id, controller.signal);
        });
      }
    }, 5000);

    return () => {
      mounted.current = false;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  const handleCreate = async () => {
    try {
      await fetch(`${API_URL}/automations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAuto),
      });
      setShowCreateModal(false);
      fetchAutomations();
    } catch (e) {
      alert("Failed to create automation. Check API connection.");
    }
  };

  const toggleStatus = async (id: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    await fetch(`${API_URL}/automations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    fetchAutomations();
  };

  const handleSignalAction = async (id: string, action: 'confirm' | 'reject') => {
    if (action === 'confirm') {
      await fetch(`${API_URL}/signals/${id}/confirm`, { method: 'POST' });
    } else {
      await fetch(`${API_URL}/signals/${id}`, { method: 'DELETE' });
    }
    if (automations.length > 0) fetchSignals(automations[0].id);
  };

  return (
    <div className="min-h-screen bg-[#030712] text-foreground flex">
      <Sidebar />
      <div className="flex-1 ml-64 p-8">
        {/* API STATUS BANNER */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-500 animate-pulse">
            <Activity className="h-5 w-5" />
            <span className="font-semibold">{error}</span>
            <button onClick={() => window.location.reload()} className="ml-auto px-3 py-1 bg-red-500/20 rounded-lg text-sm hover:bg-red-500/30">
              Retry Connection
            </button>
          </div>
        )}

        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Command Center</h1>
            <p className="text-gray-400 text-sm">Welcome back, Trader.</p>
          </div>
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold">
              <Wallet size={18} />
              <span>Connect</span>
            </button>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
              <StatCard label="Total Profit" value="$12,450.20" trend="+12.5%" icon={DollarSign} color="green" />
              <StatCard label="Active Bots" value={automations.length.toString()} icon={Activity} color="blue" />
              <StatCard label="Win Rate" value="68%" trend="+2.4%" icon={BarChart3} color="purple" />
              <StatCard label="Total Forecasts" value="1,204" icon={Fingerprint} color="orange" />
            </div>

            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 lg:col-span-8 space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-blue-500 rounded-full"></span>
                    Live Signal Feed
                  </h2>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {signals.map((signal) => (
                    <SignalCard key={signal.id} {...signal} onAction={handleSignalAction} />
                  ))}
                  {signals.length === 0 && (
                    <div className="glass-panel p-10 text-center text-gray-500">
                      No active signals. Waiting for market data...
                    </div>
                  )}
                </div>
              </div>

              <div className="col-span-12 lg:col-span-4 space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-white">Automations</h2>
                  <button onClick={() => setShowCreateModal(true)} className="text-xs bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg text-blue-400 font-medium border border-blue-500/20">
                    + New Bot
                  </button>
                </div>

                <div className="space-y-4">
                  {automations.map((auto) => (
                    <AutomationRow key={auto.id} {...auto} onToggle={toggleStatus} onSelect={(id) => fetchSignals(id)} />
                  ))}
                  {automations.length === 0 && (
                    <div className="text-center p-8 border border-dashed border-gray-700 rounded-xl text-gray-500">
                      {error ? "System Offline" : "No automations created."}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {showCreateModal && (
          <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center">
            <div className="glass-panel p-8 rounded-2xl w-96 border border-white/10 shadow-2xl">
              <h2 className="text-2xl font-bold mb-6 text-white">Deploy New Bot</h2>
              <div className="space-y-4">
                <input className="w-full bg-[#030712] border border-white/10 rounded-lg p-3 text-white" placeholder="Name" value={newAuto.name} onChange={e => setNewAuto({ ...newAuto, name: e.target.value })} />
                <input className="w-full bg-[#030712] border border-white/10 rounded-lg p-3 text-white" placeholder="Slug" value={newAuto.slug} onChange={e => setNewAuto({ ...newAuto, slug: e.target.value })} />
                <textarea className="w-full bg-[#030712] border border-white/10 rounded-lg p-3 text-white" placeholder="Desc" value={newAuto.description} onChange={e => setNewAuto({ ...newAuto, description: e.target.value })} />
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button onClick={() => setShowCreateModal(false)} className="px-4 py-2 text-gray-400">Cancel</button>
                <button onClick={handleCreate} className="px-6 py-2 bg-blue-600 rounded-lg text-white">Deploy</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
