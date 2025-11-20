"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PdfViewerDialog } from "@/components/pdf-viewer-dialog";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface Chunk {
  chunk_id: string;
  arxiv_id: string;
  text: string;
  score: number;
}

interface ChunksCarouselProps {
  chunks: Chunk[];
  animationDelay?: number;
}

export function ChunksCarousel({ chunks, animationDelay = 0 }: ChunksCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedPaper, setSelectedPaper] = useState<{ arxiv_id: string; title: string } | null>(null);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : chunks.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < chunks.length - 1 ? prev + 1 : 0));
  };

  const currentChunk = chunks[currentIndex];

  return (
    <>
      <div
        className="mt-4 opacity-0 animate-fadeInUp"
        style={{
          animationDelay: `${animationDelay}ms`,
          animationFillMode: 'forwards'
        }}
      >
        <p className="text-xs font-semibold mb-3 text-muted-foreground">
          Top Retrieved Chunks ({chunks.length})
        </p>
        <div className="relative">
          <div 
            className="bg-muted/30 border border-border rounded-2xl p-4 space-y-2 cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => {
              setSelectedPaper({
                arxiv_id: currentChunk.arxiv_id,
                title: `Paper ${currentChunk.arxiv_id}`
              });
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                {currentChunk.chunk_id}
              </span>
              <span className="text-xs font-semibold text-green-500 whitespace-nowrap">
                Score: {currentChunk.score.toFixed(4)}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Paper: {currentChunk.arxiv_id}
            </div>
            <div className="text-xs leading-relaxed pt-2 border-t break-words">
              {currentChunk.text}
            </div>
          </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-3">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={(e) => {
              e.stopPropagation();
              handlePrev();
            }}
            disabled={chunks.length <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <span className="text-xs text-muted-foreground">
            {currentIndex + 1} / {chunks.length}
          </span>

          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={(e) => {
              e.stopPropagation();
              handleNext();
            }}
            disabled={chunks.length <= 1}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        </div>
      </div>

      {/* PDF Viewer Dialog */}
      <PdfViewerDialog
        paper={selectedPaper}
        open={!!selectedPaper}
        onOpenChange={(open) => !open && setSelectedPaper(null)}
      />
    </>
  );
}
