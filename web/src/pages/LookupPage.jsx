import React, { useState, useEffect } from 'react';
import { Search, Package, MapPin, ArrowRight, ShieldAlert, Sparkles, Check } from 'lucide-react';

export default function LookupPage({ apiBase = 'http://localhost:8000' }) {
  const [productId, setProductId] = useState('P001');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRecommendation = async (id) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/recommend/${id.toUpperCase()}`);
      if (!res.ok) throw new Error(`Product ${id} not found.`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendation(productId);
  }, [apiBase]);

  const handleSubmit = (e) => {
    e.preventDefault();
    fetchRecommendation(productId);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Search className="w-6 h-6 text-blue-400" />
          Product Slotting Auditor & Explainability Engine
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Inspect granular placement decisions. Every single SKU placement is backed by an auditable plain-English operational rationale.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            placeholder="Enter Product ID (e.g., P001, P042, P150)..."
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm font-mono uppercase focus:outline-none focus:border-blue-500"
          />
        </div>
        <button
          type="submit"
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition flex items-center gap-2"
        >
          Audit SKU
        </button>
      </form>

      {/* Quick Select Pill Buttons */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <span>Quick Samples:</span>
        {['P001', 'P002', 'P004', 'P015', 'P060', 'P150'].map((p) => (
          <button
            key={p}
            onClick={() => { setProductId(p); fetchRecommendation(p); }}
            className={`px-2 py-1 rounded transition border ${productId.toUpperCase() === p ? 'bg-blue-600/30 text-blue-300 border-blue-500' : 'bg-slate-900 border-slate-800 hover:border-slate-700'}`}
          >
            {p}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800 rounded-xl text-sm text-red-300">
          {error}
        </div>
      )}

      {data && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          {/* Top Info Banner */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
                <Package className="w-6 h-6" />
              </div>
              <div>
                <div className="text-lg font-bold text-white font-mono flex items-center gap-2">
                  {data.product_id}
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-sans">
                    {data.product_info.category}
                  </span>
                  {data.product_info.special_handling === 1 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800 flex items-center gap-1 font-sans">
                      <ShieldAlert className="w-3 h-3" /> Special Handling (Zone D)
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">
                  Dims: {data.product_info.length} x {data.product_info.width} x {data.product_info.height} cm | Vol: {data.product_info.volume.toLocaleString()} cm³
                </div>
              </div>
            </div>

            <div className="text-right font-mono">
              <div className="text-xs text-slate-400">Weekly Pick Frequency</div>
              <div className="text-xl font-bold text-amber-400">{data.product_info.avg_weekly_demand} picks/wk</div>
            </div>
          </div>

          {/* Allocation Transition */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
              <span className="text-xs font-mono text-slate-400 uppercase">Original Baseline Slot</span>
              <div className="text-xl font-bold text-slate-200 font-mono mt-1 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-red-400" />
                {data.product_info.baseline_location_id}
              </div>
            </div>

            <div className="bg-emerald-950/20 border border-emerald-800/40 p-4 rounded-xl">
              <span className="text-xs font-mono text-emerald-400 uppercase">SlotIQ Recommended Slot</span>
              <div className="text-xl font-bold text-emerald-300 font-mono mt-1 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-emerald-400" />
                {data.target_location}
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 font-sans font-normal ml-auto">
                  {data.location_info.distance_to_door} m from door
                </span>
              </div>
            </div>
          </div>

          {/* Plain-English Audit Rationale */}
          <div className="p-4 bg-gradient-to-r from-blue-950/40 to-indigo-950/30 border border-blue-800/40 rounded-xl">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider mb-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              SlotIQ AI Operational Explanation
            </div>
            <p className="text-sm text-slate-200 leading-relaxed font-mono">
              "{data.explanation}"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
