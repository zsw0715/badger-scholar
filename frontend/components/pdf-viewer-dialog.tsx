"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Paper {
  arxiv_id: string;
  title: string;
}

interface PdfViewerDialogProps {
  paper: Paper | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PdfViewerDialog({ paper, open, onOpenChange }: PdfViewerDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[90vw] w-[90vw] h-[90vh] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 border-b">
          <DialogTitle>{paper?.title}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 w-full h-full bg-muted overflow-hidden">
          {paper && (
            <iframe
              src={`https://arxiv.org/pdf/${paper.arxiv_id}`}
              className="w-full h-full border-none"
              title="PDF Preview"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
