'use client';

import { Play, Pause, Server, Activity } from 'lucide-react';

interface AutomationProps {
    id: string;
    name: string;
    description: string;
    status: string;
    onToggle: (id: string, status: string) => void;
    onSelect: (id: string) => void;
}

export default function AutomationRow({ id, name, description, status, onToggle, onSelect }: AutomationProps) {
    const isActive = status === 'active';

    return (
        <div
            onClick={() => onSelect(id)}
            className="glass-panel p-4 rounded-xl flex items-center justify-between group cursor-pointer hover:bg-white/[0.03] transition-colors"
        >
            <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${isActive
                        ? 'bg-blue-500/10 border-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.15)]'
                        : 'bg-gray-800 border-white/5 text-gray-500'
                    }`}>
                    <Server size={24} />
                </div>
                <div>
                    <h3 className="font-bold text-white group-hover:text-blue-400 transition-colors">{name}</h3>
                    <p className="text-sm text-gray-400">{description}</p>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <div className="text-right hidden sm:block">
                    <div className="text-xs text-gray-500">Uptime</div>
                    <div className="font-mono text-sm text-green-400">99.9%</div>
                </div>

                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggle(id, status);
                    }}
                    className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${isActive
                            ? 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                            : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-600/20'
                        }`}
                >
                    {isActive ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
                </button>
            </div>
        </div>
    );
}
