import React, { useState } from 'react';
import { Upload, CheckCircle2, AlertTriangle, FileText, RefreshCw } from 'lucide-react';

export default function UploadPage({ apiBase = 'http://localhost:8000' }) {
  const [fileType, setFileType] = useState('products');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file_type', fileType);
    formData.append('file', file);

    try {
      const res = await fetch(`${apiBase}/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-bold text-white tracking-tight">Dataset Ingestion & Data Quality Auditor</h2>
        <p className="text-sm text-slate-400 mt-1">
          Upload raw warehouse CSVs. SlotIQ cleans dirty rows, resolves unavailable locations, and records an auditable data-quality log.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">1. Select Entity Type</label>
          <select
            value={fileType}
            onChange={(e) => setFileType(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="products">Products (Dims, 12w Demand, Handling)</option>
            <option value="locations">Locations (Grid, Capacity, Distance)</option>
            <option value="orders">Orders (Order ID, Product, Week)</option>
          </select>

          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mt-5 mb-2">2. Upload File</label>
          <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-6 text-center cursor-pointer transition">
            <input
              type="file"
              accept=".csv"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
              id="csv-file-input"
            />
            <label htmlFor="csv-file-input" className="cursor-pointer flex flex-col items-center">
              <Upload className="w-8 h-8 text-blue-400 mb-2" />
              <span className="text-sm font-medium text-slate-200">
                {uploading ? 'Validating & Ingesting...' : 'Choose CSV file to audit'}
              </span>
              <span className="text-xs text-slate-500 mt-1">Supports products_dirty.csv, locations.csv, etc.</span>
            </label>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-xs text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="md:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              Automated Data Quality Audit Summary
            </h3>
            {result && (
              <span className="text-xs px-2.5 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full font-mono">
                Cleaned {result.filename}
              </span>
            )}
          </div>

          {!result ? (
            <div className="h-64 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800/80 rounded-lg">
              <RefreshCw className="w-8 h-8 text-slate-600 mb-2 animate-spin" style={{ animationDuration: '6s' }} />
              <p className="text-sm">Upload a dirty CSV file to inspect the line-by-line cleaner audit trail.</p>
              <p className="text-xs text-slate-600 mt-1">Try uploading <code className="text-slate-400">slotiq/data/products_dirty.csv</code></p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Anomalies Detected</div>
                  <div className="text-xl font-bold text-white mt-1">{result.audit_report.total_issues}</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-red-400">Rows Rejected</div>
                  <div className="text-xl font-bold text-red-400 mt-1">{result.audit_report.rejected_count}</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-amber-400">Rows Auto-Fixed</div>
                  <div className="text-xl font-bold text-amber-400 mt-1">{result.audit_report.fixed_count}</div>
                </div>
              </div>

              <div className="max-h-64 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/60 divide-y divide-slate-800/60 font-mono text-xs">
                {result.audit_report.details.map((item, idx) => (
                  <div key={idx} className="p-2.5 flex items-center justify-between hover:bg-slate-900/60 transition">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        item.action === 'REJECTED' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}>
                        {item.action}
                      </span>
                      <span className="text-slate-300 font-semibold">{item.row_id}</span>
                      <span className="text-slate-400">({item.dataset})</span>
                    </div>
                    <span className="text-slate-400 text-right">{item.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
