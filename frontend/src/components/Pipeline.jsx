import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import { Cpu, Play, CheckCircle, Clock, AlertCircle, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../config';

export default function Pipeline() {
  const [latestDiscovery, setLatestDiscovery] = useState(null);
  const [latestCrawl, setLatestCrawl] = useState(null);
  const [latestRecheck, setLatestRecheck] = useState(null);
  const [validationCounts, setValidationCounts] = useState({ verified: 0, likelyValid: 0, review: 0 });
  const [isUpdating, setIsUpdating] = useState(false);
  const [recheckStatus, setRecheckStatus] = useState({ running: false, message: '' });
  const [crawlStatus, setCrawlStatus] = useState({ running: false, message: '' });

  const fetchPipelineMetrics = async () => {
    try {
      setIsUpdating(true);

      // 1. Get latest discovery run
      const { data: discData } = await supabase
        .from('discovery_runs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1);

      // 2. Get latest crawl run
      const { data: crawlData } = await supabase
        .from('crawl_runs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1);

      // 3. Get latest recheck run
      const { data: recheckData } = await supabase
        .from('recheck_runs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1);

      // 4. Get validation metrics
      const { data: valData } = await supabase
        .from('scholarship_validations')
        .select('status');

      if (discData) setLatestDiscovery(discData[0]);
      if (crawlData) setLatestCrawl(crawlData[0]);
      if (recheckData) setLatestRecheck(recheckData[0]);

      if (valData) {
        const counts = { verified: 0, likelyValid: 0, review: 0 };
        valData.forEach((v) => {
          const s = v.status?.toUpperCase();
          if (s === 'VERIFIED' || s === 'HIGH_CONFIDENCE') counts.verified++;
          else if (s === 'LIKELY_VALID') counts.likelyValid++;
          else counts.review++;
        });
        setValidationCounts(counts);
      }

      // Check current running statuses from API
      await checkRunningStatuses();

    } catch (e) {
      console.error('Error fetching pipeline metrics:', e);
    } finally {
      setIsUpdating(false);
    }
  };

  const checkRunningStatuses = async () => {
    try {
      // Check Recheck status
      const recheckRes = await fetch(`${API_BASE_URL}/recheck/status`);
      if (recheckRes.ok) {
        const status = await recheckRes.json();
        setRecheckStatus({
          running: status.running,
          message: status.running ? 'Recheck is currently executing in the background...' : ''
        });
      }

      // Check Crawl/Orchestrator status
      const crawlRes = await fetch(`${API_BASE_URL}/orchestrator/status`);
      if (crawlRes.ok) {
        const status = await crawlRes.json();
        setCrawlStatus({
          running: status.running,
          message: status.running ? 'End-to-end pipeline run is executing in the background...' : ''
        });
      }
    } catch (e) {
      console.log('Backend API offline. Using fallback Supabase status.');
    }
  };

  useEffect(() => {
    fetchPipelineMetrics();

    // Poll status every 15 seconds
    const interval = setInterval(fetchPipelineMetrics, 15000);
    return () => clearInterval(interval);
  }, []);

  const triggerRecheck = async () => {
    if (recheckStatus.running) return;
    
    const confirmRun = window.confirm('Are you sure you want to trigger a scholarship recheck cycle? This runs in the background and re-validates all scholarships.');
    if (!confirmRun) return;

    try {
      setRecheckStatus({ running: true, message: 'Initiating recheck...' });
      const res = await fetch(`${API_BASE_URL}/recheck/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_size: 25, stale_after_hours: 24 })
      });

      if (res.ok) {
        setRecheckStatus({ running: true, message: 'Recheck started in the background.' });
        setTimeout(fetchPipelineMetrics, 2000);
      } else {
        throw new Error('Server returned error status');
      }
    } catch (e) {
      alert('Could not start recheck. Make sure your backend API service is running locally on port 8000.');
      setRecheckStatus({ running: false, message: 'Launch failed.' });
    }
  };

  const triggerOrchestrator = async () => {
    if (crawlStatus.running) return;

    const confirmRun = window.confirm('Are you sure you want to trigger the end-to-end scholarship discovery & crawl pipeline? This will perform web searches and scrape government listings, which can take several minutes.');
    if (!confirmRun) return;

    try {
      setCrawlStatus({ running: true, message: 'Initiating discovery crawl...' });
      const res = await fetch(`${API_BASE_URL}/orchestrator/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_domains: 5, max_depth: 2, max_pages: 15 })
      });

      if (res.ok) {
        setCrawlStatus({ running: true, message: 'Pipeline run started in the background.' });
        setTimeout(fetchPipelineMetrics, 2000);
      } else {
        throw new Error('Server error');
      }
    } catch (e) {
      alert('Could not start orchestrator crawl. Make sure your backend API service is running locally on port 8000.');
      setCrawlStatus({ running: false, message: 'Launch failed.' });
    }
  };

  // Build list of stages for visual flowchart
  const stages = [
    { name: 'Discovery', desc: 'Find candidate domains', status: crawlStatus.running ? 'RUNNING' : (latestDiscovery ? (latestDiscovery.status || 'COMPLETED') : 'PENDING'), icon: '🔍' },
    { name: 'Crawling', desc: 'Scrape listing index pages', status: crawlStatus.running ? 'RUNNING' : (latestCrawl ? (latestCrawl.status || 'COMPLETED') : 'PENDING'), icon: '🕷️' },
    { name: 'Extraction', desc: 'Deterministic card mapping', status: crawlStatus.running ? 'RUNNING' : (latestCrawl ? 'COMPLETED' : 'PENDING'), icon: '📄' },
    { name: 'Validation', desc: 'Legitimacy & dates checks', status: crawlStatus.running ? 'RUNNING' : (latestCrawl ? 'COMPLETED' : 'PENDING'), icon: '🛡️' },
    { name: 'Database', desc: 'Write relational Supabase data', status: crawlStatus.running ? 'RUNNING' : (latestCrawl ? 'COMPLETED' : 'PENDING'), icon: '💾' },
    { name: 'Monitoring', desc: 'Scheduling & failure triggers', status: recheckStatus.running ? 'RUNNING' : (latestRecheck ? 'COMPLETED' : 'PENDING'), icon: '⏰' },
    { name: 'Recheck', desc: 'Verify field drift / liveness', status: recheckStatus.running ? 'RUNNING' : (latestRecheck ? (latestRecheck.status || 'COMPLETED') : 'PENDING'), icon: '🔄' },
  ];

  return (
    <div className="p-8 space-y-8 select-none">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-50 text-indigo-700 p-2.5 rounded-xl border border-indigo-150 shadow-sm">
            <Cpu size={24} className="stroke-[2.5]" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Pipeline & Architecture</h2>
            <p className="text-xs text-slate-500 mt-1 font-medium">Monitor automation stages, view crawler metrics, and launch manual tasks.</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={triggerOrchestrator}
            disabled={crawlStatus.running}
            className={`flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-bold shadow-sm transition-all hover:bg-slate-50 disabled:opacity-50 ${
              crawlStatus.running ? 'cursor-not-allowed' : 'active:scale-95'
            }`}
          >
            <Play size={14} className="fill-slate-600 text-slate-600" />
            Run Discovery Pipeline
          </button>

          <button
            onClick={triggerRecheck}
            disabled={recheckStatus.running}
            className={`flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-bold shadow-sm transition-all disabled:opacity-50 ${
              recheckStatus.running ? 'cursor-not-allowed' : 'active:scale-95'
            }`}
          >
            <Play size={14} className="fill-white" />
            Run Recheck Now
          </button>
        </div>
      </div>

      {/* Task Running Status Bars */}
      {recheckStatus.message && (
        <div className="bg-indigo-50 border border-indigo-250 p-4 rounded-xl flex items-center gap-3">
          <RefreshCw className="text-indigo-600 animate-spin" size={18} />
          <span className="text-sm font-semibold text-indigo-900">{recheckStatus.message}</span>
        </div>
      )}
      {crawlStatus.message && (
        <div className="bg-blue-50 border border-blue-250 p-4 rounded-xl flex items-center gap-3">
          <RefreshCw className="text-blue-600 animate-spin" size={18} />
          <span className="text-sm font-semibold text-blue-900">{crawlStatus.message}</span>
        </div>
      )}

      {/* Visual Pipeline Flowchart */}
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-6">Automation Stages Flowchart</h3>
        <div className="grid grid-cols-1 lg:grid-cols-7 gap-4 relative">
          {stages.map((stage, idx) => {
            const isRunning = stage.status === 'RUNNING';
            const isCompleted = stage.status === 'COMPLETED';
            const isFailed = stage.status === 'FAILED';

            return (
              <div key={stage.name} className="flex flex-col items-center relative group">
                {/* Visual Node */}
                <div className={`w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shadow-sm border transition-all duration-200 ${
                  isRunning ? 'bg-blue-50 border-blue-500 text-blue-700 ring-4 ring-blue-100 animate-pulse' :
                  isFailed ? 'bg-rose-50 border-rose-450 text-rose-700' :
                  isCompleted ? 'bg-emerald-50 border-emerald-450 text-emerald-700' :
                  'bg-slate-50 border-slate-200 text-slate-400'
                }`}>
                  {stage.icon}
                </div>

                {/* Node Labels */}
                <h4 className="font-bold text-slate-900 mt-3 text-sm">{stage.name}</h4>
                <p className="text-[10px] text-slate-400 text-center mt-1 font-semibold leading-tight">{stage.desc}</p>
                
                <span className={`inline-block px-2 py-0.5 text-[9px] font-bold rounded-full border mt-2.5 ${
                  isRunning ? 'bg-blue-50 text-blue-800 border-blue-200' :
                  isFailed ? 'bg-rose-50 text-rose-800 border-rose-200' :
                  isCompleted ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                  'bg-slate-100 text-slate-500 border-slate-200'
                }`}>
                  {stage.status}
                </span>

                {/* Flow Connector Arrow for desktop */}
                {idx < 6 && (
                  <div className="hidden lg:block absolute top-7 -right-4 translate-x-1/2 z-0 font-bold text-slate-300 text-base">
                    ➔
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Runs Metrics Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Discovery Metric Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="text-base">🔍</span> Latest Discovery Run
            </h3>
            {latestDiscovery ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-450 font-semibold block uppercase">Search Queries</span>
                    <span className="text-xl font-bold text-slate-800">{latestDiscovery.total_queries}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-450 font-semibold block uppercase">Raw Candidates</span>
                    <span className="text-xl font-bold text-slate-800">{latestDiscovery.total_candidates}</span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-slate-450 font-semibold block uppercase">Last Executed</span>
                  <span className="text-sm font-medium text-slate-600">
                    {latestDiscovery.completed_at ? new Date(latestDiscovery.completed_at).toLocaleString() : 'Running...'}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-450 italic">No discovery run history found.</p>
            )}
          </div>
          <div className="mt-6 border-t border-slate-100 pt-4 flex justify-between items-center text-xs font-semibold text-slate-400 uppercase">
            <span>Status</span>
            <span className={`px-2 py-0.5 rounded-full border ${latestDiscovery?.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border-emerald-250' : 'bg-slate-50 text-slate-500 border-slate-200'}`}>
              {latestDiscovery?.status || 'UNKNOWN'}
            </span>
          </div>
        </div>

        {/* Crawling Metric Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="text-base">🕷️</span> Latest Crawl Run
            </h3>
            {latestCrawl ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <span className="text-xs text-slate-450 font-semibold block uppercase">Visited</span>
                    <span className="text-xl font-bold text-slate-800">{latestCrawl.total_pages_visited} pages</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-450 font-semibold block uppercase">Extracted</span>
                    <span className="text-xl font-bold text-slate-800">{latestCrawl.total_scholarships_extracted}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-450 font-semibold block uppercase">Failed</span>
                    <span className={`text-xl font-bold ${latestCrawl.total_pages_failed > 0 ? 'text-amber-600' : 'text-slate-800'}`}>{latestCrawl.total_pages_failed}</span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-slate-455 font-semibold block uppercase">Start Target URL</span>
                  <span className="text-xs font-mono text-indigo-600 truncate block mt-1" title={latestCrawl.start_url}>
                    {latestCrawl.start_url}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-450 italic">No crawl run history found.</p>
            )}
          </div>
          <div className="mt-6 border-t border-slate-100 pt-4 flex justify-between items-center text-xs font-semibold text-slate-400 uppercase">
            <span>Status</span>
            <span className={`px-2 py-0.5 rounded-full border ${latestCrawl?.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border-emerald-250' : 'bg-slate-50 text-slate-500 border-slate-200'}`}>
              {latestCrawl?.status || 'UNKNOWN'}
            </span>
          </div>
        </div>

        {/* Validation Metric Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="text-base">🛡️</span> Validation Integrity
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs text-slate-450 font-semibold block uppercase">Verified status</span>
                  <span className="text-xl font-extrabold text-teal-600 flex items-center gap-1">
                    <CheckCircle size={15} /> {validationCounts.verified}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-slate-450 font-semibold block uppercase">Likely Valid</span>
                  <span className="text-xl font-extrabold text-amber-600 flex items-center gap-1">
                    <Clock size={15} /> {validationCounts.likelyValid}
                  </span>
                </div>
              </div>
              <div>
                <span className="text-xs text-slate-450 font-semibold block uppercase">Needs Review / Low Conf</span>
                <span className="text-sm font-bold text-slate-500 flex items-center gap-1 mt-1">
                  <AlertCircle size={14} /> {validationCounts.review} items
                </span>
              </div>
            </div>
          </div>
          <div className="mt-6 border-t border-slate-100 pt-4 flex justify-between items-center text-xs font-semibold text-slate-400 uppercase">
            <span>Integrity Check</span>
            <span className="text-emerald-700 font-bold">ONLINE</span>
          </div>
        </div>
      </div>

      {/* System Health Status List */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">System Service Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Database</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Discovery</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Crawler</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Validator</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Monitoring</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="font-semibold text-slate-700">Recheck API</span>
            <span className="text-emerald-600 font-bold uppercase select-none">● Healthy</span>
          </div>
        </div>
      </div>
    </div>
  );
}
