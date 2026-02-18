"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi, type Application, type ApplicationStage } from "@/lib/api";
import { format } from "date-fns";
import { clsx } from "clsx";

const STAGES: ApplicationStage[] = [
  "preparing", "submitted", "screening",
  "interview_1", "interview_2", "interview_3",
  "assessment", "offer", "negotiating", "accepted",
];

const TERMINAL_STAGES: ApplicationStage[] = ["rejected", "declined", "ghosted", "withdrawn"];

const STAGE_LABELS: Record<ApplicationStage, string> = {
  preparing: "Preparing",
  submitted: "Submitted",
  screening: "Screening",
  interview_1: "Interview 1",
  interview_2: "Interview 2",
  interview_3: "Interview 3",
  assessment: "Assessment",
  reference: "Reference Check",
  offer: "Offer",
  negotiating: "Negotiating",
  accepted: "Accepted",
  declined: "Declined",
  rejected: "Rejected",
  ghosted: "Ghosted",
};

const STAGE_COLORS: Partial<Record<ApplicationStage, string>> = {
  preparing: "bg-gray-100",
  submitted: "bg-blue-100",
  screening: "bg-blue-200",
  interview_1: "bg-purple-100",
  interview_2: "bg-purple-200",
  interview_3: "bg-purple-300",
  assessment: "bg-amber-100",
  offer: "bg-green-100",
  negotiating: "bg-green-200",
  accepted: "bg-green-300",
  rejected: "bg-red-100",
  declined: "bg-gray-100",
  ghosted: "bg-red-50",
};

export default function TrackerPage() {
  const qc = useQueryClient();

  const { data: pipelineStats } = useQuery({
    queryKey: ["pipeline-stats"],
    queryFn: applicationsApi.pipeline,
  });

  const { data: activeApps, isLoading } = useQuery({
    queryKey: ["applications", "active"],
    queryFn: () => applicationsApi.list({ active_only: true, page_size: 50 }),
  });

  const { data: closedApps } = useQuery({
    queryKey: ["applications", "closed"],
    queryFn: () => applicationsApi.list({ page_size: 20 }),
  });

  const updateApp = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Application> }) =>
      applicationsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["pipeline-stats"] });
    },
  });

  // Group active apps by stage for kanban-ish view
  const byStage: Record<string, Application[]> = {};
  activeApps?.items.forEach((app) => {
    if (!byStage[app.stage]) byStage[app.stage] = [];
    byStage[app.stage].push(app);
  });

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Application Tracker</h1>
        <p className="text-sm text-gray-500">
          {activeApps?.total ?? 0} active · {closedApps?.total ?? 0} total
        </p>
      </div>

      {/* Pipeline funnel */}
      {pipelineStats && (
        <div className="card">
          <h2 className="font-semibold text-gray-700 mb-3 text-sm">Pipeline Funnel</h2>
          <div className="flex gap-1 overflow-x-auto pb-2">
            {STAGES.map((stage) => {
              const count = pipelineStats[stage] || 0;
              return (
                <div key={stage} className="flex flex-col items-center min-w-[70px]">
                  <div
                    className={clsx(
                      "w-full rounded-t-md text-center text-sm font-bold text-gray-800 py-1",
                      STAGE_COLORS[stage] || "bg-gray-100"
                    )}
                    style={{ minHeight: `${Math.max(count * 8 + 32, 32)}px` }}
                  >
                    {count}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 text-center leading-tight">
                    {STAGE_LABELS[stage]}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Active applications list */}
      <div>
        <h2 className="font-semibold text-gray-700 mb-3">Active Applications</h2>
        {isLoading ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : activeApps?.items.length === 0 ? (
          <div className="card text-center py-10">
            <p className="text-gray-400 text-sm">No active applications yet.</p>
            <p className="text-gray-400 text-xs mt-1">
              Shortlist a job and create an application to start tracking.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeApps?.items.map((app) => (
              <div key={app.id} className="card hover:border-brand-200 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-gray-900">{app.job_title}</p>
                    <p className="text-sm text-gray-600">{app.company}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span
                        className={clsx(
                          "badge",
                          STAGE_COLORS[app.stage]
                            ? "text-gray-700"
                            : "badge-gray"
                        )}
                        style={{
                          background: STAGE_COLORS[app.stage]?.replace("bg-", "") || undefined,
                        }}
                      >
                        {STAGE_LABELS[app.stage]}
                      </span>
                      {app.referral_used && <span className="badge badge-green">Referral</span>}
                      {app.recruiter_name && (
                        <span className="text-xs text-gray-400">
                          Recruiter: {app.recruiter_name}
                          {app.recruiter_agency ? ` (${app.recruiter_agency})` : ""}
                        </span>
                      )}
                    </div>
                    {app.submitted_date && (
                      <p className="text-xs text-gray-400 mt-1">
                        Submitted: {format(new Date(app.submitted_date), "d MMM yyyy")}
                      </p>
                    )}
                    {app.next_action_date && (
                      <p className="text-xs text-amber-600 mt-0.5">
                        Next action: {format(new Date(app.next_action_date), "d MMM yyyy")}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col gap-2 items-end flex-shrink-0">
                    <select
                      value={app.stage}
                      onChange={(e) =>
                        updateApp.mutate({ id: app.id, data: { stage: e.target.value as ApplicationStage } })
                      }
                      className="text-xs border border-gray-200 rounded-md px-2 py-1 outline-none"
                    >
                      {([...STAGES, ...TERMINAL_STAGES] as ApplicationStage[]).map((s) => (
                        <option key={s} value={s}>{STAGE_LABELS[s]}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {app.notes && (
                  <p className="text-xs text-gray-500 mt-2 pt-2 border-t border-gray-100 italic">
                    {app.notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
