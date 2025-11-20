"use client";

import { useState, useEffect } from "react";
import { ModeToggle } from "./ui/mode-toggle";
import { Kbd } from "./ui/kbd";
import { SearchDialog } from "./search-dialog";
import { PdfViewerDialog } from "./pdf-viewer-dialog";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search } from "lucide-react";

export default function Navbar() {
    const pathname = usePathname();
    const [searchOpen, setSearchOpen] = useState(false);
    const [selectedPaper, setSelectedPaper] = useState<{ arxiv_id: string; title: string } | null>(null);

    const navItems = [
        { label: "Datasets", href: "/dataset" },
        { label: "Chat", href: "/chat" },
        // { label: "Recommendations", href: "/recommendation" },
        // { label: "Users", href: "/user" },
    ];

    // Listen for Command+K
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setSearchOpen(!searchOpen);
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    return (
        <>
            <div className="sticky top-0 z-50 h-12 w-full border-b flex items-center justify-between px-12 bg-white dark:bg-black">
                <div className="flex space-x-3">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`cursor-pointer h-full px-3 py-2 rounded-2xl text-sm transition-all duration-300 hover:bg-zinc-200/60 dark:hover:bg-zinc-700/20 ${isActive
                                    ? "font-semibold text-zinc-900 dark:text-zinc-100"
                                    : "text-zinc-600 dark:text-zinc-300"
                                    }`}
                            >
                                {item.label}
                            </Link>
                        );
                    })}
                </div>
                <div className="flex items-center justify-center space-x-3">
                    {/* Search Bar */}
                    <div
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-background hover:bg-accent/50 transition-colors cursor-pointer min-w-[280px]"
                        onClick={() => setSearchOpen(true)}
                    >
                        <Search className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground flex-1">Search papers...</span>
                        <Kbd>
                            <span className="text-xs">⌘</span>K
                        </Kbd>
                    </div>

                    <ModeToggle />
                    <div className="flex items-center justify-between rounded-2xl pl-3 py-0.5 pr-0.5 space-x-3 hover:bg-zinc-200/60 dark:hover:bg-zinc-700/20 cursor-pointer transition-all duration-300">
                        <span className="text-sm font-medium">Username</span>
                        <div className="h-full w-full rounded-lg">
                            <Image src="/assets/user_avatar_placeholder.png" alt="User Avatar" width={32} height={32} className="rounded-lg" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Search Dialog */}
            <SearchDialog
                open={searchOpen}
                onOpenChange={setSearchOpen}
                onPaperClick={(paper) => {
                    setSelectedPaper(paper);
                }}
            />

            {/* PDF Viewer Dialog */}
            <PdfViewerDialog
                paper={selectedPaper}
                open={!!selectedPaper}
                onOpenChange={(open) => !open && setSelectedPaper(null)}
            />
        </>
    );
}
