import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, GraduationCap, Activity, History, Cpu, Terminal } from 'lucide-react';

export default function Sidebar() {
  const menuItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Scholarships', path: '/scholarships', icon: GraduationCap },
    { name: 'Monitoring', path: '/monitoring', icon: Activity },
    { name: 'Changes', path: '/changes', icon: History },
    { name: 'Pipeline', path: '/pipeline', icon: Cpu },
    { name: 'Terminal', path: '/terminal', icon: Terminal },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-screen sticky top-0 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-850 flex items-center gap-3">
        <div className="bg-indigo-600 text-white p-2 rounded-lg">
          <Cpu size={20} className="stroke-[2.5]" />
        </div>
        <div>
          <h1 className="font-bold text-white text-md tracking-tight leading-none">Scholarship</h1>
          <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Automation</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-6 px-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer / System Status */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Online</span>
          </div>
          <span className="text-[10px] text-slate-600 font-mono">v1.2.0</span>
        </div>
      </div>
    </aside>
  );
}
