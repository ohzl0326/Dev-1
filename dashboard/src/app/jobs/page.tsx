"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobsApi, type Job, type JobStatus } from "@/lib/api";
import { ExternalLink, Star, RefreshCw, Search, CheckCircle, AlertCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { clsx } from "clsx";

const STATUS_COLORS: Record<JobStatus, string> = {
  new: "badge-blue",
  reviewing: "badge-purple",
  shortlisted: "badge-amber",
  applied: "badge-green",
  interviewing: "badge-green",
  offer: "badge-green",
  accepted: "badge-green",
  rejected: "badge-red",
  withdrawn: "badge-gray",
  closed: "badge-gray",
};

const STATUS_OPTIONS: JobStatus[] = [
  "new", "reviewing", "shortlisted", "applied", "interviewing",
  "offer", "accepted", "rejected", "withdrawn",
];

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<JobStatus | "">("");
  const [locationFilter, setLocationFilter] = useState<"" | "Singapore" | "Sydney">("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [scrapeStatus, setScrapeStatus] = useState<"idle" | "queued" | "error">("idle");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["jobs", statusFilter, locationFilter, search, page],
    queryFn: () =>
      jobsApi.list({
        status: statusFilter || undefined,
        location: locationFilter || undefined,
        search: search || undefined,
        page,
        page_size: 20,
      }),
  });

  const updateJob = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Job> }) =>
      jobsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const triggerScrape = useMutation({
    mutationFn: jobsApi.triggerScrape,
    onSuccess: () => {
      setScrapeStatus("queued");
      // Refresh job list after a delay to pick up results as they land
      setTimeout(() => qc.invalidateQueries({ queryKey: ["jobs"] }), 15000);
      setTimeout(() => qc.invalidateQueries({ queryKey: ["jobs"] }), 45000);
      setTimeout(() => setScrapeStatus("idle"), 8000);
    },
    onError: () => {
      setScrapeStatus("error");
      setTimeout(() => setScrapeStatus("idle"), 6000);
    },
  });

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="text-sm text-gray-500">{data?.total ?? 0} total discovered</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => triggerScrape.mutate()}
          disabled={triggerScrape.isPending || scrapeStatus === "queued"}
        >
          <RefreshCw className={clsx("w-4 h-4", triggerScrape.isPending && "animate-spin")} />
          {triggerScrape.isPending ? "Queueing…" : scrapeStatus === "queued" ? "Scraping…" : "Scrape Now"}
        </button>
      </div>

      {scrapeStatus === "queued" && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2.5">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          Scrape queued — results will appear automatically. This usually takes 1–3 minutes.
        </div>
      )}
      {scrapeStatus === "error" && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Failed to queue scrape — check that the API and Celery worker are running.
        </div>
      )}

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search title, company..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-brand-200"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as JobStatus | ""); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-200"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>

        <select
          value={locationFilter}
          onChange={(e) => { setLocationFilter(e.target.value as any); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-200"
        >
          <option value="">All locations</option>
          <option value="Singapore">Singapore</option>
          <option value="Sydney">Sydney</option>
        </select>
      </div>

      {/* Job list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items.map((job) => (
            <div key={job.id} className="card flex gap-4 hover:border-brand-200 transition-colors">
              {/* Score bar */}
              <div className="w-1 flex-shrink-0 rounded-full self-stretch"
                style={{
                  background: job.relevance_score >= 0.75
                    ? "#22c55e"
                    : job.relevance_score >= 0.5
                    ? "#f59e0b"
                    : "#e5e7eb",
                }}
              />

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-base font-semibold text-gray-900 hover:text-brand-600 flex items-center gap-1"
                    >
                      {job.title}
                      <ExternalLink className="w-3.5 h-3.5 opacity-50 flex-shrink-0" />
                    </a>
                    <p className="text-sm text-gray-600">
                      {job.company} · <span className="text-gray-500">{job.location}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={clsx("badge", STATUS_COLORS[job.status])}>{job.status}</span>
                    <button
                      onClick={() => updateJob.mutate({ id: job.id, data: { is_starred: !job.is_starred } })}
                      className="text-gray-300 hover:text-amber-400 transition-colors"
                    >
                      <Star className={clsx("w-4 h-4", job.is_starred && "fill-amber-400 text-amber-400")} />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 mt-2">
                  <span className="text-xs text-gray-400">
                    Score: <span className="font-medium text-gray-700">{Math.round(job.relevance_score * 100)}%</span>
                  </span>
                  {job.market_type && (
                    <span className="badge badge-purple">{job.market_type}</span>
                  )}
                  {job.salary_min && (
                    <span className="text-xs text-gray-400">
                      {job.salary_currency} {job.salary_min.toLocaleString()}
                      {job.salary_max ? `–${job.salary_max.toLocaleString()}` : "+"}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 capitalize">{job.source}</span>
                  {job.posted_date && (
                    <span className="text-xs text-gray-400">
                      {formatDistanceToNow(new Date(job.posted_date), { addSuffix: true })}
                    </span>
                  )}
                </div>

                {/* Status changer */}
                <div className="mt-3 flex gap-2">
                  <select
                    value={job.status}
                    onChange={(e) =>
                      updateJob.mutate({ id: job.id, data: { status: e.target.value as JobStatus } })
                    }
                    className="text-xs border border-gray-200 rounded-md px-2 py-1 outline-none focus:ring-1 focus:ring-brand-200"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-gray-500">
            Page {page} of {Math.ceil(data.total / 20)}
          </p>
          <div className="flex gap-2">
            <button
              className="btn-secondary"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              className="btn-secondary"
              disabled={page >= Math.ceil(data.total / 20)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
