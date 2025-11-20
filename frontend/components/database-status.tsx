"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, Database, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusResponse {
  mongodb_count: number;
  elasticsearch_count: number;
  in_sync: boolean;
}

export function DatabaseStatus() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/search/status");
      if (!res.ok) throw new Error("Failed to fetch status");
      const json: StatusResponse = await res.json();
      setStatus(json);
      setError(false);
    } catch (err) {
      console.error(err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 10 seconds
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !status) {
    return <div className="text-xs text-muted-foreground flex items-center gap-2"><RefreshCw className="h-3 w-3 animate-spin" /> Loading status...</div>;
  }

  if (error) {
    return <div className="text-xs text-red-500 flex items-center gap-2"><XCircle className="h-3 w-3" /> Status Error</div>;
  }

  if (!status) return null;

  return (
    <div className="flex items-center gap-4 text-xs border rounded-md px-3 py-1.5 bg-muted/50">
      <div className="flex items-center gap-1.5" title="MongoDB Count">
        <Database className="h-3 w-3 text-green-600" />
        <span className="font-medium">Mongo:</span>
        <span>{status.mongodb_count.toLocaleString()}</span>
      </div>
      <div className="w-px h-3 bg-border" />
      <div className="flex items-center gap-1.5" title="Elasticsearch Count">
        <Database className="h-3 w-3 text-yellow-600" />
        <span className="font-medium">ES:</span>
        <span>{status.elasticsearch_count.toLocaleString()}</span>
      </div>
      <div className="w-px h-3 bg-border" />
      <div className={cn("flex items-center gap-1.5 font-medium", status.in_sync ? "text-green-600" : "text-red-500")}>
        {status.in_sync ? (
          <>
            <CheckCircle2 className="h-3 w-3" />
            <span>In Sync</span>
          </>
        ) : (
          <>
            <XCircle className="h-3 w-3" />
            <span>Out of Sync</span>
          </>
        )}
      </div>
    </div>
  );
}
