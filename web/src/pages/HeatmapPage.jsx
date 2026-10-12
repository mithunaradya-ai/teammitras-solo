import React, { useEffect, useState } from 'react';
import { Layers, MapPin, Info } from 'lucide-react';

function WarehouseGrid({ title, locations, subtitle, badgeColor }) {
  const [hovered, setHovered] = useState(null);

  // Group locations by zone: A, B, C, D
  const zones = ['A', 'B', 'C', 'D'];
  const byZone = {};
  zones.forEach(z => { byZone[z] = []; });
  (locations || []).forEach(l => {
    if (byZone[l.zone]) byZone[l.zone].push(l);
  });

  const getHeatColor = (picks) => {
    if (!picks || picks === 0) return 'bg-slate-800/60 border-slate-700/40 text-slate-500';
    if (picks > 150) return 'bg-red-500 text-white font-bold shadow-sm shadow-red-500/50';
    if (picks > 80) return 'bg-amber-500 text-slate-900 font-bold';
    if (picks > 30) return 'bg-emerald-600 text-white';
    if (picks > 10) return 'bg-blue-600 text-white';
    return 'bg-blue-950/80 border border-blue-800/40 text-blue-300';
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-1.5">{title}</h3>
          <p className="text-[11px] text-slate-400">{subtitle}</p>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${badgeColor}`}>
          Door @ (0,0)
        </span>
      </div>

      {/* Grid of zones */}
      <div className="space-y-3 flex-1">
        {zones.map(z => (
          <div key={z} className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
            <div className="text-[10px] font-mono font-bold text-slate-400 mb-1.5 flex justify-between">
              <span>ZONE {z} {z === 'D' && '(Special Handling)'}</span>
              <span className="text-slate-500">{byZone[z].length} Bins</span>
            </div>
            <div className="grid grid-cols-10 gap-1">
              {byZone[z].map(loc => (
                <div
                  key={loc.location_id}
                  onMouseEnter={() => setHovered(loc)}
                  onMouseLeave={() => setHovered(null)}
                  className={`h-5 rounded flex items-center justify-center text-[9px] cursor-pointer transition transform hover:scale-125 hover:z-20 ${
                    loc.available === 0 ? 'bg-zinc-800 border border-red-900/60 text-zinc-600 opacity-40' : getHeatColor(loc.picks)
                  }`}
                >
                  {loc.assigned_product ? loc.assigned_product.replace('P', '') : '·'}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Tooltip Card */}
      <div className="mt-3 p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono h-14 flex items-center">
        {hovered ? (
          <div className="flex justify-between w-full">
            <div>
              <span className="font-bold text-blue-400">{hovered.location_id}</span>
              <span className="text-slate-400 mx-1.5">|</span>
              <span className="text-white font-semibold">{hovered.assigned_product || 'EMPTY'}</span>
              <span className="text-slate-400 ml-1.5">({hovered.category || 'N/A'})</span>
            </div>
            <div>
              <span className="text-amber-400 font-bold">{hovered.picks} picks/wk</span>
              <span className="text-slate-500 mx-1.5">|</span>
              <span className="text-slate-300">{hovered.distance_to_door} m to door</span>
            </div>
          </div>
        ) : (
          <span className="text-slate-500 text-[11px] flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" /> Hover over any slot cell to inspect assigned SKU, pick volume, and door distance.
          </span>
        )}
      </div>
    </div>
  );
}

export default function HeatmapPage({ apiBase = 'http://localhost:8000' }) {
  const [baselineLocs, setBaselineLocs] = useState([]);
  const [optimizedLocs, setOptimizedLocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHeatmaps() {
      setLoading(true);
      try {
        const [resBase, resOpt] = await Promise.all([
          fetch(`${apiBase}/layout?strategy=baseline`),
          fetch(`${apiBase}/layout?strategy=forecast_affinity`)
        ]);
        const dataBase = await resBase.json();
        const dataOpt = await resOpt.json();
        setBaselineLocs(dataBase.locations);
        setOptimizedLocs(dataOpt.locations);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadHeatmaps();
  }, [apiBase]);

  return (
    <div className="space-y-5">
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Layers className="w-6 h-6 text-blue-400" />
          Warehouse Spatial Density Heatmap (Before vs After)
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Visual comparison showing how high-velocity SKUs are pulled from distant back zones (C & D) directly into golden zones near the dispatch door.
        </p>
      </div>

      {/* Heatmap Legend */}
      <div className="flex flex-wrap items-center gap-4 p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-xs font-mono">
        <span className="text-slate-400 font-bold uppercase">Pick Velocity:</span>
        <div className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded bg-red-500"></span><span className="text-slate-300">&gt;150/wk (Prime)</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded bg-amber-500"></span><span className="text-slate-300">80-150/wk</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded bg-emerald-600"></span><span className="text-slate-300">30-80/wk</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded bg-blue-600"></span><span className="text-slate-300">10-30/wk</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded bg-blue-950 border border-blue-800"></span><span className="text-slate-400">&lt;10/wk</span></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WarehouseGrid
          title="Baseline Layout (Suboptimal / Random)"
          subtitle="High velocity picks scattered indiscriminately up to 70 meters from door"
          locations={baselineLocs}
          badgeColor="bg-red-950 text-red-400 border border-red-800"
        />
        <WarehouseGrid
          title="SlotIQ Optimized (Forecast + Affinity)"
          subtitle="High picks concentrated into Zone A & B within 15 meters of door"
          locations={optimizedLocs}
          badgeColor="bg-emerald-950 text-emerald-400 border border-emerald-800"
        />
      </div>
    </div>
  );
}
