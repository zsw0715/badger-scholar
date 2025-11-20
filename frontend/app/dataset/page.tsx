"use client";

import { useEffect, useState } from "react";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Button } from "@/components/ui/button";
import { FileText, Import } from "lucide-react";
import { ImportDialog } from "@/components/import-dialog";
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from "@/components/ui/pagination";
import { DatabaseStatus } from "@/components/database-status";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Paper {
    _id: string;
    arxiv_id: string;
    title: string;
    summary: string;
    authors: string[];
    published: string;
    categories: string[];
}

interface ApiResponse {
    total: number;
    page: number;
    page_size: number;
    data: Paper[];
}

export default function Dataset() {
    const [data, setData] = useState<Paper[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [total, setTotal] = useState(0);
    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const res = await fetch(`http://localhost:8000/api/etl/papers?page=${page}&page_size=${pageSize}`);
                if (!res.ok) {
                    throw new Error("Failed to fetch data");
                }
                const json: ApiResponse = await res.json();
                setData(json.data || []);
                setTotal(json.total || 0);
                // setData([]);
                // setTotal(0);
            } catch (err) {
                console.error(err);
                setError("Failed to load data");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [page, pageSize]);

    const totalPages = Math.ceil(total / pageSize);

    if (error) {
        return <div className="flex items-center justify-center h-[calc(100vh-48px)] text-red-500">{error}</div>;
    }

    if (!loading && data.length === 0) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-48px)] p-4 pb-36">
                <Empty>
                    <EmptyHeader>
                        <EmptyMedia variant="icon">
                            <FileText className="w-12 h-12 text-muted-foreground" />
                        </EmptyMedia>
                        <EmptyTitle>No Papers Found</EmptyTitle>
                        <EmptyDescription>
                            Your dataset is currently empty. Import papers from Arxiv to get started.
                        </EmptyDescription>
                    </EmptyHeader>
                    <EmptyContent>
                        <ImportDialog />
                    </EmptyContent>
                </Empty>
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-48px)] flex flex-col relative overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 pb-20">
                <div className="container mx-auto max-w-5xl">
                    <div className="flex items-center justify-between mb-4">
                        <h1 className="text-xl font-bold">Dataset ({total})</h1>
                        <div className="text-sm text-muted-foreground">
                            Page {page} of {totalPages}
                        </div>
                    </div>
                    <div className="grid gap-2">
                        {loading ? (
                            <div className="text-center py-10">Loading...</div>
                        ) : (
                            data.map((paper) => (
                                <div
                                    key={paper._id}
                                    className="p-3 border rounded-md shadow-sm hover:bg-accent/50 transition-colors flex flex-col gap-1 cursor-pointer"
                                    onClick={() => setSelectedPaper(paper)}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <h2 className="text-base font-semibold leading-tight line-clamp-1">{paper.title}</h2>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
                                            {new Date(paper.published).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span className="font-medium text-foreground">{paper.authors.slice(0, 3).join(", ")}{paper.authors.length > 3 ? " et al." : ""}</span>
                                        <span>•</span>
                                        <span className="bg-secondary px-1.5 py-0.5 rounded text-[10px]">{paper.categories?.[0]}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                        {paper.summary}
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Fixed Pagination Bar */}
            <div className="absolute bottom-0 left-0 right-0 bg-background border-t p-2 z-10 flex items-center justify-between gap-4">
                <div className="flex-1">
                    <Pagination className="justify-start">
                        <PaginationContent>
                            <PaginationItem>
                                <PaginationPrevious
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        if (page > 1) setPage(page - 1);
                                    }}
                                    className={page <= 1 ? "pointer-events-none opacity-50" : ""}
                                />
                            </PaginationItem>

                            {(() => {
                                const items = [];
                                const showStart = 3;
                                const showEnd = 3;
                                const showAround = 2; // Current +/- 2

                                // Generate set of pages to show
                                const pages = new Set<number>();

                                // Add first few
                                for (let i = 1; i <= Math.min(showStart, totalPages); i++) pages.add(i);

                                // Add last few
                                for (let i = Math.max(1, totalPages - showEnd + 1); i <= totalPages; i++) pages.add(i);

                                // Add around current
                                for (let i = Math.max(1, page - showAround); i <= Math.min(totalPages, page + showAround); i++) pages.add(i);

                                const sortedPages = Array.from(pages).sort((a, b) => a - b);

                                // Build items with ellipsis
                                for (let i = 0; i < sortedPages.length; i++) {
                                    const p = sortedPages[i];

                                    // Check for gap before this page
                                    if (i > 0 && p > sortedPages[i - 1] + 1) {
                                        items.push(
                                            <PaginationItem key={`ellipsis-${p}`}>
                                                <PaginationEllipsis />
                                            </PaginationItem>
                                        );
                                    }

                                    items.push(
                                        <PaginationItem key={p}>
                                            <PaginationLink
                                                href="#"
                                                isActive={page === p}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    setPage(p);
                                                }}
                                            >
                                                {p}
                                            </PaginationLink>
                                        </PaginationItem>
                                    );
                                }
                                return items;
                            })()}

                            <PaginationItem>
                                <PaginationNext
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        if (page < totalPages) setPage(page + 1);
                                    }}
                                    className={page >= totalPages ? "pointer-events-none opacity-50" : ""}
                                />
                            </PaginationItem>
                        </PaginationContent>
                    </Pagination>
                </div>

                <div className="flex items-center gap-2 mr-4">
                    <ImportDialog triggerClassName="border-4 border-zinc-200 dark:border-zinc-700" />
                    <Button variant="destructive" onClick={() => alert("Drop dataset functionality coming soon!")}>
                        Drop Dataset
                    </Button>
                    <div className="h-8 w-px bg-border mx-2" />
                    <DatabaseStatus />
                </div>
            </div>

            <Dialog open={!!selectedPaper} onOpenChange={(open) => !open && setSelectedPaper(null)}>
                <DialogContent className="sm:max-w-[90vw] w-[90vw] h-[90vh] flex flex-col p-0 gap-0">
                    <DialogHeader className="p-4 border-b">
                        <DialogTitle>{selectedPaper?.title}</DialogTitle>
                    </DialogHeader>
                    <div className="flex-1 w-full h-full bg-muted overflow-hidden">
                        {selectedPaper && (
                            <iframe
                                src={`https://arxiv.org/pdf/${selectedPaper.arxiv_id}`}
                                className="w-full h-full border-none"
                                title="PDF Preview"
                            />
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
