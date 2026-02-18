"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Calendar,
  Users,
  ClipboardList,
  Sparkles,
  Target,
} from "lucide-react";
import { clsx } from "clsx";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/events", label: "Events", icon: Calendar },
  { href: "/connections", label: "Connections", icon: Users },
  { href: "/tracker", label: "Applications", icon: ClipboardList },
  { href: "/suggestions", label: "AI Suggestions", icon: Sparkles },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Target className="w-6 h-6 text-brand-500" />
          <div>
            <p className="text-sm font-semibold text-gray-900">Career Tracker</p>
            <p className="text-xs text-gray-400">SG · Sydney · Q3 2026</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Goal countdown */}
      <GoalCountdown />
    </aside>
  );
}

function GoalCountdown() {
  const deadline = new Date("2026-09-30");
  const today = new Date();
  const daysLeft = Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  const pct = Math.max(0, Math.min(100, ((365 - daysLeft) / 365) * 100));

  return (
    <div className="p-4 border-t border-gray-100">
      <p className="text-xs text-gray-500 mb-1">Goal deadline</p>
      <p className="text-sm font-semibold text-gray-800">{daysLeft} days left</p>
      <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">Q3 2026 · Asset Management</p>
    </div>
  );
}
