"use client";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, jobsApi, eventsApi, suggestionsApi } from "@/lib/api";
import {
  Briefcase,
  Calendar,
  Users,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { clsx } from "clsx";

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 1000 * 60 * 5, // refresh every 5 min
  });

  const { data: topJobs } = useQuery({
    queryKey: ["jobs", "top"],
    queryFn: () => jobsApi.list({ status: "new", page_size: 5, sort_by: "relevance_score" }),
  });

  const { data: upcomingEvents } = useQuery({
    queryKey: ["events", "upcoming"],
    queryFn: () => eventsApi.list({ upcoming_only: true, page_size: 5 }),
  });

  const { data: suggestions } = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => suggestionsApi.list({ limit: 5 }),
  });

  if (isLoading || !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    );
  }

  const { goal, jobs, events, connections } = summary;

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Institutional RM roles · Singapore & Sydney · Deadline:{" "}
          <span className="font-medium text-brand-600">{format(new Date(goal.deadline), "d MMM yyyy")}</span>
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="New Jobs"
          value={jobs.new_unreviewed}
          sub={`${jobs.total_discovered} total discovered`}
          icon={<Briefcase className="w-5 h-5 text-blue-500" />}
          color="blue"
        />
        <KpiCard
          label="Active Applications"
          value={jobs.active_applications}
          sub="in pipeline"
          icon={<Briefcase className="w-5 h-5 text-green-500" />}
          color="green"
          alert={jobs.active_applications === 0}
        />
        <KpiCard
          label="Upcoming Events"
          value={events.upcoming}
          sub={`${events.registered} registered`}
          icon={<Calendar className="w-5 h-5 text-purple-500" />}
          color="purple"
        />
        <KpiCard
          label="Overdue Follow-ups"
          value={connections.overdue_followups}
          sub={`${connections.total} total connections`}
          icon={<Users className="w-5 h-5 text-amber-500" />}
          color="amber"
          alert={connections.overdue_followups > 0}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top new jobs */}
        <div className="lg:col-span-1 card">
          <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-blue-500" />
            Top New Jobs
          </h2>
          {topJobs?.items.length ? (
            <ul className="space-y-3">
              {topJobs.items.map((job) => (
                <li key={job.id} className="flex flex-col gap-0.5">
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-gray-900 hover:text-brand-600 flex items-center gap-1"
                  >
                    {job.title}
                    <ExternalLink className="w-3 h-3 opacity-50" />
                  </a>
                  <span className="text-xs text-gray-500">
                    {job.company} · {job.location}
                  </span>
                  <ScoreBar score={job.relevance_score} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No new jobs. Run a scrape to discover roles.</p>
          )}
        </div>

        {/* Upcoming events */}
        <div className="lg:col-span-1 card">
          <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-purple-500" />
            Upcoming Events
          </h2>
          {upcomingEvents?.items.length ? (
            <ul className="space-y-3">
              {upcomingEvents.items.map((event) => (
                <li key={event.id}>
                  <a
                    href={event.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-gray-900 hover:text-brand-600 flex items-center gap-1"
                  >
                    {event.name}
                    <ExternalLink className="w-3 h-3 opacity-50" />
                  </a>
                  <p className="text-xs text-gray-500">
                    {event.city} ·{" "}
                    {event.event_date
                      ? format(new Date(event.event_date), "d MMM yyyy")
                      : "Date TBC"}
                  </p>
                  <EventStatusBadge status={event.status} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No upcoming events found yet.</p>
          )}
        </div>

        {/* AI Suggestions */}
        <div className="lg:col-span-1 card">
          <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            AI Suggestions
          </h2>
          {suggestions?.length ? (
            <ul className="space-y-3">
              {suggestions.map((s) => (
                <li key={s.id} className="border-l-2 border-brand-200 pl-3">
                  <p className="text-sm font-medium text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.action_text}</p>
                  <span
                    className={clsx("badge mt-1", {
                      "badge-red": s.priority === "high",
                      "badge-amber": s.priority === "medium",
                      "badge-gray": s.priority === "low",
                    })}
                  >
                    {s.priority}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No suggestions yet. They generate daily.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label, value, sub, icon, color, alert = false,
}: {
  label: string;
  value: number;
  sub: string;
  icon: React.ReactNode;
  color: string;
  alert?: boolean;
}) {
  return (
    <div className={clsx("card flex flex-col gap-2", alert && "border-amber-200 bg-amber-50")}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 font-medium">{label}</span>
        {alert && <AlertTriangle className="w-4 h-4 text-amber-500" />}
        {!alert && icon}
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full", {
            "bg-green-500": score >= 0.75,
            "bg-amber-400": score >= 0.5 && score < 0.75,
            "bg-red-400": score < 0.5,
          })}
          style={{ width: `${score * 100}%` }}
        />
      </div>
      <span className="text-xs text-gray-400">{Math.round(score * 100)}%</span>
    </div>
  );
}

function EventStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    discovered: "badge-gray",
    interested: "badge-blue",
    registered: "badge-green",
    attended: "badge-purple",
    missed: "badge-red",
    skipped: "badge-gray",
  };
  return <span className={clsx("badge mt-1", map[status] || "badge-gray")}>{status}</span>;
}
