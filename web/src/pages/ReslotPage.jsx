import React, { useState, useEffect } from 'react';
import { ArrowLeftRight, Download, DollarSign, Calendar, TrendingDown, CheckCircle2 } from 'lucide-react';

export default function ReslotPage({ apiBase = 'http://localhost:8000' }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPlan() {
      setLoading(true);
      try {
        const res = await fetch(`${apiBase}/optimize?strategy=forecast_affinity`, { method: 'POST' });
        const json = await res.json();
        setPlan(json.reslotting_summary);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchPlan();
  }, [apiBase]);

  const handleDownloadCSV = () => {
    if (!plan || !plan.moves_list) return;
    const headers = ['product_id', 'category', 'from_location', 'to_location', 'weekly_picks', 'daily_savings_m', 'daily_savings_inr'];
    const rows = plan.moves_list.map(m => [
      m.product_id, m.category, m.from_location, m.to_location, m.weekly_picks, m.daily_savings_m, m.daily_savings_inr
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'slotiq_reslotting_recommendations.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <ArrowLeftRight className="w-6 h-6 text-emerald-400" />
            Warehouse Re-slotting Transition & Financial Payback Plan
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Prioritized physical moves ranked by highest daily ROI. Quantifies technician labor moving cost vs pick labor saved.
          </p>
        </div>
        <button
          onClick={handleDownloadCSV}
          disabled={!plan}
          className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold font-mono transition flex items-center gap-2 shadow-lg shadow-emerald-950/40"
        >
          <Download className="w-4 h-4" /> Download Recommendations CSV
        </button>
      </div>

      {plan && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
            <span className="text-xs text-slate-400 uppercase font-mono">Moves Needed</span>
            <div className="text-2xl font-bold text-white font-mono mt-1">{plan.total_moves} SKUs</div>
            <span className="text-[11px] text-slate-500 mt-0.5 block">Total physical relabelings</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
            <span className="text-xs text-slate-400 uppercase font-mono">Relocation Labor Cost</span>
            <div className="text-2xl font-bold text-slate-200 font-mono mt-1">₹{plan.total_relocation_cost_inr.toLocaleString()}</div>
            <span className="text-[11px] text-slate-500 mt-0.5 block">@ ₹12.00 / technician move</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
            <span className="text-xs text-slate-400 uppercase font-mono">Daily Labor Savings</span>
            <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">₹{plan.daily_financial_savings_inr.toLocaleString()}</div>
            <span className="text-[11px] text-emerald-500/80 mt-0.5 block">{plan.daily_distance_saved_m.toLocaleString()} m/day reduced</span>
          </div>

          <div className="bg-emerald-950/30 border border-emerald-800/60 rounded-xl p-4 shadow-lg">
            <span className="text-xs text-emerald-400 uppercase font-mono font-bold flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Payback Period
            </span>
            <div className="text-2xl font-bold text-emerald-300 font-mono mt-1">{plan.payback_period_days} Days</div>
            <span className="text-[11px] text-emerald-400 mt-0.5 block">Full capital break-even ROI</span>
          </div>
        </div>
      )}

      {/* Prioritized Move List Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-5 py-3 border-b border-slate-800 flex justify-between items-center bg-slate-950/40">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Prioritized Move Execution Sequence (Highest Impact First)
          </span>
          <span className="text-xs text-slate-400 font-mono">
            Showing top {plan?.moves_list?.length || 0} moves
          </span>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800 sticky top-0">
              <tr>
                <th className="p-3">SKU</th>
                <th className="p-3">Category</th>
                <th className="p-3">From Slot</th>
                <th className="p-3">To Slot</th>
                <th className="p-3">Weekly Picks</th>
                <th className="p-3">Distance Delta</th>
                <th className="p-3">Daily Travel Saved</th>
                <th className="p-3 text-right">Daily Labor Value Saved (₹/day)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {plan?.moves_list?.map((m, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="p-3 font-bold text-white">{m.product_id}</td>
                  <td className="p-3 text-slate-300">{m.category}</td>
                  <td className="p-3 text-red-400 font-bold">{m.from_location}</td>
                  <td className="p-3 text-emerald-400 font-bold">{m.to_location}</td>
                  <td className="p-3 text-slate-300">{m.weekly_picks}</td>
                  <td className="p-3 text-blue-400">{m.distance_delta_m > 0 ? `+${m.distance_delta_m} m` : `${m.distance_delta_m} m`}</td>
                  <td className="p-3 text-slate-200">{m.daily_savings_m} m/day</td>
                  <td className="p-3 text-right font-bold text-emerald-400">₹{m.daily_savings_inr.toFixed(2)}/day</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
