"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Import } from "lucide-react";

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
}

export function ImportDialog({ triggerClassName }: ImportDialogProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"bulk" | "recent">("bulk");
  const [category, setCategory] = useState("cs.AI");
  const [limit, setLimit] = useState("1000");

  const handleImport = () => {
    console.log("Importing with:", { mode, category, limit: mode === "bulk" ? limit : 50 });
    setOpen(false);
    // TODO: Implement actual import logic
  };

  return (
    <Dialog open={open} onOpenChange={setOpen} modal>
      <DialogTrigger asChild>
        <Button className={triggerClassName}>
          <Import className="mr-2 h-4 w-4" />
          Import from Arxiv
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Import Papers from Arxiv</DialogTitle>
          <DialogDescription>
            Select a category and import mode to fetch papers.
          </DialogDescription>
        </DialogHeader>
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
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleImport}>Start Import</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
