import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { CardSkeleton, TableSkeleton } from './Skeleton';
import { Activity, Clock, ShieldAlert, CheckCircle, RefreshCw, AlertTriangle } from 'lucide-react';

export default function Monitoring() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const STALE_THRESHOLD_HOURS = 24;

  const fetchData = async () => {
    try {
      setIsLoading(true);

      // Fetch scholarships joined with monitoring
      const { data: schData, error: schError } = await supabase
        .from('scholarships')
        .select(`
          id,
          title,
          is_active,
          scholarship_monitoring(*)
        `);

      if (schError) throw schError;

      // Fetch latest recheck run
      const { data: runsData, error: runsError } = await supabase
        .from('recheck_runs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1);

      if (runsError) throw runsError;

      setData(schData || []);
      setLatestRun(runsData?.[0] || null);

    } catch (e) {
      console.error('Error fetching monitoring data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Auto-refresh monitoring page every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Compute values
  const monitoringRows = React.useMemo(() => {
    return data.map((s) => {
      const mon = s.scholarship_monitoring?.[0] || {};
      return {
        id: s.id,
        title: s.title,
        is_active: s.is_active,
        last_checked_at: mon.last_checked_at,
        consecutive_failures: mon.consecutive_failures || 0,
      };
    });
  }, [data]);

  // Sort by oldest check first
  const sortedMonitoringRows = React.useMemo(() => {
    const sorted = [...monitoringRows];
    sorted.sort((a, b) => {
      if (!a.last_checked_at) return -1;
      if (!b.last_checked_at) return 1;
      return new Date(a.last_checked_at) - new Date(b.last_checked_at);
    });
    return sorted;
  }, [monitoringRows]);

  // Identify stale scholarships
  const staleRows = React.useMemo(() => {
    const cutoff = new Date(Date.now() - STALE_THRESHOLD_HOURS * 60 * 60 * 1000);
    return monitoringRows.filter((row) => {
      if (!row.last_checked_at) return true; // Never checked is stale
      return new Date(row.last_checked_at) < cutoff;
    });
  }, [monitoringRows]);

  // Calculations for KPI cards
  const totalChecked = monitoringRows.filter((r) => r.last_checked_at).length;
  const totalFailures = monitoringRows.filter((r) => r.consecutive_failures > 0).length;

  const formatTimeAgo = (isoString) => {
    if (!isoString) return 'Never checked';
    const date = new Date(isoString);
    const diffMs = new Date() - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      if (diffMins === 0) return 'Just now';
      return `${diffMins} minutes ago`;
    }
    if (diffHours >= 24) {
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays} days ago (${new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`;
    }
    return `${diffHours} hours ago`;
  };

  const getNextRecheckTime = () => {
    if (!latestRun?.completed_at) return 'Unknown';
    try {
      const lastCheck = new Date(latestRun.completed_at);
      // Next recheck is scheduled 24 hours later
      const nextCheck = new Date(lastCheck.getTime() + 24 * 60 * 60 * 1000);
      return nextCheck.toLocaleString([], {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return 'Unknown';
    }
  };

  return (
    <div className="p-8 space-y-8 select-none">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-50 text-indigo-700 p-2.5 rounded-xl border border-indigo-150 shadow-sm">
            <Activity size={24} className="stroke-[2.5]" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Monitoring Hub</h2>
            <p className="text-xs text-slate-500 mt-1 font-medium">Verify automated cron cycles, check failures, and locate stale entries.</p>
          </div>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-5">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, idx) => <CardSkeleton key={idx} />)
        ) : (
          <>
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Last Recheck</span>
              <span className="text-sm font-bold text-slate-800 block mt-2">
                {latestRun?.completed_at ? new Date(latestRun.completed_at).toLocaleDateString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : 'Never'}
              </span>
              <p className="text-[10px] text-slate-400 mt-1.5 uppercase font-bold tracking-wider">Automated Cycle</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Next Recheck</span>
              <span className="text-sm font-bold text-slate-850 block mt-2">{getNextRecheckTime()}</span>
              <p className="text-[10px] text-slate-400 mt-1.5 uppercase font-bold tracking-wider">Scheduled Cron</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Running Now</span>
              <div className="flex items-center gap-2 mt-2">
                <span className={`w-2.5 h-2.5 rounded-full ${latestRun?.status === 'RUNNING' ? 'bg-blue-500 animate-pulse' : 'bg-slate-350'}`}></span>
                <span className="text-base font-bold text-slate-800">
                  {latestRun?.status === 'RUNNING' ? 'Yes' : 'No'}
                </span>
              </div>
              <p className="text-[10px] text-slate-400 mt-2.5 uppercase font-bold tracking-wider">Background Task</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Checked</span>
              <span className="text-2xl font-extrabold text-slate-800 block mt-1">{totalChecked}</span>
              <p className="text-[10px] text-slate-400 mt-1 uppercase font-bold tracking-wider">Of {data.length} Total</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Failing Checks</span>
              <span className={`text-2xl font-extrabold block mt-1 ${totalFailures > 0 ? 'text-rose-650' : 'text-slate-800'}`}>{totalFailures}</span>
              <p className="text-[10px] text-slate-400 mt-1 uppercase font-bold tracking-wider">Active failures</p>
            </div>
          </>
        )}
      </div>

      {/* Stale Scholarships Warning Box */}
      {!isLoading && staleRows.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-amber-600 mt-0.5 shrink-0" size={20} />
            <div>
              <h3 className="text-sm font-bold text-amber-800 uppercase tracking-wider">Needs Recheck ({staleRows.length})</h3>
              <p className="text-xs text-amber-700 mt-1">
                The following {staleRows.length} scholarship{staleRows.length === 1 ? '' : 's'} haven't been checked in the last {STALE_THRESHOLD_HOURS} hours and may have stale information.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[160px] overflow-y-auto pr-2">
            {staleRows.map((row) => (
              <div
                key={row.id}
                onClick={() => navigate(`/scholarships/${row.id}`)}
                className="bg-white border border-amber-100 hover:border-amber-300 rounded-lg p-3 flex justify-between items-center text-xs font-medium cursor-pointer shadow-sm hover:shadow transition-all"
              >
                <span className="text-slate-800 truncate font-semibold pr-3 max-w-[280px]">{row.title}</span>
                <span className="text-amber-700 shrink-0 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded font-bold font-mono">
                  {row.last_checked_at ? formatTimeAgo(row.last_checked_at) : 'Never Checked'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monitoring Grid / Oldest Checks Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-md font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Clock size={16} className="text-slate-455" />
            Check Schedule (Oldest check first)
          </h3>
          <p className="text-xs text-slate-400 mt-1">Shows full list of recheck tasks. Oldest checks at the top require the most immediate crawl.</p>
        </div>

        {isLoading ? (
          <TableSkeleton rows={6} cols={4} />
        ) : (
          <div className="overflow-x-auto border border-slate-150 rounded-lg">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-xs text-slate-500 font-bold uppercase tracking-wider select-none">
                  <th className="px-6 py-3.5">Scholarship</th>
                  <th className="px-6 py-3.5">Last Checked</th>
                  <th className="px-6 py-3.5">Monitoring Status</th>
                  <th className="px-6 py-3.5">Consecutive Failures</th>
                  <th className="px-6 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-150">
                {sortedMonitoringRows.map((row) => {
                  const isStale = !row.last_checked_at || new Date(row.last_checked_at) < new Date(Date.now() - STALE_THRESHOLD_HOURS * 60 * 60 * 1000);
                  const isAlert = row.consecutive_failures >= 3;
                  const isWarn = row.consecutive_failures > 0 && row.consecutive_failures < 3;

                  return (
                    <tr key={row.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-3.5 font-semibold text-slate-900 max-w-[320px] truncate" title={row.title}>
                        {row.title}
                      </td>
                      <td className="px-6 py-3.5 text-slate-600 font-medium">
                        <span className={isStale ? 'text-amber-700 font-semibold' : 'text-slate-655'}>
                          {formatTimeAgo(row.last_checked_at)}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-1.5 select-none">
                          <span className={`w-2.5 h-2.5 rounded-full ${
                            isAlert ? 'bg-rose-500 animate-pulse' :
                            isWarn ? 'bg-amber-500' :
                            row.is_active ? 'bg-emerald-500' : 'bg-slate-400'
                          }`}></span>
                          <span className={`text-xs font-bold uppercase ${
                            isAlert ? 'text-rose-700' :
                            isWarn ? 'text-amber-700' :
                            row.is_active ? 'text-emerald-700' : 'text-slate-550'
                          }`}>
                            {isAlert ? 'ATTENTION REQUIRED' :
                             isWarn ? 'CHECK WARNING' :
                             row.is_active ? 'HEALTHY' : 'INACTIVE'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5">
                        {row.consecutive_failures > 0 ? (
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold font-mono ${
                            row.consecutive_failures >= 3 ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            {row.consecutive_failures} failures
                          </span>
                        ) : (
                          <span className="text-emerald-600 text-xs font-bold uppercase flex items-center gap-1">
                            <CheckCircle size={13} className="stroke-[2.5]" /> Healthy
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <button
                          onClick={() => navigate(`/scholarships/${row.id}`)}
                          className="text-xs font-bold text-indigo-650 hover:text-indigo-900 border border-slate-200 hover:border-slate-350 px-2.5 py-1.5 rounded-md bg-white hover:bg-slate-50 transition-all shadow-sm"
                        >
                          Audit
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
