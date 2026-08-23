import React, { useEffect, useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { supabase } from './supabaseClient';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import Scholarships from './components/Scholarships';
import Monitoring from './components/Monitoring';
import Changes from './components/Changes';
import Pipeline from './components/Pipeline';
import ScholarshipDetails from './components/ScholarshipDetails';
import Terminal from './components/Terminal';


export default function App() {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchLastRecheckRun = async () => {
    try {
      const { data, error } = await supabase
        .from('recheck_runs')
        .select('completed_at')
        .eq('status', 'COMPLETED')
        .order('completed_at', { ascending: false })
        .limit(1);
      
      if (error) throw error;

      if (data && data.length > 0) {
        setLastUpdated(data[0].completed_at);
      }
    } catch (e) {
      console.error('Error fetching last recheck run completed time:', e);
    }
  };

  useEffect(() => {
    fetchLastRecheckRun();
  }, []);

  const handleRefresh = async () => {
    setIsUpdating(true);
    await fetchLastRecheckRun();
    // Briefly show the spinner for a premium interactive feel
    setTimeout(() => {
      setIsUpdating(false);
      window.location.reload();
    }, 600);
  };

  return (
    <Router>
      <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Global Header */}
          <Header
            lastUpdated={lastUpdated}
            isUpdating={isUpdating}
            onRefresh={handleRefresh}
          />

          {/* Dynamic Scrollable Page Content */}
          <main className="flex-1 overflow-y-auto bg-slate-50/50">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scholarships" element={<Scholarships />} />
              <Route path="/scholarships/:id" element={<ScholarshipDetails />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/changes" element={<Changes />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/terminal" element={<Terminal />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}
