import React, { useEffect, useState, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import { Trophy, CheckCircle, TrendingDown, ArrowRight, Zap } from 'lucide-react';

export default function LeaderboardPage({ apiBase = 'http://localhost:8000', onSelectStrategy }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const chartRef = useRef(null);

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/compare`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, [apiBase]);

  useEffect(() => {
    if (!data || !chartRef.current) return;

    const names = Object.keys(data);
    const distances = names.map(n => data[n].metrics.total_picking_distance_m);
    const colors = names.map(n => n.includes('Baseline') ? '#EF4444' : n.includes('Forecast') ? '#10B981' : '#3B82F6');

    const trace = {
      x: names,
      y: distances,
      type: 'bar',
      marker: { color: colors, opacity: 0.9, line: { color: '#1E293B', width: 1 } },
      text: distances.map(d => `${d.toLocaleString()} m`),
      textposition: 'auto',
      hoverinfo: 'x+y'
    };

    const layout = {
      title: { text: 'Total Weekly Picking Distance by Strategy (Meters)', font: { color: '#E2E8F0', size: 14 } },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#94A3B8', family: 'inherit' },
      margin: { t: 40, b: 40, l: 60, r: 20 },
      yaxis: { gridcolor: '#1E293B', zerolinecolor: '#334155', title: 'Meters Walked' },
      xaxis: { gridcolor: '#1E293B' }
    };

    Plotly.newPlot(chartRef.current, [trace], layout, { responsive: true, displayModeBar: false });
  }, [data]);

  const baselineDist = data?.['Baseline']?.metrics?.total_picking_distance_m || 172603;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Trophy className="w-6 h-6 text-amber-400" />
            Optimization Strategy Leaderboard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Empirical benchmark comparing mathematical heuristics, Hungarian bipartite matching, and Forecast+Affinity AI.
          </p>
        </div>
        <button
          onClick={fetchLeaderboard}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition flex items-center gap-2"
        >
          <Zap className="w-4 h-4" /> Re-benchmark All
        </button>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div ref={chartRef} className="w-full h-72"></div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-5 py-3 border-b border-slate-800 flex justify-between items-center bg-slate-950/40">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Multi-Metric Comparative Table</span>
          <span className="text-xs text-emerald-400 font-mono">Feasibility reported per strategy</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800">
              <tr>
                <th className="p-3">Strategy</th>
                <th className="p-3">Pick Distance</th>
                <th className="p-3">Reduction</th>
                <th className="p-3">Feasibility</th>
                <th className="p-3">Space Util</th>
                <th className="p-3">Weekly Labor (₹)</th>
                <th className="p-3">Co-order Pair Distance</th>
                <th className="p-3">Moves</th>
                <th className="p-3">Top20 in Prime</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data && Object.entries(data).map(([name, item]) => {
                const m = item.metrics;
                const reduction = Math.max(0, ((baselineDist - m.total_picking_distance_m) / baselineDist) * 100).toFixed(1);
                const isOptimal = name.includes('Optimal');
                return (
                  <tr key={name} className={`hover:bg-slate-800/40 transition ${isOptimal ? 'bg-emerald-950/10' : ''}`}>
                    <td className="p-3 font-semibold text-white flex items-center gap-1.5">
                      {isOptimal && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
                      {name}
                    </td>
                    <td className="p-3 text-slate-200">{m.total_picking_distance_m.toLocaleString()} m</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${reduction > 0 ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'text-slate-500'}`}>
                        {reduction > 0 ? `-${reduction}%` : '0%'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`font-semibold ${m.feasibility_pct === 100 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {m.feasibility_pct}%
                      </span>
                    </td>
                    <td className="p-3 text-slate-300">{m.space_utilization_pct}%</td>
                    <td className="p-3 text-slate-200">₹{m.handling_cost_inr.toLocaleString()}</td>
                    <td className="p-3 text-slate-200">{m.average_affinity_distance_m.toLocaleString()} m</td>
                    <td className="p-3 text-slate-400">{m.moves_needed}</td>
                    <td className="p-3 text-amber-400 font-semibold">{m.high_demand_in_prime_slot_pct}%</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => onSelectStrategy && onSelectStrategy(name)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] transition inline-flex items-center gap-1"
                      >
                        Apply <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
