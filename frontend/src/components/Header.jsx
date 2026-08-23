import React from 'react';
import { RefreshCw } from 'lucide-react';

export default function Header({ lastUpdated, isUpdating, onRefresh }) {
  const formatTime = (isoString) => {
    if (!isoString) return 'Never checked';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch (e) {
      return isoString;
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 px-8 py-5 sticky top-0 z-10 flex items-center justify-between shadow-sm select-none">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight leading-none">
          Scholarship Automation Dashboard
        </h2>
        <p className="text-sm text-slate-500 mt-1.5 font-normal">
          Discover, verify and continuously monitor scholarship opportunities.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <span className="text-xs text-slate-400 font-semibold block uppercase tracking-wider">
            Last Checked
          </span>
          <span className="text-sm text-slate-700 font-medium font-sans">
            {isUpdating ? (
              <span className="text-indigo-600 font-semibold animate-pulse-slow">Updating...</span>
            ) : (
              formatTime(lastUpdated)
            )}
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isUpdating}
          className={`flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 text-slate-700 hover:text-slate-900 rounded-lg text-sm font-semibold transition-all shadow-sm ${
            isUpdating ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'
          }`}
        >
          <RefreshCw size={15} className={`${isUpdating ? 'animate-spin text-indigo-600' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
}
