'use client';

import { ArrowRight, Check, X, Clock, TrendingUp, TrendingDown } from 'lucide-react';

interface SignalProps {
    id: string;
    symbol: string;
    timestamp: string;
    score: number;
    status: string;
    payload: any;
    realized_slippage?: number;
    onAction: (id: string, action: 'confirm' | 'reject') => void;
}

export default function SignalCard({ id, symbol, timestamp, score, status, payload, realized_slippage, onAction }: SignalProps) {
    const isBearish = payload?.type?.includes('BEARISH');
    const date = new Date(timestamp);
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return (
        <div className="glass-panel rounded-xl p-0 overflow-hidden group hover:border-blue-500/30 transition-all duration-300">
            <div className="p-5">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isBearish ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
                            }`}>
                            {isBearish ? <TrendingDown size={20} /> : <TrendingUp size={20} />}
                        </div>
                        <div>
                            <h4 className="font-bold text-lg text-white tracking-wide">{symbol}</h4>
                            <div className="flex items-center gap-2 text-xs text-gray-400">
                                <Clock size={12} />
                                <span>{timeStr}</span>
                            </div>
                        </div>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-bold border ${score >= 80 ? 'bg-green-500/10 border-green-500/20 text-green-400' :
                        score >= 50 ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                            'bg-gray-500/10 border-gray-500/20 text-gray-400'
                        }`}>
                        Score: {score}
                    </div>
                </div>

                <div className="flex justify-between items-end">
                    <div>
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Signal Price</div>
                        <div className="text-2xl font-mono text-white flex items-baseline gap-1">
                            <span className="text-gray-500 text-sm">$</span>
                            {(payload?.price || 0).toFixed(2)}
                        </div>
                    </div>

                    {status === 'new' ? (
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 translate-y-2 group-hover:translate-y-0">
                            <button
                                onClick={() => onAction(id, 'reject')}
                                className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white transition-colors border border-red-500/20"
                                title="Reject"
                            >
                                <X size={18} />
                            </button>
                            <button
                                onClick={() => onAction(id, 'confirm')}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 text-white font-semibold hover:bg-green-400 transition-colors shadow-lg shadow-green-500/20"
                            >
                                <Check size={18} />
                                <span>Approve</span>
                            </button>
                        </div>
                    ) : (
                        <div className="flex flex-col items-end gap-1">
                            <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-gray-300">
                                {status.toUpperCase()}
                            </div>
                            {realized_slippage !== undefined && realized_slippage !== null && (
                                <div className={`text-[10px] font-mono ${realized_slippage > 0.0003 ? 'text-red-400' : 'text-gray-500'}`}>
                                    Slippage: {(realized_slippage * 10000).toFixed(1)} bps
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Progress Bar (Fake confidence meter) */}
            <div className="h-1 w-full bg-gray-800">
                <div
                    className={`h-full ${isBearish ? 'bg-red-500' : 'bg-green-500'}`}
                    style={{ width: `${score}%` }}
                ></div>
            </div>
        </div>
    );
}
