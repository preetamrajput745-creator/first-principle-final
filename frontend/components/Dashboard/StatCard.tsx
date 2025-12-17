'use client';

import { LucideIcon } from 'lucide-react';

interface StatCardProps {
    label: string;
    value: string;
    trend?: string;
    icon: LucideIcon;
    color: 'blue' | 'green' | 'purple' | 'orange';
}

const colorMap = {
    blue: 'from-blue-500 to-cyan-400',
    green: 'from-green-500 to-emerald-400',
    purple: 'from-purple-500 to-pink-400',
    orange: 'from-orange-500 to-red-400',
};

const bgMap = {
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
    orange: 'bg-orange-500/10 text-orange-400',
};

export default function StatCard({ label, value, trend, icon: Icon, color }: StatCardProps) {
    return (
        <div className="glass-panel p-5 rounded-xl relative overflow-hidden group hover:translate-y-[-2px] transition-transform duration-300">
            {/* Background Glow */}
            <div className={`absolute -right-6 -top-6 w-24 h-24 rounded-full bg-gradient-to-br ${colorMap[color]} blur-2xl opacity-10 group-hover:opacity-20 transition-opacity`}></div>

            <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                    <div className={`p-2.5 rounded-lg ${bgMap[color]}`}>
                        <Icon size={20} />
                    </div>
                    {trend && (
                        <span className="px-2 py-0.5 rounded text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                            {trend}
                        </span>
                    )}
                </div>

                <div className="text-2xl font-bold text-white mb-1 tracking-tight">{value}</div>
                <div className="text-sm text-gray-400 font-medium">{label}</div>
            </div>
        </div>
    );
}
