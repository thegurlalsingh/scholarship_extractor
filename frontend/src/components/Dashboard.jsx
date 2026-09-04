import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import ScholarshipTable from './ScholarshipTable';
import { CardSkeleton } from './Skeleton';
import { ShieldCheck, Layers, FileText, CheckCircle2, History, AlertTriangle, AlertCircle } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const [scholarships, setScholarships] = useState([]);
  const [recentChanges, setRecentChanges] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    inactive: 0,
    changed: 0,
    verified: 0,
    likelyValid: 0,
  });

  const fetchData = async () => {
    try {
      setIsLoading(true);

      // Fetch all scholarships with monitoring, validations, and changes
      const { data: schData, error: schError } = await supabase
        .from('scholarships')
        .select(`
          *,
          scholarship_monitoring(*),
          scholarship_validations(*),
          scholarship_changes(*)
        `);

      if (schError) throw schError;

      // Fetch recent 5 global changes
      const { data: changesData, error: changesError } = await supabase
        .from('scholarship_changes')
        .select('*, scholarships(title)')
        .order('detected_at', { ascending: false })
        .limit(5);

      if (changesError) throw changesError;

      // Fetch latest completed recheck run
      const { data: runsData, error: runsError } = await supabase
        .from('recheck_runs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1);

      if (runsError) throw runsError;

      // Fetch recent changes count (last 24 hours)
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      const { count: recentChangesCount, error: countError } = await supabase
        .from('scholarship_changes')
        .select('*', { count: 'exact', head: true })
        .gte('detected_at', yesterday);

      if (countError) throw countError;

      // Process Stats
      const schs = schData || [];
      const total = schs.length;
      const active = schs.filter((s) => s.is_active).length;
      const inactive = total - active;

      const verified = schs.filter((s) =>
        s.scholarship_validations?.[0]?.status === 'VERIFIED' ||
        s.scholarship_validations?.[0]?.status === 'HIGH_CONFIDENCE'
      ).length;

      const likelyValid = schs.filter((s) =>
        s.scholarship_validations?.[0]?.status === 'LIKELY_VALID'
      ).length;

      setScholarships(schs);
      setRecentChanges(changesData || []);
      setLatestRun(runsData?.[0] || null);
      setStats({
        total,
        active,
        inactive,
        changed: recentChangesCount || 0,
        verified,
        likelyValid,
      });

    } catch (e) {
      console.error('Error fetching dashboard statistics:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Setup auto-refresh every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const getMonitoringHealth = () => {
    if (latestRun?.status === 'RUNNING') {
      return { label: 'Running', colorClass: 'text-blue-700 bg-blue-50 border-blue-200', dotClass: 'bg-blue-500 animate-pulse' };
    }

    const hasAttentionNeeded = scholarships.some((s) => {
      const mon = Array.isArray(s.scholarship_monitoring) ? s.scholarship_monitoring[0] : s.scholarship_monitoring;
      const failures = mon?.consecutive_failures || 0;
      return failures >= 3;
    });

    if (hasAttentionNeeded) {
      return { label: 'Failed', subText: 'Requires Attention', colorClass: 'text-rose-700 bg-rose-50 border-rose-200', dotClass: 'bg-rose-500' };
    }

    const hasSomeFailures = scholarships.some((s) => {
      const mon = Array.isArray(s.scholarship_monitoring) ? s.scholarship_monitoring[0] : s.scholarship_monitoring;
      const failures = mon?.consecutive_failures || 0;
      return failures > 0;
    });

    if (hasSomeFailures || latestRun?.status === 'FAILED') {
      return { label: 'Warning', subText: 'Checks failing', colorClass: 'text-amber-700 bg-amber-50 border-amber-200', dotClass: 'bg-amber-500' };
    }

    // No recheck_runs yet — if scholarships are loaded the system is healthy.
    // recheck_runs only exists after POST /recheck/run fires; initial discovery
    // doesn't write there, so we should not penalise the card for that.
    if (!latestRun) {
      if (scholarships.length > 0) {
        return {
          label: 'Healthy',
          subText: 'Pipeline operational',
          colorClass: 'text-emerald-700 bg-emerald-50 border-emerald-200',
          dotClass: 'bg-emerald-500',
        };
      }
      return {
        label: 'Never Run',
        subText: 'No data yet',
        colorClass: 'text-slate-500 bg-slate-50 border-slate-200',
        dotClass: 'bg-slate-400',
      };
    }

    return { label: 'Healthy', colorClass: 'text-emerald-700 bg-emerald-50 border-emerald-200', dotClass: 'bg-emerald-500' };
  };


  const health = getMonitoringHealth();

  return (
    <div className="p-8 space-y-8 select-none">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-5">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, idx) => <CardSkeleton key={idx} />)
        ) : (
          <>
            {/* Total Scholarships */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Total</span>
                <Layers size={16} />
              </div>
              <h3 className="text-3xl font-extrabold text-slate-900 mt-3">{stats.total}</h3>
              <p className="text-xs text-slate-500 mt-2 font-medium">Scholarships stored</p>
            </div>

            {/* Active */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-emerald-500">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Active</span>
                <CheckCircle2 size={16} />
              </div>
              <h3 className="text-3xl font-extrabold text-emerald-600 mt-3">{stats.active}</h3>
              <p className="text-xs text-slate-500 mt-2 font-medium">Currently live online</p>
            </div>

            {/* Inactive */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Inactive</span>
                <AlertCircle size={16} />
              </div>
              <h3 className="text-3xl font-extrabold text-slate-500 mt-3">{stats.inactive}</h3>
              <p className="text-xs text-slate-500 mt-2 font-medium">Archived or closed</p>
            </div>

            {/* Recently Changed */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-purple-500">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Changes</span>
                <History size={16} />
              </div>
              <h3 className="text-3xl font-extrabold text-purple-600 mt-3">{stats.changed}</h3>
              <p className="text-xs text-slate-500 mt-2 font-medium">Detected in last 24h</p>
            </div>

            {/* Verification */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-teal-500">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Verification</span>
                <ShieldCheck size={16} />
              </div>
              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="text-2xl font-extrabold text-teal-600">{stats.verified}</span>
                <span className="text-xs text-slate-400 font-bold uppercase">VER</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-3 font-semibold uppercase tracking-wider">
                {stats.likelyValid} Likely Valid
              </p>
            </div>

            {/* Monitoring Health */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex justify-between items-start text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Health</span>
                <AlertTriangle size={16} className={health.label === 'Healthy' ? 'text-emerald-500' : 'text-amber-500'} />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${health.dotClass}`}></span>
                <span className="text-xl font-extrabold text-slate-800">{health.label}</span>
              </div>
              <p className="text-xs text-slate-550 mt-2 font-medium truncate">
                {health.subText || (latestRun?.completed_at ? `Last run: ${new Date(latestRun.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'API Connected')}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Recent Changes Timeline */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h3 className="text-md font-bold text-slate-900 uppercase tracking-wider mb-5 flex items-center gap-2">
          <History size={16} className="text-slate-455" />
          Recent Changes Detected
        </h3>
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-10 bg-slate-100 rounded w-full animate-pulse"></div>
            <div className="h-10 bg-slate-100 rounded w-full animate-pulse"></div>
          </div>
        ) : recentChanges.length === 0 ? (
          <div className="py-6 text-center text-slate-500 text-sm font-medium border border-dashed border-slate-200 rounded-lg">
            ✓ No changes detected. All monitored scholarships are currently unchanged.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-450 font-bold uppercase tracking-wider select-none">
                  <th className="pb-3 pr-4">Scholarship</th>
                  <th className="pb-3 pr-4">Field</th>
                  <th className="pb-3 pr-4">Previous Value</th>
                  <th className="pb-3 pr-4">Current Value</th>
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 text-right">Detected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentChanges.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3.5 pr-4 font-semibold text-slate-800">
                      <button
                        onClick={() => navigate(`/scholarships/${c.scholarship_id}?tab=changes`)}
                        className="hover:text-indigo-600 text-left"
                      >
                        {c.scholarships?.title || 'Unknown Scholarship'}
                      </button>
                    </td>
                    <td className="py-3.5 pr-4 text-xs font-mono text-slate-500">
                      {c.field_name}
                    </td>
                    <td className="py-3.5 pr-4 text-slate-655 truncate max-w-[200px]" title={c.old_value}>
                      {c.old_value === 'true' && <span className="text-emerald-600 font-semibold">Active</span>}
                      {c.old_value === 'false' && <span className="text-rose-600 font-semibold">Inactive</span>}
                      {c.old_value !== 'true' && c.old_value !== 'false' && (c.old_value || '—')}
                    </td>
                    <td className="py-3.5 pr-4 text-slate-850 truncate max-w-[200px] font-semibold" title={c.new_value}>
                      {c.new_value === 'true' && <span className="text-emerald-600 font-bold">Active</span>}
                      {c.new_value === 'false' && <span className="text-rose-600 font-bold">Inactive</span>}
                      {c.new_value !== 'true' && c.new_value !== 'false' && (c.new_value || '—')}
                    </td>
                    <td className="py-3.5 pr-4">
                      <span className={`inline-flex px-2 py-0.5 text-[10px] font-bold rounded-full border ${c.change_type === 'MARKED_INACTIVE' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                        c.change_type === 'REACTIVATED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          'bg-purple-50 text-purple-700 border-purple-200'
                        }`}>
                        {c.change_type?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3.5 text-right text-xs text-slate-500 font-medium">
                      {new Date(c.detected_at).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Scholarship Overview Table */}
      <div className="space-y-4">
        <h3 className="text-md font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <FileText size={16} className="text-slate-455" />
          Scholarship Overview
        </h3>
        <ScholarshipTable scholarships={scholarships} isLoading={isLoading} />
      </div>
    </div>
  );
}
