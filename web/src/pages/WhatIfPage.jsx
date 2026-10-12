import React, { useState, useEffect } from 'react';
import { Sliders, RefreshCw, TrendingUp, DollarSign, Clock, RotateCcw } from 'lucide-react';

export default function WhatIfPage({ apiBase = 'http://localhost:8000' }) {
  const [multipliers, setMultipliers] = useState({
    Electronics: 1.0,
    Apparel: 1.0,
    Grocery: 1.0,
    Health: 1.0,
    Home: 1.0
  });

  const [simResults, setSimResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async (mults) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/whatif`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ multipliers: mults })
      });
      const json = await res.json();
      setSimResults(json);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation(multipliers);
  }, [apiBase]);

  const handleSliderChange = (cat, val) => {
    const updated = { ...multipliers, [cat]: parseFloat(val) };
    setMultipliers(updated);
    runSimulation(updated);
  };

  const applyPreset = (preset) => {
    setMultipliers(preset);
    runSimulation(preset);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Sliders className="w-6 h-6 text-purple-400" />
            Demand Sensitivity & What-If Scenario Simulator
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Simulate seasonal spikes, promotions, and category demand shocks. SlotIQ dynamically reslots the warehouse in real time.
          </p>
        </div>
        <button
          onClick={() => applyPreset({ Electronics: 1.0, Apparel: 1.0, Grocery: 1.0, Health: 1.0, Home: 1.0 })}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono transition flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Reset 1.0x
        </button>
      </div>

      {/* Preset Scenarios */}
      <div className="flex flex-wrap gap-2 text-xs font-mono">
        <span className="text-slate-500 py-1">Presets:</span>
        <button
          onClick={() => applyPreset({ Electronics: 2.2, Apparel: 1.1, Grocery: 0.9, Health: 1.0, Home: 1.4 })}
          className="px-3 py-1 bg-purple-950/60 border border-purple-800/60 text-purple-300 rounded-lg hover:bg-purple-900/60 transition"
        >
          Cyber Monday (+120% Tech)
        </button>
        <button
          onClick={() => applyPreset({ Electronics: 0.9, Apparel: 1.0, Grocery: 1.6, Health: 2.0, Home: 0.8 })}
          className="px-3 py-1 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 rounded-lg hover:bg-emerald-900/60 transition"
        >
          Winter Health Surge (+100% Health)
        </button>
        <button
          onClick={() => applyPreset({ Electronics: 1.5, Apparel: 1.5, Grocery: 1.5, Health: 1.5, Home: 1.5 })}
          className="px-3 py-1 bg-amber-950/60 border border-amber-800/60 text-amber-300 rounded-lg hover:bg-amber-900/60 transition"
        >
          Peak Holiday Rush (All +50%)
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sliders Box */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Category Demand Multipliers</h3>
          {Object.entries(multipliers).map(([cat, val]) => (
            <div key={cat} className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-300 font-semibold">{cat}</span>
                <span className="text-purple-400 font-bold">{val.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="3.0"
                step="0.1"
                value={val}
                onChange={(e) => handleSliderChange(cat, e.target.value)}
                className="w-full accent-purple-500 cursor-pointer"
              />
            </div>
          ))}
        </div>

        {/* Live Metrics Box */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Dynamic Re-optimized Impact</h3>
              {loading && <RefreshCw className="w-4 h-4 text-purple-400 animate-spin" />}
            </div>

            {simResults && (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-400">Total Picking Distance</div>
                  <div className="text-xl font-bold text-white font-mono mt-1">
                    {simResults.metrics.total_picking_distance_m.toLocaleString()} m
                  </div>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-400">Handling Labor Cost</div>
                  <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
                    ${simResults.metrics.handling_cost_usd.toLocaleString()}
                  </div>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-400">Daily Walking Saved</div>
                  <div className="text-xl font-bold text-blue-400 font-mono mt-1">
                    {simResults.reslot.daily_distance_saved_m.toLocaleString()} m/day
                  </div>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-xs text-slate-400">Payback Period</div>
                  <div className="text-xl font-bold text-amber-400 font-mono mt-1">
                    {simResults.reslot.payback_period_days} days
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-5 p-3.5 bg-purple-950/20 border border-purple-800/40 rounded-xl text-xs text-slate-300 font-mono">
            💡 Demand shifts alter item velocity rankings. Hungarian & Affinity algorithms instantly swap high-velocity items into prime positions to preserve operational throughput.
          </div>
        </div>
      </div>
    </div>
  );
}
