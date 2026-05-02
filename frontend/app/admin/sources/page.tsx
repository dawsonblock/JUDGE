"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface SourceRegistry {
  id: number;
  source_key: string;
  source_name: string;
  source_type: string;
  country?: string;
  province_state?: string;
  city?: string;
  source_tier: string;
  is_active: boolean;
  rate_limit_rpm?: number;
  health_score: number;
  last_successful_fetch?: string;
  last_ingested_at?: string;
  admin_notes?: string;
  created_at: string;
  updated_at: string;
}

interface SourceHealth {
  health_score: number;
  last_successful_fetch?: string;
  last_error?: string;
  last_error_at?: string;
  last_ingested_at?: string;
  recent_run_count: number;
  recent_error_count: number;
}

interface IngestionRun {
  id: number;
  status: string;
  started_at: string;
  finished_at?: string;
  fetched_count: number;
  parsed_count: number;
  persisted_count: number;
  error_count: number;
}

export default function AdminSourcesPage() {
  const [sources, setSources] = useState<SourceRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);
  const [health, setHealth] = useState<Record<string, SourceHealth>>({});
  const [runs, setRuns] = useState<Record<string, IngestionRun[]>>({});
  const [loadingDetails, setLoadingDetails] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("jta_admin_token");
    if (!storedToken) {
      setError("Admin token not found. Please provide JTA_ADMIN_TOKEN.");
      setLoading(false);
      return;
    }
    setToken(storedToken);
  }, []);

  useEffect(() => {
    if (!token) return;
    loadSources();
  }, [token]);

  const loadSources = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch("/api/admin/sources", {
        headers: {
          Accept: "application/json",
          "X-JTA-Admin-Token": token,
        },
      });
      if (!res.ok) throw new Error("Failed to load sources");
      const data = await res.json();
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const loadSourceDetails = async (sourceKey: string) => {
    if (!token) return;
    try {
      setLoadingDetails((prev) => ({ ...prev, [sourceKey]: true }));

      // Load health
      const healthRes = await fetch(`/api/admin/sources/${sourceKey}/health`, {
        headers: {
          Accept: "application/json",
          "X-JTA-Admin-Token": token,
        },
      });
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth((prev) => ({ ...prev, [sourceKey]: healthData }));
      }

      // Load runs
      const runsRes = await fetch(`/api/admin/sources/${sourceKey}/runs?limit=5`, {
        headers: {
          Accept: "application/json",
          "X-JTA-Admin-Token": token,
        },
      });
      if (runsRes.ok) {
        const runsData = await runsRes.json();
        setRuns((prev) => ({ ...prev, [sourceKey]: runsData }));
      }
    } catch (err) {
      console.error("Failed to load source details:", err);
    } finally {
      setLoadingDetails((prev) => ({ ...prev, [sourceKey]: false }));
    }
  };

  const toggleSource = async (sourceKey: string, isActive: boolean) => {
    if (!token) return;
    try {
      const action = isActive ? "disable" : "enable";
      const res = await fetch(`/api/admin/sources/${sourceKey}/${action}`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-JTA-Admin-Token": token,
        },
      });
      if (!res.ok) throw new Error(`Failed to ${action} source`);
      
      showToast(`Source ${action}d successfully`);
      await loadSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleExpand = (sourceKey: string) => {
    if (expandedSource === sourceKey) {
      setExpandedSource(null);
    } else {
      setExpandedSource(sourceKey);
      loadSourceDetails(sourceKey);
    }
  };

  if (loading) return <div className="p-4">Loading sources...</div>;
  if (error) return <div className="p-4 text-red-600">Error: {error}</div>;

  return (
    <div className="p-6 bg-white">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Source Registry</h1>
        <p className="text-gray-600">
          Ingestion sources. Disabled sources will not run. Enable to allow ingestion.
        </p>
      </div>

      {toastMessage && (
        <div className="mb-4 p-3 bg-green-100 text-green-800 rounded-lg">
          {toastMessage}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead className="bg-gray-100">
            <tr>
              <th className="border border-gray-300 p-3 text-left">Source Key</th>
              <th className="border border-gray-300 p-3 text-left">Name</th>
              <th className="border border-gray-300 p-3 text-left">Type</th>
              <th className="border border-gray-300 p-3 text-center">Status</th>
              <th className="border border-gray-300 p-3 text-center">Health</th>
              <th className="border border-gray-300 p-3 text-center">Last Fetch</th>
              <th className="border border-gray-300 p-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.source_key} className="hover:bg-gray-50">
                <td className="border border-gray-300 p-3 font-mono text-sm">
                  {source.source_key}
                </td>
                <td className="border border-gray-300 p-3">{source.source_name}</td>
                <td className="border border-gray-300 p-3 text-sm text-gray-600">
                  {source.source_type}
                </td>
                <td className="border border-gray-300 p-3 text-center">
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-semibold ${
                      source.is_active
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {source.is_active ? "ENABLED" : "DISABLED"}
                  </span>
                </td>
                <td className="border border-gray-300 p-3 text-center">
                  <span className="text-sm">
                    {(source.health_score * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="border border-gray-300 p-3 text-center">
                  <span className="text-sm text-gray-600">
                    {source.last_successful_fetch
                      ? new Date(source.last_successful_fetch).toLocaleDateString()
                      : "Never"}
                  </span>
                </td>
                <td className="border border-gray-300 p-3 text-center space-x-2">
                  <button
                    onClick={() => toggleSource(source.source_key, source.is_active)}
                    className={`px-3 py-1 rounded text-sm font-semibold ${
                      source.is_active
                        ? "bg-red-500 hover:bg-red-600 text-white"
                        : "bg-green-500 hover:bg-green-600 text-white"
                    }`}
                  >
                    {source.is_active ? "Disable" : "Enable"}
                  </button>
                  <button
                    onClick={() => handleExpand(source.source_key)}
                    className="px-3 py-1 rounded text-sm font-semibold bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    {expandedSource === source.source_key ? "Hide" : "Details"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Expanded details */}
      {expandedSource && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-300">
          <h2 className="text-xl font-bold mb-4">
            Details: {expandedSource}
          </h2>

          {loadingDetails[expandedSource] ? (
            <p className="text-gray-600">Loading details...</p>
          ) : (
            <>
              {/* Health metrics */}
              {health[expandedSource] && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Health Metrics (Last 7 Days)</h3>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <div className="bg-white p-3 rounded border border-gray-200">
                      <p className="text-gray-600 text-sm">Health Score</p>
                      <p className="text-2xl font-bold">
                        {(health[expandedSource].health_score * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div className="bg-white p-3 rounded border border-gray-200">
                      <p className="text-gray-600 text-sm">Recent Runs</p>
                      <p className="text-2xl font-bold">
                        {health[expandedSource].recent_run_count}
                      </p>
                    </div>
                    <div className="bg-white p-3 rounded border border-gray-200">
                      <p className="text-gray-600 text-sm">Error Count</p>
                      <p className="text-2xl font-bold text-red-600">
                        {health[expandedSource].recent_error_count}
                      </p>
                    </div>
                    <div className="bg-white p-3 rounded border border-gray-200">
                      <p className="text-gray-600 text-sm">Last Fetch</p>
                      <p className="text-sm">
                        {health[expandedSource].last_successful_fetch
                          ? new Date(
                              health[expandedSource].last_successful_fetch || ""
                            ).toLocaleDateString()
                          : "Never"}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Recent runs */}
              {runs[expandedSource] && runs[expandedSource].length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Recent Runs</h3>
                  <div className="space-y-2">
                    {runs[expandedSource].map((run) => (
                      <div
                        key={run.id}
                        className="bg-white p-3 rounded border border-gray-200"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-sm">Run #{run.id}</span>
                          <span
                            className={`px-2 py-1 rounded text-xs font-semibold ${
                              run.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : run.status === "failed"
                                ? "bg-red-100 text-red-800"
                                : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {run.status}
                          </span>
                        </div>
                        <p className="text-gray-600 text-xs mt-1">
                          {new Date(run.started_at).toLocaleString()} — Fetched:{" "}
                          {run.fetched_count}, Parsed: {run.parsed_count}, Persisted:{" "}
                          {run.persisted_count}, Errors: {run.error_count}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">Control Principle</h3>
        <p className="text-sm text-blue-800">
          <strong>is_active = true</strong> → ingestion can run. <br />
          <strong>is_active = false</strong> → ingestion fails closed. <br />
          The database field <code className="bg-blue-100 px-1 rounded">SourceRegistry.is_active</code> is the only runtime ingestion switch. No frontend state override.
        </p>
      </div>
    </div>
  );
}
