'use client';

import { Activity, BarChart2, BookOpen, Settings, Zap } from 'lucide-react';

const menuItems = [
    { icon: Zap, label: "Automations", active: true },
    { icon: Activity, label: "Live Signals", active: false },
    { icon: BarChart2, label: "Analytics", active: false },
    { icon: BookOpen, label: "Strategy Logs", active: false },
    { icon: Settings, label: "Configuration", active: false },
];

export default function Sidebar() {
    return (
        <aside className="w-64 h-screen fixed left-0 top-0 bg-[#030712] border-r border-white/5 flex flex-col z-50">
            <div className="p-6 border-b border-white/5 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
                    <Zap className="w-5 h-5 text-white fill-current" />
                </div>
                <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                    First Principle
                </span>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                {menuItems.map((item) => (
                    <button
                        key={item.label}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${item.active
                                ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-lg shadow-blue-500/5'
                                : 'text-gray-400 hover:bg-white/5 hover:text-white'
                            }`}
                    >
                        <item.icon className={`w-5 h-5 ${item.active ? 'text-blue-400' : 'text-gray-500 group-hover:text-white'}`} />
                        <span className="font-medium">{item.label}</span>
                    </button>
                ))}
            </nav>

            <div className="p-4 border-t border-white/5">
                <div className="glass-panel p-4 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400 uppercase font-semibold tracking-wider">System Status</span>
                        <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse"></span>
                    </div>
                    <div className="text-sm font-mono text-green-400">All Systems Operational</div>
                </div>
            </div>
        </aside>
    );
}
