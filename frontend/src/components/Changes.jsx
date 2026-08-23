import React, { useEffect, useState, useMemo } from 'react';
import { supabase } from '../supabaseClient';
import { TableSkeleton } from './Skeleton';
import { History, Search, Filter } from 'lucide-react';

export default function Changes() {
  const [changes, setChanges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [fieldFilter, setFieldFilter] = useState('ALL');

  const fetchChanges = async () => {
    try {
      setIsLoading(true);
      const { data, error } = await supabase
        .from('scholarship_changes')
        .select('*, scholarships(title)')
        .order('detected_at', { ascending: false });
      if (error) throw error;
      setChanges(data || []);
    } catch (e) {
      console.error('Error fetching changes:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChanges();
  }, []);

  // Compute unique field names for the field filter dropdown
  const uniqueFields = useMemo(() => {
    const fields = new Set();
    changes.forEach((c) => {
      if (c.field_name) fields.add(c.field_name);
    });
    return Array.from(fields);
  }, [changes]);

  // Filter changes
  const filteredChanges = useMemo(() => {
    let result = [...changes];

    // Search scholarship name
    if (searchTerm) {
      const lower = searchTerm.toLowerCase();
      result = result.filter((c) =>
        c.scholarships?.title?.toLowerCase().includes(lower)
      );
    }

    // Change Type filter
    if (typeFilter !== 'ALL') {
      result = result.filter((c) => c.change_type === typeFilter);
    }

    // Field Name filter
    if (fieldFilter !== 'ALL') {
      result = result.filter((c) => c.field_name === fieldFilter);
    }

    return result;
  }, [changes, searchTerm, typeFilter, fieldFilter]);

  return (
    <div className="p-8 space-y-6 select-none">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-50 text-indigo-700 p-2.5 rounded-xl border border-indigo-150 shadow-sm">
          <History size={24} className="stroke-[2.5]" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Global Changes Log</h2>
          <p className="text-xs text-slate-500 mt-1 font-medium">Verify the history and audit trail of updates detected across all scholarships.</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[260px]">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by scholarship title..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-250 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-sans"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Change Type Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
            <span className="text-xs text-slate-450 font-semibold uppercase tracking-wider">Change Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="text-xs font-semibold text-slate-700 bg-transparent border-none outline-none cursor-pointer"
            >
              <option value="ALL">All Types</option>
              <option value="FIELD_UPDATED">Field Updated</option>
              <option value="MARKED_INACTIVE">Marked Inactive</option>
              <option value="REACTIVATED">Reactivated</option>
            </select>
          </div>

          {/* Field Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
            <span className="text-xs text-slate-455 font-semibold uppercase tracking-wider">Field Name:</span>
            <select
              value={fieldFilter}
              onChange={(e) => setFieldFilter(e.target.value)}
              className="text-xs font-semibold text-slate-700 bg-transparent border-none outline-none cursor-pointer"
            >
              <option value="ALL">All Fields</option>
              {uniqueFields.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={7} cols={6} />
      ) : filteredChanges.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm">
          <History size={32} className="text-slate-300 mx-auto mb-3" />
          <h3 className="font-semibold text-slate-800 text-base">No change logs found</h3>
          <p className="text-slate-500 text-xs mt-1">Try relaxing filters or search query.</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-xs text-slate-500 font-bold uppercase tracking-wider select-none">
                  <th className="px-6 py-4">Scholarship</th>
                  <th className="px-6 py-4">Field</th>
                  <th className="px-6 py-4">Previous Value</th>
                  <th className="px-6 py-4">Current Value</th>
                  <th className="px-6 py-4">Change Type</th>
                  <th className="px-6 py-4 text-right">Detected At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-150 text-sm">
                {filteredChanges.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900 max-w-[280px] truncate" title={c.scholarships?.title}>
                      {c.scholarships?.title || 'Unknown Scholarship'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                        {c.field_name}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 max-w-[200px] truncate" title={c.old_value}>
                      {c.old_value === 'true' && <span className="text-emerald-600 font-semibold">Active</span>}
                      {c.old_value === 'false' && <span className="text-rose-650 font-semibold">Inactive</span>}
                      {c.old_value !== 'true' && c.old_value !== 'false' && (c.old_value || '—')}
                    </td>
                    <td className="px-6 py-4 text-slate-800 font-medium max-w-[200px] truncate" title={c.new_value}>
                      {c.new_value === 'true' && <span className="text-emerald-650 font-bold">Active</span>}
                      {c.new_value === 'false' && <span className="text-rose-700 font-bold">Inactive</span>}
                      {c.new_value !== 'true' && c.new_value !== 'false' && (c.new_value || '—')}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                        c.change_type === 'MARKED_INACTIVE' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                        c.change_type === 'REACTIVATED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        'bg-purple-50 text-purple-750 border-purple-200'
                      }`}>
                        {c.change_type?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-xs text-slate-500 font-medium font-sans">
                      {new Date(c.detected_at).toLocaleString([], { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
