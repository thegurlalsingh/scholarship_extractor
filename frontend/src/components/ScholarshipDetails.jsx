import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { getDeadlineUrgency, getValidationBadge } from './ScholarshipTable';
import { DetailSkeleton } from './Skeleton';
import { ArrowLeft, ExternalLink, Calendar, Shield, Activity, History, Info, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';

export default function ScholarshipDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [scholarship, setScholarship] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchDetails = async () => {
    try {
      setIsLoading(true);
      const { data, error } = await supabase
        .from('scholarships')
        .select(`
          *,
          scholarship_monitoring(*),
          scholarship_validations(*),
          scholarship_changes(*)
        `)
        .eq('id', id)
        .single();

      if (error) throw error;
      setScholarship(data);

      // Read tab preference from query params or URL hash
      const searchParams = new URLSearchParams(location.search);
      if (searchParams.get('tab') === 'changes' || location.hash === '#changes') {
        setActiveTab('changes');
      }

    } catch (e) {
      console.error('Error fetching scholarship details:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id, location]);

  if (isLoading) {
    return (
      <div className="p-8">
        <DetailSkeleton />
      </div>
    );
  }

  if (!scholarship) {
    return (
      <div className="p-8 text-center select-none space-y-4">
        <AlertCircle size={40} className="text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Scholarship not found</h2>
        <button
          onClick={() => navigate('/scholarships')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-650 hover:text-indigo-900 border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 shadow-sm"
        >
          <ArrowLeft size={16} /> Back to Database
        </button>
      </div>
    );
  }

  const monitoring = scholarship.scholarship_monitoring?.[0] || {};
  const validation = scholarship.scholarship_validations?.[0] || {};
  const changes = scholarship.scholarship_changes || [];
  const urgency = getDeadlineUrgency(scholarship.application_end);
  const valInfo = getValidationBadge(validation.status);
  const ValIcon = valInfo.icon;

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'Never checked';
    return new Date(isoString).toLocaleString('en-US', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="p-8 space-y-6 select-none max-w-6xl mx-auto">
      {/* Back navigation */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-slate-800 uppercase tracking-wider transition-colors"
      >
        <ArrowLeft size={14} className="stroke-[2.5]" />
        Back to listings
      </button>      {/* Profile Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2.5">
          <h2 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight leading-snug">
            {scholarship.title}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${scholarship.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`}></span>
            <span className={`text-xs font-bold uppercase mr-3 ${scholarship.is_active ? 'text-emerald-700' : 'text-slate-550'}`}>
              {scholarship.is_active ? 'Active' : 'Inactive'}
            </span>

            {/* Computed Status Badge */}
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${
              scholarship.computed_status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
              scholarship.computed_status === 'EXPIRING_SOON' ? 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse' :
              scholarship.computed_status === 'EXPIRED' ? 'bg-rose-50 text-rose-700 border-rose-200' :
              'bg-slate-50 text-slate-700 border-slate-250'
            }`}>
              {scholarship.computed_status?.replace('_', ' ') || 'ACTIVE'}
            </span>

            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${valInfo.badgeClass}`}>
              <ValIcon size={12} className="stroke-[2.5]" />
              <span>{valInfo.label}</span>
            </span>

            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${urgency.badgeClass}`}>
              <span>{urgency.icon}</span>
              <span>{urgency.label}</span>
            </span>
          </div>
        </div>

        <div className="text-left md:text-right text-xs text-slate-455 space-y-1 md:border-l md:border-slate-150 md:pl-6 shrink-0">
          <div>
            <span className="font-semibold uppercase tracking-wider block text-[10px]">Last Checked</span>
            <span className="font-medium text-slate-700 text-sm block mt-0.5">{formatDateTime(monitoring.last_checked_at)}</span>
          </div>
          <div className="pt-2">
            <span className="font-semibold uppercase tracking-wider block text-[10px]">Last Updated</span>
            <span className="font-medium text-slate-700 text-sm block mt-0.5">{formatDateTime(scholarship.updated_at)}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex gap-6 text-sm font-bold">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 transition-all ${
            activeTab === 'overview'
              ? 'text-indigo-650 border-b-2 border-indigo-600'
              : 'text-slate-400 hover:text-slate-650'
          }`}
        >
          Overview & Eligibility
        </button>
        <button
          onClick={() => setActiveTab('verification')}
          className={`pb-3 transition-all flex items-center gap-1.5 ${
            activeTab === 'verification'
              ? 'text-indigo-650 border-b-2 border-indigo-600'
              : 'text-slate-400 hover:text-slate-650'
          }`}
        >
          <Shield size={14} /> Verification Details ({validation.legitimacy_score ?? 0}%)
        </button>
        <button
          onClick={() => setActiveTab('changes')}
          className={`pb-3 transition-all flex items-center gap-1.5 ${
            activeTab === 'changes'
              ? 'text-indigo-650 border-b-2 border-indigo-600'
              : 'text-slate-400 hover:text-slate-650'
          }`}
        >
          <History size={14} /> Change History ({changes.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm lg:col-span-2 space-y-6">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
              <Info size={16} className="text-slate-400" />
              Scholarship Details & Schema Fields
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Title</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.title}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Organization</span>
                <p className="text-sm font-medium text-slate-805">{scholarship.organization || 'Not specified'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Scheme Type</span>
                <p className="text-xs font-mono text-slate-700 bg-slate-50 px-2 py-0.5 rounded w-max">
                  {scholarship.scheme_type?.replace('_', ' ') || 'UNKNOWN'}
                </p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Scholarship Amount / Benefit</span>
                <p className="text-sm font-bold text-emerald-700">{scholarship.scholarship_amount || 'Not specified'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Education / Course Level</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.education_level || 'Not specified'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Family Income Limit</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.income_criteria || 'Not specified'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Gender Restriction</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.gender_criteria || 'Not restricted'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Category Criteria</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.category_criteria || 'All Categories'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Domicile Requirement</span>
                <p className="text-sm font-medium text-slate-800">{scholarship.domicile || 'Not restricted'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Verification Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-800">{validation.legitimacy_score ?? '—'} / 100</span>
                  {validation.confidence !== undefined && (
                    <span className="text-[10px] text-indigo-600 font-bold uppercase">({Math.round(validation.confidence * 100)}% Confidence)</span>
                  )}
                </div>
              </div>
            </div>

            {/* Application Dates */}
            <div className="border-t border-slate-100 pt-5 space-y-4">
              <h4 className="text-xs font-bold text-slate-450 uppercase tracking-wider flex items-center gap-2">
                <Calendar size={14} /> Application Timeline
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-600">Start Date</span>
                  <span className="font-bold text-slate-800">{formatDate(scholarship.application_start)}</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-600">Deadline</span>
                  <span className="font-bold text-slate-800">{formatDate(scholarship.application_end)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Action Sidebar */}
          <div className="space-y-6">
            {/* Official Source Links */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2.5">
                Official Links
              </h3>
              
              <div className="flex flex-col gap-2">
                <a
                  href={scholarship.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 border border-slate-200 hover:border-slate-350 rounded-lg text-xs font-bold text-indigo-650 hover:text-indigo-900 hover:bg-slate-50 transition-all shadow-sm"
                >
                  <span>Official Portal page</span>
                  <ExternalLink size={14} />
                </a>

                {scholarship.application_url && (
                  <a
                    href={scholarship.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 border border-indigo-200 bg-indigo-50/20 hover:bg-indigo-50/50 rounded-lg text-xs font-bold text-indigo-700 hover:text-indigo-900 transition-all shadow-sm"
                  >
                    <span>Direct Application Link</span>
                    <ExternalLink size={14} />
                  </a>
                )}

                {scholarship.guidelines_url && (
                  <a
                    href={scholarship.guidelines_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 border border-slate-200 hover:border-slate-350 rounded-lg text-xs font-bold text-slate-650 hover:text-slate-900 hover:bg-slate-50 transition-all shadow-sm"
                  >
                    <span>View Guidelines PDF</span>
                    <ExternalLink size={14} />
                  </a>
                )}

                {scholarship.faq_url && (
                  <a
                    href={scholarship.faq_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 border border-slate-200 hover:border-slate-350 rounded-lg text-xs font-bold text-slate-650 hover:text-slate-900 hover:bg-slate-50 transition-all shadow-sm"
                  >
                    <span>View FAQs Page</span>
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            </div>

            {/* Monitoring Stats */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2.5 flex items-center gap-2">
                <Activity size={15} className="text-slate-400" />
                Pipeline Monitoring
              </h3>

              <div className="space-y-4 text-xs font-medium">
                {monitoring.consecutive_failures > 0 && (
                  <div className={`p-3.5 rounded-lg flex items-start gap-2 border ${
                    monitoring.consecutive_failures >= 3 ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-amber-50 border-amber-200 text-amber-800'
                  }`}>
                    <AlertTriangle className="shrink-0 mt-0.5 animate-pulse" size={16} />
                    <div>
                      <span className="font-bold uppercase block text-[10px]">Crawl Warning active</span>
                      <span className="text-[11px] block mt-0.5">
                        {monitoring.consecutive_failures} consecutive connection failures detected.
                        {monitoring.consecutive_failures >= 3 && ' Rechecking has locked this scholarship as INACTIVE.'}
                      </span>
                    </div>
                  </div>
                )}

                <div className="flex justify-between items-center">
                  <span className="text-slate-455">Monitoring status</span>
                  <span className={`font-bold uppercase ${monitoring.is_active ? 'text-emerald-700' : 'text-slate-500'}`}>
                    {monitoring.is_active ? '● Active' : '● Inactive'}
                  </span>
                </div>

                <div className="flex justify-between items-center border-t border-slate-100 pt-3">
                  <span className="text-slate-455">Consecutive failures</span>
                  <span className={`font-bold font-mono ${monitoring.consecutive_failures > 0 ? 'text-rose-650' : 'text-emerald-650'}`}>
                    {monitoring.consecutive_failures}
                  </span>
                </div>

                <div className="flex justify-between items-center border-t border-slate-100 pt-3">
                  <span className="text-slate-455">Check frequency</span>
                  <span className="text-slate-800 font-semibold font-mono">Once per 24 hours</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : activeTab === 'verification' ? (
        /* Verification Tab Panel */
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-md font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Shield size={18} className="text-indigo-600" />
                Legitimacy Verification Engine
              </h3>
              <p className="text-xs text-slate-500 mt-1">Detailed breakdown of evidence signals calculated by the verification parser.</p>
            </div>
            <div className="flex items-center gap-4 bg-slate-50 px-4 py-2.5 border border-slate-200 rounded-xl">
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Confidence Score</span>
                <span className="text-lg font-extrabold text-slate-850 font-mono">
                  {validation.legitimacy_score ?? '—'} / 100
                </span>
              </div>
              <div className="border-l border-slate-200 h-8 pl-4">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Evaluation Result</span>
                <span className={`text-xs font-extrabold uppercase ${
                  validation.status === 'VERIFIED' ? 'text-emerald-700' :
                  validation.status === 'HIGH_CONFIDENCE' ? 'text-indigo-700' :
                  validation.status === 'LIKELY_VALID' ? 'text-amber-700' : 'text-rose-700'
                }`}>
                  {validation.status?.replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>

          {/* Verification Checks Grid */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold text-slate-450 uppercase tracking-wider">Scoring Breakdown & Checks</h4>
            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-450 uppercase tracking-wider">
                    <th className="py-3 px-4">Verification Check</th>
                    <th className="py-3 px-4">Result</th>
                    <th className="py-3 px-4 text-right">Points Earned</th>
                    <th className="py-3 px-4">Description / Findings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-150 text-xs font-medium">
                  {validation.verification_checks && validation.verification_checks.length > 0 ? (
                    validation.verification_checks.map((c, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/40">
                        <td className="py-3.5 px-4 font-bold text-slate-800 capitalize">
                          {c.check?.replace(/_/g, ' ')}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                            c.passed 
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                              : 'bg-rose-50 text-rose-700 border-rose-200'
                          }`}>
                            {c.passed ? '✓ PASSED' : '❌ FAILED'}
                          </span>
                        </td>
                        <td className={`py-3.5 px-4 text-right font-mono font-bold ${c.passed ? 'text-emerald-700' : 'text-slate-400'}`}>
                          {c.passed ? `+${c.score}` : '0'}
                        </td>
                        <td className="py-3.5 px-4 text-slate-550">
                          {c.message}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="py-6 text-center text-slate-500 italic">No structured checks found in validation record.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Source snap Traceability */}
          {validation.source_snapshot && (
            <div className="border-t border-slate-100 pt-6 space-y-4">
              <h4 className="text-xs font-bold text-slate-450 uppercase tracking-wider">Evidence Traceability</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs bg-slate-50 p-4 border border-slate-200 rounded-xl font-mono text-slate-650">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase block font-sans mb-1">Official Domain</span>
                  <span className="text-slate-800 break-all">{validation.source_snapshot.domain}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase block font-sans mb-1">Official Registry Status</span>
                  <span className={validation.source_snapshot.is_official_domain ? 'text-emerald-700 font-bold' : 'text-slate-700'}>
                    {validation.source_snapshot.is_official_domain ? 'Government Official Domain verified (+30 pts)' : 'Non-Gov Known Domain verified'}
                  </span>
                </div>
                <div className="md:col-span-2 border-t border-slate-200/60 mt-2 pt-2">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block font-sans mb-1">Trace Source URL</span>
                  <a href={validation.source_snapshot.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-900 break-all underline">
                    {validation.source_snapshot.url}
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Warnings Panel */}
          {validation.warnings && validation.warnings.length > 0 && (
            <div className="border-t border-slate-100 pt-6 space-y-3">
              <h4 className="text-xs font-bold text-slate-450 uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                <AlertTriangle size={15} /> System Validation Warnings
              </h4>
              <div className="bg-rose-50/30 border border-rose-150 rounded-xl p-4 space-y-2">
                {validation.warnings.map((w, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-rose-800">
                    <span className="mt-0.5">•</span>
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Changes tab panel */
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h3 className="text-md font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <History size={16} className="text-slate-450" />
              Relational Changes Audit history
            </h3>
            <p className="text-xs text-slate-400 mt-1">Timeline of field edits detected during daily cron-recheck cycles.</p>
          </div>

          {changes.length === 0 ? (
            <div className="py-8 text-center text-slate-500 text-sm font-medium border border-dashed border-slate-200 rounded-lg">
              ✓ No change history logged. This scholarship matches its original discovered values.
            </div>
          ) : (
            <div className="relative border-l-2 border-indigo-150 pl-6 space-y-6 my-4 ml-3">
              {changes.map((c) => {
                const isDeactivated = c.change_type === 'MARKED_INACTIVE';
                const isReactivated = c.change_type === 'REACTIVATED';

                return (
                  <div key={c.id} className="relative">
                    {/* Timeline Node icon */}
                    <div className={`absolute -left-[31px] top-1 w-4.5 h-4.5 rounded-full border-2 flex items-center justify-center bg-white ${
                      isDeactivated ? 'border-rose-500 text-rose-500' :
                      isReactivated ? 'border-emerald-500 text-emerald-500' :
                      'border-indigo-500 text-indigo-500'
                    }`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        isDeactivated ? 'bg-rose-500' :
                        isReactivated ? 'bg-emerald-500' :
                        'bg-indigo-500'
                      }`} />
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 max-w-2xl space-y-2">
                      <div className="flex items-center justify-between flex-wrap gap-2 text-xs font-semibold text-slate-500">
                        <span className="font-sans font-medium text-slate-655 uppercase tracking-wider">
                          {new Date(c.detected_at).toLocaleString([], { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span className={`px-2 py-0.5 text-[9px] font-bold rounded-full border ${
                          isDeactivated ? 'bg-rose-50 text-rose-800 border-rose-250' :
                          isReactivated ? 'bg-emerald-50 text-emerald-800 border-emerald-250' :
                          'bg-purple-50 text-purple-750 border-purple-250'
                        }`}>
                          {c.change_type?.replace('_', ' ')}
                        </span>
                      </div>

                      <div className="text-sm font-medium text-slate-800">
                        {isDeactivated && (
                          <p>Scholarship recheck exceeded max retry threshold: <span className="text-rose-700 font-bold">MARKED INACTIVE</span></p>
                        )}
                        {isReactivated && (
                          <p>Scholarship recheck resolved connectivity: <span className="text-emerald-700 font-bold">REACTIVATED ACTIVE</span></p>
                        )}
                        {!isDeactivated && !isReactivated && (
                          <p>
                            Field <span className="text-indigo-650 font-mono text-xs bg-slate-200/50 px-1.5 py-0.5 rounded">{c.field_name}</span> updated
                          </p>
                        )}
                      </div>

                      {!isDeactivated && !isReactivated && (
                        <div className="grid grid-cols-2 gap-4 border-t border-slate-200/60 pt-2.5 text-xs">
                          <div>
                            <span className="text-slate-400 font-semibold block uppercase text-[10px]">Previous</span>
                            <span className="text-slate-600 block mt-1 font-medium bg-slate-200/30 px-2 py-1 rounded truncate">{c.old_value || '—'}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 font-semibold block uppercase text-[10px]">Updated</span>
                            <span className="text-slate-900 block mt-1 font-bold bg-indigo-50/50 border border-indigo-100 px-2 py-1 rounded truncate">{c.new_value || '—'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
