import { useState, useRef, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Import, Loader2, CheckCircle, XCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";

const CATEGORIES = [
  { id: "cs.AI", name: "Artificial Intelligence", zh: "人工智能" },
  { id: "cs.LG", name: "Machine Learning", zh: "机器学习" },
  { id: "cs.CV", name: "Computer Vision", zh: "计算机视觉" },
  { id: "cs.CL", name: "Computation and Language", zh: "自然语言处理" },
  { id: "cs.RO", name: "Robotics", zh: "机器人学" },
  { id: "cs.IR", name: "Information Retrieval", zh: "信息检索" },
  { id: "cs.DS", name: "Data Structures and Algorithms", zh: "数据结构与算法" },
  { id: "cs.DB", name: "Databases", zh: "数据库" },
  { id: "cs.SE", name: "Software Engineering", zh: "软件工程" },
  { id: "cs.OS", name: "Operating Systems", zh: "操作系统" },
  { id: "cs.NI", name: "Networking and Internet Architecture", zh: "网络与互联网结构" },
  { id: "cs.CR", name: "Cryptography and Security", zh: "密码学与安全" },
  { id: "cs.HC", name: "Human-Computer Interaction", zh: "人机交互" },
  { id: "cs.SY", name: "Systems and Control", zh: "系统与控制" },
  { id: "cs.MM", name: "Multimedia", zh: "多媒体" },
];

interface ImportDialogProps {
  triggerClassName?: string;
  onImportSuccess?: () => void;
}

export function ImportDialog({ triggerClassName, onImportSuccess }: ImportDialogProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"bulk" | "recent">("bulk");
  const [category, setCategory] = useState("cs.AI");
  const [limit, setLimit] = useState("1000");

  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle");

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const addLog = (message: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleImport = async () => {
    setIsImporting(true);
    setStatus("running");
    setProgress(0);
    setLogs([]);

    try {
      // Step 1: Check ETL Health
      addLog("Checking ETL service health...");
      const etlHealthRes = await fetch("http://localhost:8000/api/etl/status");
      if (!etlHealthRes.ok) throw new Error("ETL service is not healthy");
      setProgress(10);
      addLog("ETL service is healthy.");

      // Step 2: Run ETL
      addLog(`Starting ETL process (Mode: ${mode}, Category: ${category})...`);
      const etlRunRes = await fetch("http://localhost:8000/api/etl/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          categories: category,
          limit: mode === "bulk" ? parseInt(limit) : 50
        }),
      });
      if (!etlRunRes.ok) throw new Error("Failed to start ETL process");
      const etlData = await etlRunRes.json();
      addLog(`ETL completed: ${JSON.stringify(etlData)}`);
      setProgress(30);

      // Step 3: Check Search Health
      addLog("Checking Search service health...");
      const searchHealthRes = await fetch("http://localhost:8000/api/search/health");
      if (!searchHealthRes.ok) throw new Error("Search service is not healthy");
      setProgress(40);
      addLog("Search service is healthy.");

      // Step 4: Create Search Index
      addLog("Creating search index...");
      const createIndexRes = await fetch("http://localhost:8000/api/search/index/create", { method: "POST" });
      if (!createIndexRes.ok) {
        const errorData = await createIndexRes.json();
        if (errorData.detail && errorData.detail.includes("already exists")) {
          addLog("Search index already exists, skipping creation.");
        } else {
          throw new Error(errorData.detail || "Failed to create search index");
        }
      } else {
        addLog("Search index created.");
      }
      setProgress(50);

      // Step 5: Sync to Search
      addLog("Syncing data to Elasticsearch...");
      const syncSearchRes = await fetch("http://localhost:8000/api/search/sync", { method: "POST" });
      if (!syncSearchRes.ok) throw new Error("Failed to sync to Elasticsearch");
      const syncSearchData = await syncSearchRes.json();
      addLog(`Search sync completed: ${syncSearchData.details?.message || "Success"}`);
      setProgress(70);

      // Step 6: Sync Vector DB (Coarse)
      addLog("Syncing Vector DB (Coarse Index)...");
      const syncVectorRes = await fetch("http://localhost:8000/api/rag/sync-coarse", { method: "POST" });
      if (!syncVectorRes.ok) throw new Error("Failed to sync Vector DB");
      setProgress(90);
      addLog("Vector DB sync completed.");

      // Step 7: Check Vector Sync Status
      addLog("Verifying final sync status...");
      const finalStatusRes = await fetch("http://localhost:8000/api/rag/sync-status");
      if (!finalStatusRes.ok) throw new Error("Failed to check final status");
      const finalStatus = await finalStatusRes.json();
      addLog(`Final Status: MongoDB: ${finalStatus.mongodb_count}, Chroma: ${finalStatus.chromadb_count}, In Sync: ${finalStatus.in_sync}`);

      setProgress(100);
      setStatus("success");
      addLog("All steps completed successfully!");

      if (onImportSuccess) {
        onImportSuccess();
      }

    } catch (error: any) {
      console.error(error);
      addLog(`Error: ${error.message || "Unknown error occurred"}`);
      setStatus("error");
    } finally {
      setIsImporting(false);
    }
  };

  const resetDialog = () => {
    setOpen(false);
    setTimeout(() => {
      setStatus("idle");
      setProgress(0);
      setLogs([]);
      setIsImporting(false);
    }, 300);
  };

  return (
    <Dialog open={open} onOpenChange={(val) => !isImporting && (val ? setOpen(true) : resetDialog())} modal>
      <DialogTrigger asChild>
        <Button className={triggerClassName}>
          <Import className="mr-2 h-4 w-4" />
          Import from Arxiv
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Import Papers from Arxiv</DialogTitle>
          <DialogDescription>
            {status === "idle"
              ? "Select a category and import mode to fetch papers."
              : "Importing papers, please wait..."}
          </DialogDescription>
        </DialogHeader>

        {status === "idle" ? (
          <div className="grid gap-6 py-4">
            <div className="grid gap-2">
              <Label>Import Mode</Label>
              <RadioGroup defaultValue="bulk" value={mode} onValueChange={(v) => setMode(v as "bulk" | "recent")} className="grid grid-cols-2 gap-4">
                <div>
                  <RadioGroupItem value="bulk" id="bulk" className="peer sr-only" />
                  <Label
                    htmlFor="bulk"
                    className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary"
                  >
                    <span className="text-base font-semibold">Bulk Import</span>
                    <span className="text-xs text-muted-foreground mt-1">Specify limit (default 1000)</span>
                  </Label>
                </div>
                <div>
                  <RadioGroupItem value="recent" id="recent" className="peer sr-only" />
                  <Label
                    htmlFor="recent"
                    className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary"
                  >
                    <span className="text-base font-semibold">Recent Papers</span>
                    <span className="text-xs text-muted-foreground mt-1">Latest 50 papers</span>
                  </Label>
                </div>
              </RadioGroup>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="category">Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>
                      <span className="font-medium">{cat.id}</span> - {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {mode === "bulk" && (
              <div className="grid gap-2">
                <Label htmlFor="limit">Limit (Optional)</Label>
                <Input
                  id="limit"
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                  placeholder="1000"
                  min="1"
                  max="2000"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of papers to import. Default is 1000.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="w-full" />

            <div className="border rounded-md bg-muted/50 p-4 h-[200px] overflow-hidden flex flex-col">
              <div className="text-xs font-medium mb-2 text-muted-foreground uppercase tracking-wider">Logs</div>
              <ScrollArea className="flex-1">
                <div className="space-y-1">
                  {logs.map((log, i) => (
                    <div key={i} className="text-xs font-mono text-foreground/80 break-all">
                      {log}
                    </div>
                  ))}
                  {status === "running" && (
                    <div className="text-xs font-mono text-muted-foreground animate-pulse">
                      ...
                    </div>
                  )}
                  <div ref={logsEndRef} />
                </div>
              </ScrollArea>
            </div>

            {status === "success" && (
              <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-md border border-green-100">
                <CheckCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Import completed successfully!</span>
              </div>
            )}

            {status === "error" && (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-md border border-red-100">
                <XCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Import failed. Check logs for details.</span>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {status === "idle" ? (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={handleImport}>Start Import</Button>
            </>
          ) : (
            <Button onClick={resetDialog} disabled={status === "running"}>
              {status === "running" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                "Close"
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
