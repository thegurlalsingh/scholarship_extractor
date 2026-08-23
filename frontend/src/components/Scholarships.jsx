import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import ScholarshipTable from './ScholarshipTable';
import { TableSkeleton } from './Skeleton';
import { GraduationCap } from 'lucide-react';

export default function Scholarships() {
  const [scholarships, setScholarships] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchScholarships = async () => {
    try {
      setIsLoading(true);
      const { data, error } = await supabase
        .from('scholarships')
        .select(`
          *,
          scholarship_monitoring(*),
          scholarship_validations(*),
          scholarship_changes(*)
        `);
      if (error) throw error;
      setScholarships(data || []);
    } catch (e) {
      console.error('Error fetching scholarships:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScholarships();
  }, []);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-50 text-indigo-700 p-2.5 rounded-xl border border-indigo-150 shadow-sm">
          <GraduationCap size={24} className="stroke-[2.5]" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Scholarship Database</h2>
          <p className="text-xs text-slate-500 mt-1 font-medium">Browse, search, and audit all discovered scholarship opportunities.</p>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={8} cols={7} />
      ) : (
        <ScholarshipTable scholarships={scholarships} isLoading={false} />
      )}
    </div>
  );
}
