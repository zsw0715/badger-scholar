"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Search, Calendar as CalendarIcon, Loader2, X } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

const CATEGORIES = [
  { id: "cs.AI", name: "Artificial Intelligence" },
  { id: "cs.LG", name: "Machine Learning" },
  { id: "cs.CV", name: "Computer Vision" },
  { id: "cs.CL", name: "Computation and Language" },
  { id: "cs.RO", name: "Robotics" },
  { id: "cs.IR", name: "Information Retrieval" },
];

interface SearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPaperClick: (paper: { arxiv_id: string; title: string }) => void;
}

interface SearchResult {
  arxiv_id: string;
  title: string;
  summary: string;
  authors: string[];
  published: string;
  categories: string[];
  score: number;
  title_highlight?: string;
  summary_highlight?: string;
}

interface SearchResponse {
  total: number;
  page: number;
  size: number;
  took: number;
  results: SearchResult[];
}

export function SearchDialog({ open, onOpenChange, onPaperClick }: SearchDialogProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("");
  const [author, setAuthor] = useState("");
  const [fromDate, setFromDate] = useState<Date>();
  const [toDate, setToDate] = useState<Date>();
  const [page, setPage] = useState(1);
  const [size] = useState(10);

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);

  const performSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        q: query,
        page: page.toString(),
        size: size.toString(),
      });

      if (category) params.append("category", category);
      if (author) params.append("author", author);
      if (fromDate) params.append("from_date", format(fromDate, "yyyy-MM-dd"));
      if (toDate) params.append("to_date", format(toDate, "yyyy-MM-dd"));

      const res = await fetch(`http://localhost:8000/api/search?${params}`);
      if (!res.ok) throw new Error("Search failed");

      const data: SearchResponse = await res.json();
      setResults(data);
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (query) {
      const debounce = setTimeout(() => {
        performSearch();
      }, 500);
      return () => clearTimeout(debounce);
    } else {
      setResults(null);
    }
  }, [query, category, author, fromDate, toDate, page]);

  const totalPages = results ? Math.ceil(results.total / size) : 0;

  const clearFilters = () => {
    setCategory("");
    setAuthor("");
    setFromDate(undefined);
    setToDate(undefined);
    setPage(1);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px] h-[700px] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 border-b">
          <DialogTitle>Search Papers</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4 border-b">
          {/* Search Query */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search papers by title, author, or abstract..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="pl-10"
              autoFocus
            />
          </div>

          {/* Filters */}
          <div className="grid grid-cols-4 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Category</Label>
              <Select value={category} onValueChange={(v) => { setCategory(v); setPage(1); }}>
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>
                      {cat.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Author</Label>
              <Input
                placeholder="Author name"
                value={author}
                onChange={(e) => { setAuthor(e.target.value); setPage(1); }}
                className="h-9"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs">From Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "h-9 w-full justify-start text-left font-normal",
                      !fromDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {fromDate ? format(fromDate, "yyyy-MM-dd") : <span>Pick a date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={fromDate}
                    onSelect={(date) => { setFromDate(date); setPage(1); }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">To Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "h-9 w-full justify-start text-left font-normal",
                      !toDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {toDate ? format(toDate, "yyyy-MM-dd") : <span>Pick a date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={toDate}
                    onSelect={(date) => { setToDate(date); setPage(1); }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {(category || author || fromDate || toDate) && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8">
              <X className="mr-2 h-3 w-3" />
              Clear Filters
            </Button>
          )}
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : results ? (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Found {results.total} results ({results.took}ms)
              </div>
              {results.results.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  No papers found. Try adjusting your filters.
                </div>
              ) : (
                results.results.map((paper) => (
                  <div
                    key={paper.arxiv_id}
                    className="border rounded-2xl p-4 hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => {
                      onPaperClick({ arxiv_id: paper.arxiv_id, title: paper.title });
                      onOpenChange(false);
                    }}
                  >
                    <h3
                      className="font-semibold text-base mb-2"
                      dangerouslySetInnerHTML={{ __html: paper.title_highlight || paper.title }}
                    />
                    <div className="text-xs text-muted-foreground mb-2">
                      {paper.authors.slice(0, 3).join(", ")}
                      {paper.authors.length > 3 && " et al."} · {new Date(paper.published).toLocaleDateString()} · {paper.categories[0]}
                    </div>
                    <p
                      className="text-sm text-muted-foreground line-clamp-2"
                      dangerouslySetInnerHTML={{ __html: paper.summary_highlight || paper.summary }}
                    />
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Enter a search query to find papers
            </div>
          )}
        </div>

        {/* Pagination */}
        {results && results.total > 0 && (
          <div className="border-t p-3">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                    className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>

                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = i + 1;
                  return (
                    <PaginationItem key={pageNum}>
                      <PaginationLink
                        href="#"
                        isActive={page === pageNum}
                        onClick={(e) => {
                          e.preventDefault();
                          setPage(pageNum);
                        }}
                      >
                        {pageNum}
                      </PaginationLink>
                    </PaginationItem>
                  );
                })}

                <PaginationItem>
                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                    className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
