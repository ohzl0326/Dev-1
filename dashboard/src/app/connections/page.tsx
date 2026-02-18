"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi, type Connection, type OutreachStatus } from "@/lib/api";
import { Linkedin, Star, Plus, Users, AlertTriangle } from "lucide-react";
import { formatDistanceToNow, format, isPast } from "date-fns";
import { clsx } from "clsx";

const STATUS_COLORS: Record<OutreachStatus, string> = {
  new: "badge-gray",
  pending: "badge-blue",
  outreach_sent: "badge-blue",
  responded: "badge-green",
  call_scheduled: "badge-amber",
  met: "badge-green",
  nurturing: "badge-purple",
  referred: "badge-green",
  stale: "badge-red",
  inactive: "badge-gray",
};

const WARMTH_COLORS: Record<string, string> = {
  cold: "bg-blue-100 text-blue-600",
  warm: "bg-amber-100 text-amber-600",
  hot: "bg-red-100 text-red-600",
};

export default function ConnectionsPage() {
  const [statusFilter, setStatusFilter] = useState<OutreachStatus | "">("");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [search, setSearch] = useState("");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["connections", statusFilter, overdueOnly, search],
    queryFn: () =>
      connectionsApi.list({
        status: statusFilter || undefined,
        overdue_only: overdueOnly,
        search: search || undefined,
        page_size: 50,
      }),
  });

  const updateConn = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Connection> }) =>
      connectionsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const overdue = data?.items.filter(
    (c) => c.next_followup_date && isPast(new Date(c.next_followup_date))
  );

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Connections</h1>
          <p className="text-sm text-gray-500">{data?.total ?? 0} contacts</p>
        </div>
        <a href="/connections/new" className="btn-primary">
          <Plus className="w-4 h-4" />
          Add Connection
        </a>
      </div>

      {/* Overdue alert */}
      {overdue && overdue.length > 0 && (
        <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
          <p className="text-sm text-amber-800">
            <span className="font-semibold">{overdue.length} follow-up{overdue.length > 1 ? "s" : ""} overdue:</span>{" "}
            {overdue.slice(0, 3).map((c) => c.name).join(", ")}
            {overdue.length > 3 ? ` +${overdue.length - 3} more` : ""}
          </p>
          <button
            className="ml-auto text-xs text-amber-700 hover:text-amber-900 underline"
            onClick={() => setOverdueOnly(true)}
          >
            Show overdue only
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search name, company..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-48 text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-200"
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as OutreachStatus | "")}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none"
        >
          <option value="">All statuses</option>
          {(["new", "pending", "outreach_sent", "responded", "call_scheduled", "met", "nurturing", "stale"] as OutreachStatus[]).map(
            (s) => <option key={s} value={s}>{s.replace("_", " ")}</option>
          )}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(e) => setOverdueOnly(e.target.checked)}
            className="rounded"
          />
          Overdue only
        </label>
      </div>

      {/* Connections grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {data?.items.map((conn) => {
          const isOverdue = conn.next_followup_date && isPast(new Date(conn.next_followup_date));
          return (
            <div
              key={conn.id}
              className={clsx(
                "card hover:border-brand-200 transition-colors",
                isOverdue && "border-amber-200 bg-amber-50"
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{conn.name}</p>
                    {conn.warmth && (
                      <span className={clsx("badge text-xs", WARMTH_COLORS[conn.warmth] || "badge-gray")}>
                        {conn.warmth}
                      </span>
                    )}
                    {conn.is_hiring_manager && <span className="badge badge-purple">HM</span>}
                    {conn.is_recruiter && <span className="badge badge-blue">Recruiter</span>}
                  </div>
                  <p className="text-sm text-gray-600">
                    {conn.current_title}
                    {conn.current_company && ` · ${conn.current_company}`}
                  </p>
                  {conn.location && (
                    <p className="text-xs text-gray-400">{conn.location}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {conn.linkedin_url && (
                    <a href={conn.linkedin_url} target="_blank" rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-600">
                      <Linkedin className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={() => updateConn.mutate({ id: conn.id, data: { is_starred: !conn.is_starred } })}
                    className="text-gray-300 hover:text-amber-400"
                  >
                    <Star className={clsx("w-4 h-4", conn.is_starred && "fill-amber-400 text-amber-400")} />
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 mt-3">
                <span className={clsx("badge", STATUS_COLORS[conn.status])}>
                  {conn.status.replace("_", " ")}
                </span>
                {conn.how_met && (
                  <span className="text-xs text-gray-400">Met: {conn.how_met}</span>
                )}
              </div>

              {conn.next_followup_date && (
                <p className={clsx("text-xs mt-2", isOverdue ? "text-amber-600 font-medium" : "text-gray-400")}>
                  {isOverdue ? "⚠ Overdue — " : "Follow up: "}
                  {formatDistanceToNow(new Date(conn.next_followup_date), { addSuffix: true })}
                </p>
              )}

              {conn.follow_up_notes && (
                <p className="text-xs text-gray-500 mt-1 italic">{conn.follow_up_notes}</p>
              )}

              {/* Quick status update */}
              <div className="mt-3 pt-3 border-t border-gray-100">
                <select
                  value={conn.status}
                  onChange={(e) =>
                    updateConn.mutate({ id: conn.id, data: { status: e.target.value as OutreachStatus } })
                  }
                  className="text-xs border border-gray-200 rounded-md px-2 py-1 outline-none w-full"
                >
                  {(["new", "pending", "outreach_sent", "responded", "call_scheduled", "met", "nurturing", "referred", "stale", "inactive"] as OutreachStatus[]).map(
                    (s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                  )}
                </select>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
