"use client";

import { ModeToggle } from "./ui/mode-toggle";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
    const pathname = usePathname();

    const navItems = [
        { label: "Datasets", href: "/dataset" },
        { label: "Chat", href: "/chat" },
        { label: "Recommendations", href: "/recommendation" },
        { label: "Users", href: "/user" },
    ];

    return (
        <div className="h-12 w-full border-b flex items-center justify-between px-12">
            <div className="flex space-x-3">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`cursor-pointer h-full px-3 py-2 rounded-2xl text-sm transition-all duration-300 hover:bg-zinc-200/60 dark:hover:bg-zinc-700/20 ${
                                isActive
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
                <ModeToggle />
                <div className="flex items-center justify-between rounded-2xl pl-3 py-0.5 pr-0.5 space-x-3 hover:bg-zinc-200/60 dark:hover:bg-zinc-700/20 cursor-pointer transition-all duration-300">
                    <span className="text-sm font-medium">Username</span>
                    <div className="h-full w-full rounded-lg">
                        <Image src="/assets/user_avatar_placeholder.png" alt="User Avatar" width={32} height={32} className="rounded-lg" />
                    </div>
                </div>
            </div>
        </div>
    );
}
