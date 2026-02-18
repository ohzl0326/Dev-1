"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { eventsApi, type Event, type EventStatus } from "@/lib/api";
import { ExternalLink, Star, RefreshCw, MapPin, Calendar } from "lucide-react";
import { format, formatDistanceToNow, isPast } from "date-fns";
import { clsx } from "clsx";

const STATUS_COLORS: Record<EventStatus, string> = {
  discovered: "badge-gray",
  interested: "badge-blue",
  registered: "badge-green",
  attended: "badge-purple",
  missed: "badge-red",
  skipped: "badge-gray",
};

export default function EventsPage() {
  const [cityFilter, setCityFilter] = useState<"" | "Singapore" | "Sydney" | "Online">("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<EventStatus | "">("");
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["events", cityFilter, typeFilter, statusFilter, page],
    queryFn: () =>
      eventsApi.list({
        city: cityFilter || undefined,
        event_type: typeFilter || undefined,
        status: statusFilter || undefined,
        upcoming_only: statusFilter === "" || statusFilter === "discovered",
        page,
        page_size: 20,
      }),
  });

  const updateEvent = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Event> }) =>
      eventsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });

  const triggerScrape = useMutation({ mutationFn: eventsApi.triggerScrape });

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Events</h1>
          <p className="text-sm text-gray-500">{data?.total ?? 0} events</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => triggerScrape.mutate()}
          disabled={triggerScrape.isPending}
        >
          <RefreshCw className={clsx("w-4 h-4", triggerScrape.isPending && "animate-spin")} />
          Scrape Now
        </button>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3">
        <select
          value={cityFilter}
          onChange={(e) => { setCityFilter(e.target.value as any); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none"
        >
          <option value="">All cities</option>
          <option value="Singapore">Singapore</option>
          <option value="Sydney">Sydney</option>
          <option value="Online">Online</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none"
        >
          <option value="">All types</option>
          {["networking", "panel", "conference", "roundtable", "forum", "webinar", "workshop"].map(
            (t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          )}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as EventStatus | ""); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none"
        >
          <option value="">All statuses</option>
          {(["discovered", "interested", "registered", "attended", "missed"] as EventStatus[]).map(
            (s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          )}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items.map((event) => (
            <div key={event.id} className="card hover:border-brand-200 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={event.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-base font-semibold text-gray-900 hover:text-brand-600 flex items-center gap-1"
                  >
                    {event.name}
                    <ExternalLink className="w-3.5 h-3.5 opacity-50 flex-shrink-0" />
                  </a>
                  {event.organiser && (
                    <p className="text-sm text-gray-500">{event.organiser}</p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 mt-2">
                    <span className="flex items-center gap-1 text-xs text-gray-500">
                      <MapPin className="w-3 h-3" />
                      {event.city || "Unknown"}{event.is_online ? " (Online)" : ""}
                    </span>
                    {event.event_date && (
                      <span className="flex items-center gap-1 text-xs text-gray-500">
                        <Calendar className="w-3 h-3" />
                        {format(new Date(event.event_date), "d MMM yyyy")}
                        {isPast(new Date(event.event_date)) && (
                          <span className="text-red-400">(past)</span>
                        )}
                      </span>
                    )}
                    {event.event_type && (
                      <span className="badge badge-blue">{event.event_type}</span>
                    )}
                    {event.is_free === true && <span className="badge badge-green">Free</span>}
                    {event.is_free === false && event.cost && (
                      <span className="text-xs text-gray-400">{event.cost}</span>
                    )}
                    <span className="text-xs text-gray-400">
                      Score: {Math.round(event.relevance_score * 100)}%
                    </span>
                  </div>

                  {event.themes && event.themes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {event.themes.slice(0, 4).map((t) => (
                        <span key={t} className="badge badge-gray text-xs">{t}</span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <span className={clsx("badge", STATUS_COLORS[event.status])}>{event.status}</span>
                    <button
                      onClick={() => updateEvent.mutate({ id: event.id, data: { is_starred: !event.is_starred } })}
                      className="text-gray-300 hover:text-amber-400 transition-colors"
                    >
                      <Star className={clsx("w-4 h-4", event.is_starred && "fill-amber-400 text-amber-400")} />
                    </button>
                  </div>
                  <select
                    value={event.status}
                    onChange={(e) =>
                      updateEvent.mutate({ id: event.id, data: { status: e.target.value as EventStatus } })
                    }
                    className="text-xs border border-gray-200 rounded-md px-2 py-1 outline-none"
                  >
                    {(["discovered", "interested", "registered", "attended", "missed", "skipped"] as EventStatus[]).map(
                      (s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    )}
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
