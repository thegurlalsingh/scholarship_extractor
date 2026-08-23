import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Terminal as TerminalIcon, Trash2, Pause, Play, Search, AlertCircle, Wifi, WifiOff } from 'lucide-react';

export default function Terminal() {
  const [logs, setLogs] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [status, setStatus] = useState('connecting'); // connecting, connected, disconnected
  const [filterText, setFilterText] = useState('');
  
  const terminalEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Set up Server-Sent Events (SSE) Connection
  const connectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStatus('connecting');
    const es = new EventSource('http://localhost:8000/logs/stream');
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus('connected');
      console.log('SSE connection to backend logs opened.');
    };

    es.onmessage = (event) => {
      if (isPaused) return;
      if (event.data) {
        setLogs((prev) => {
          const next = [...prev, event.data];
          if (next.length > 800) {
            return next.slice(next.length - 800); // keep memory light
          }
          return next;
        });
      }
    };

    es.onerror = (err) => {
      console.error('SSE Error:', err);
      setStatus('disconnected');
      es.close();
    };
  };

  useEffect(() => {
    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [isPaused]); // reconnect or pause changes this

  // Auto-scroll to bottom
  useEffect(() => {
    if (!isPaused && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isPaused]);

  // Filter logs locally based on search
  const filteredLogs = useMemo(() => {
    if (!filterText) return logs;
    const lower = filterText.toLowerCase();
    return logs.filter((log) => log.toLowerCase().includes(lower));
  }, [logs, filterText]);

  const handleClear = () => {
    setLogs([]);
  };

  const togglePause = () => {
    setIsPaused((p) => !p);
  };

  return (
    <div className="p-8 space-y-6 select-none max-w-6xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      {/* Header Panel */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-slate-900 text-emerald-450 p-2.5 rounded-xl border border-slate-800 shadow-sm">
            <TerminalIcon size={24} className="stroke-[2.5]" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Console Terminal</h2>
            <p className="text-xs text-slate-500 mt-1 font-medium">Real-time execution outputs from backend crawlers, classification, and validation workers.</p>
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-4 text-xs font-semibold uppercase tracking-wider">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${
            status === 'connected' ? 'bg-emerald-50 text-emerald-700 border-emerald-250' :
            status === 'connecting' ? 'bg-amber-50 text-amber-700 border-amber-250 animate-pulse' :
            'bg-rose-50 text-rose-700 border-rose-250'
          }`}>
            {status === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span>{status}</span>
          </div>
        </div>
      </div>

      {/* Control bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center justify-between shrink-0 gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Filter logs (e.g. STAGE, Supabase, Error)..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 border border-slate-250 rounded-lg text-xs bg-slate-50/30 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-sans"
          />
        </div>

        <div className="flex items-center gap-3">
          {/* Pause/Resume feed */}
          <button
            onClick={togglePause}
            className={`flex items-center gap-2 px-3 py-1.5 border rounded-lg text-xs font-bold shadow-sm transition-all active:scale-95 ${
              isPaused 
                ? 'bg-emerald-55 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200' 
                : 'bg-white hover:bg-slate-55 border-slate-250 text-slate-700'
            }`}
          >
            {isPaused ? <Play size={13} className="fill-emerald-700" /> : <Pause size={13} className="fill-slate-700" />}
            <span>{isPaused ? 'Resume Output' : 'Pause Stream'}</span>
          </button>

          {/* Clear console */}
          <button
            onClick={handleClear}
            className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-250 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 text-slate-700 rounded-lg text-xs font-bold shadow-sm transition-all active:scale-95"
          >
            <Trash2 size={13} />
            <span>Clear Terminal</span>
          </button>

          {/* Manual Reconnection */}
          {status === 'disconnected' && (
            <button
              onClick={connectSSE}
              className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-sm transition-all active:scale-95"
            >
              <span>Reconnect</span>
            </button>
          )}
        </div>
      </div>

      {/* Terminal Output Container */}
      <div className="flex-1 bg-slate-950 rounded-xl p-5 shadow-inner border border-slate-800 flex flex-col min-h-0">
        <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-3 shrink-0 text-[10px] font-mono text-slate-500 uppercase tracking-widest select-none">
          <span>logs console feed (max 800 lines)</span>
          <span>utf-8 stdout</span>
        </div>
        
        <div className="flex-1 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1.5 pr-2 select-text selection:bg-slate-800 selection:text-white">
          {filteredLogs.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500 italic select-none">
              {filterText ? 'No log lines matches filter query.' : 'Console is waiting for execution logs...'}
            </div>
          ) : (
            filteredLogs.map((log, index) => {
              // Highlight stages or warnings
              const isStage = log.startsWith('===') || log.includes('STAGE');
              const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('failed');
              const isSuccess = log.toLowerCase().includes('success') || log.toLowerCase().includes('completed') || log.includes('✓');

              return (
                <div key={index} className={`whitespace-pre-wrap break-all ${
                  isStage ? 'text-indigo-400 font-bold border-y border-slate-900/60 py-1 my-1.5' :
                  isError ? 'text-rose-400' :
                  isSuccess ? 'text-emerald-400' :
                  'text-slate-350'
                }`}>
                  {log}
                </div>
              );
            })
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
}
