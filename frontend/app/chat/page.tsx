"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChunksCarousel } from "@/components/chunks-carousel";
import { PdfViewerDialog } from "@/components/pdf-viewer-dialog";
import { Send, Loader2, FileText, Bot, Database, CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface Message {
    role: "user" | "assistant";
    content: string;
    papers?: any[];
    chunks?: any[];
}

interface CoarseSyncStatus {
    mongodb_count: number;
    chromadb_count: number;
    in_sync: boolean;
}

interface FineSyncStatus {
    chromadb_count: number;
    fulltext_indexed_papers: number;
    in_sync: boolean;
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [topKPapers, setTopKPapers] = useState("5");
    const [topKChunks, setTopKChunks] = useState("8");
    const [coarseStatus, setCoarseStatus] = useState<CoarseSyncStatus | null>(null);
    const [fineStatus, setFineStatus] = useState<FineSyncStatus | null>(null);
    const [needsTopPadding, setNeedsTopPadding] = useState(false);
    const [selectedPaper, setSelectedPaper] = useState<{ arxiv_id: string; title: string } | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Check if content height exceeds viewport height
    useEffect(() => {
        const checkContentHeight = () => {
            if (contentRef.current) {
                const contentHeight = contentRef.current.scrollHeight;
                const viewportHeight = window.innerHeight;
                setNeedsTopPadding(contentHeight > viewportHeight);
            }
        };

        checkContentHeight();
        window.addEventListener('resize', checkContentHeight);

        return () => window.removeEventListener('resize', checkContentHeight);
    }, [messages]);

    // Fetch sync status periodically
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const [coarseRes, fineRes] = await Promise.all([
                    fetch("http://localhost:8000/api/rag/sync-status"),
                    fetch("http://localhost:8000/api/rag/sync-status/fulltext"),
                ]);

                if (coarseRes.ok) {
                    const data = await coarseRes.json();
                    setCoarseStatus(data);
                }

                if (fineRes.ok) {
                    const data = await fineRes.json();
                    setFineStatus(data);
                }
            } catch (error) {
                console.error("Failed to fetch sync status:", error);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 10000); // Poll every 10 seconds

        return () => clearInterval(interval);
    }, []);

    const getFulltextColor = (count: number) => {
        if (count < 50) return "text-green-500";
        if (count <= 65) return "text-yellow-500";
        return "text-red-500";
    };

    const getFulltextIcon = (count: number) => {
        if (count < 50) return <CheckCircle className="w-4 h-4 text-green-500" />;
        if (count <= 65) return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
        return <XCircle className="w-4 h-4 text-red-500" />;
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            role: "user",
            content: input,
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setLoading(true);

        try {
            const res = await fetch("http://localhost:8000/api/rag/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: input,
                    top_k_papers: parseInt(topKPapers),
                    top_k_chunks: parseInt(topKChunks),
                }),
            });

            if (!res.ok) throw new Error("Failed to get answer");

            const data = await res.json();

            const assistantMessage: Message = {
                role: "assistant",
                content: data.answer,
                papers: data.papers,
                chunks: data.chunks,
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error:", error);
            const errorMessage: Message = {
                role: "assistant",
                content: "Sorry, I encountered an error while processing your question.",
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-full flex">
            {/* Sidebar - Reserved for Chat History */}
            <div className="w-80 border-r bg-gray-400/10 dark:bg-zinc-950 p-4 flex flex-col">
                {/* TODO: Add chat history */}
                <div className="flex-1" />

                {/* Sync Status Monitor */}
                <div className="space-y-3 pt-4 border-t border-gray-400/20 dark:border-zinc-800">
                    <div className="flex items-center gap-2 mb-2">
                        <Database className="w-4 h-4 text-zinc-800 dark:text-zinc-400" />
                        <h3 className="text-sm font-semibold text-zinc-800 dark:text-white">Sync Status</h3>
                    </div>

                    {/* Coarse Grained Status */}
                    <div className="bg-gray-400/10 dark:bg-zinc-900 rounded-2xl p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-zinc-800 dark:text-zinc-400">Coarse (Papers)</span>
                            {coarseStatus?.in_sync ? (
                                <CheckCircle className="w-3 h-3 text-green-500" />
                            ) : (
                                <XCircle className="w-3 h-3 text-red-500" />
                            )}
                        </div>
                        <p className="text-[10px] text-zinc-800 dark:text-zinc-500 leading-tight mb-2">
                            Stage 1: Retrieves relevant papers using summary embeddings
                        </p>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-800 dark:text-zinc-500">MongoDB:</span>
                            <span className="text-zinc-800 dark:text-white">{coarseStatus?.mongodb_count ?? 0}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-800 dark:text-zinc-500">ChromaDB:</span>
                            <span className="text-zinc-800 dark:text-white">{coarseStatus?.chromadb_count ?? 0}</span>
                        </div>
                    </div>

                    {/* Fine Grained Status */}
                    <div className="bg-gray-400/10 dark:bg-zinc-900 rounded-2xl p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-zinc-800 dark:text-zinc-400">Fine (Chunks)</span>
                            {fineStatus && getFulltextIcon(fineStatus.fulltext_indexed_papers)}
                        </div>
                        <p className="text-[10px] text-zinc-800 dark:text-zinc-500 leading-tight mb-2">
                            Stage 2: Searches full-text chunks from selected papers on-demand
                        </p>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-800 dark:text-zinc-500">Chunks:</span>
                            <span className="text-white">{fineStatus?.chromadb_count ?? 0}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-800 dark:text-zinc-500">Indexed Papers:</span>
                            <span className={cn("font-semibold", fineStatus && getFulltextColor(fineStatus.fulltext_indexed_papers))}>
                                {fineStatus?.fulltext_indexed_papers ?? 0} / 80
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Messages */}
                <ScrollArea className="flex-1 h-full">
                    <div
                        ref={contentRef}
                        className={cn(
                            "max-w-4xl mx-auto space-y-6 p-4 pb-8",
                            needsTopPadding ? "pt-28" : "pt-4"
                        )}
                    >
                        {messages.length === 0 && (
                            <div className="text-center py-12 text-muted-foreground">
                                <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                <p className="text-lg font-medium">Start a conversation</p>
                                <p className="text-sm mt-2">Ask any question about the research papers in your dataset</p>
                            </div>
                        )}

                        {messages.map((msg, idx) => (
                            <div key={idx}>
                                {msg.role === "user" ? (
                                    /* User Message */
                                    <div className="flex gap-3 justify-end">
                                        <div className="bg-muted/30 text-neutral-900 dark:text-white rounded-2xl border px-4 py-3 max-w-[80%]">
                                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                        <div className="flex-shrink-0">
                                            <Image
                                                src="/assets/user_avatar_placeholder.png"
                                                alt="User"
                                                width={32}
                                                height={32}
                                                className="rounded-2xl"
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    /* Assistant Message - Full Width */
                                    <div className="w-full">
                                        <div className="flex gap-3 items-start mb-2">
                                            <div className="flex-shrink-0 w-8 h-8 rounded-2xl bg-zinc-800 dark:bg-zinc-800 flex items-center justify-center">
                                                <Bot className="w-4 h-4 text-zinc-400" />
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                                                {/* Referenced Papers */}
                                                {msg.papers && msg.papers.length > 0 && (
                                                    <div className="mt-4">
                                                        <p className="text-xs font-semibold mb-3 text-muted-foreground">
                                                            Referenced Papers ({msg.papers.length})
                                                        </p>
                                                        <div className="grid gap-2">
                                                            {msg.papers.map((paper, i) => (
                                                                <div
                                                                    key={i}
                                                                    className="text-xs bg-muted/50 border border-border rounded-2xl p-3 hover:bg-muted/80 transition-all duration-300 hover:scale-[1.02] hover:shadow-md opacity-0 animate-fadeInUp cursor-pointer"
                                                                    style={{
                                                                        animationDelay: `${i * 100}ms`,
                                                                        animationFillMode: 'forwards'
                                                                    }}
                                                                    onClick={() => setSelectedPaper({ arxiv_id: paper.arxiv_id, title: paper.title })}
                                                                >
                                                                    <div className="font-medium mb-1 line-clamp-1">{paper.title}</div>
                                                                    <div className="text-muted-foreground">
                                                                        {paper.arxiv_id} · Score: {paper.score.toFixed(4)}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Top Retrieved Chunks Carousel */}
                                                {msg.chunks && msg.chunks.length > 0 && (
                                                    <ChunksCarousel
                                                        chunks={msg.chunks}
                                                        animationDelay={(msg.papers?.length || 0) * 100}
                                                    />
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}

                        {loading && (
                            <div className="flex gap-3 items-start">
                                <div className="flex-shrink-0 w-8 h-8 rounded-2xl bg-zinc-800 dark:bg-zinc-800 flex items-center justify-center">
                                    <Bot className="w-4 h-4 text-zinc-400" />
                                </div>
                                <div className="flex-1">
                                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </ScrollArea>

                {/* Input */}
                <div className="p-4">
                    <div className="max-w-4xl mx-auto">
                        <div className="flex gap-2 items-center bg-muted/50 rounded-3xl p-2 border">
                            {/* Dropdown Selects */}
                            <div className="flex gap-2 items-center">
                                <Select value={topKPapers} onValueChange={setTopKPapers}>
                                    <SelectTrigger className="h-8 w-[100px] text-xs border-none bg-transparent">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="3">3 Papers</SelectItem>
                                        <SelectItem value="5">5 Papers</SelectItem>
                                        <SelectItem value="8">8 Papers</SelectItem>
                                        <SelectItem value="10">10 Papers</SelectItem>
                                    </SelectContent>
                                </Select>

                                <Select value={topKChunks} onValueChange={setTopKChunks}>
                                    <SelectTrigger className="h-8 w-[100px] text-xs border-none bg-transparent">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="5">5 Chunks</SelectItem>
                                        <SelectItem value="8">8 Chunks</SelectItem>
                                        <SelectItem value="10">10 Chunks</SelectItem>
                                        <SelectItem value="15">15 Chunks</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Divider */}
                            <div className="h-6 w-px bg-border" />

                            {/* Input */}
                            <Input
                                placeholder="Ask a question about research papers..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                disabled={loading}
                                className="flex-1 border-none shadow-none focus-visible:ring-0 bg-transparent"
                            />

                            {/* Send Button */}
                            <Button onClick={handleSend} disabled={loading || !input.trim()} size="sm">
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* PDF Viewer Dialog */}
            <PdfViewerDialog
                paper={selectedPaper}
                open={!!selectedPaper}
                onOpenChange={(open) => !open && setSelectedPaper(null)}
            />
        </div>
    );
}
