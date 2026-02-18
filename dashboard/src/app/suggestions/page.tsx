"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suggestionsApi, type Suggestion, type SuggestionType } from "@/lib/api";
import { Sparkles, RefreshCw, CheckCircle, XCircle, Briefcase, Calendar, Users, Zap } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { clsx } from "clsx";

const TYPE_ICONS: Record<SuggestionType, React.ReactNode> = {
  job: <Briefcase className="w-4 h-4" />,
  event: <Calendar className="w-4 h-4" />,
  connection: <Users className="w-4 h-4" />,
  action: <Zap className="w-4 h-4" />,
};

const TYPE_COLORS: Record<SuggestionType, string> = {
  job: "bg-blue-50 border-blue-200",
  event: "bg-purple-50 border-purple-200",
  connection: "bg-green-50 border-green-200",
  action: "bg-amber-50 border-amber-200",
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "badge-red",
  medium: "badge-amber",
  low: "badge-gray",
};

export default function SuggestionsPage() {
  const qc = useQueryClient();

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["suggestions", "all"],
    queryFn: () => suggestionsApi.list({ limit: 20 }),
  });

  const feedback = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      suggestionsApi.feedback(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });

  const generate = useMutation({
    mutationFn: suggestionsApi.generate,
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ["suggestions"] }), 2000),
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Suggestions</h1>
          <p className="text-sm text-gray-500">
            Prioritised recommendations based on your Q3 2026 goal
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          <Sparkles className={clsx("w-4 h-4", generate.isPending && "animate-pulse")} />
          {generate.isPending ? "Generating..." : "Generate Now"}
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
        </div>
      ) : !suggestions?.length ? (
        <div className="card text-center py-12">
          <Sparkles className="w-8 h-8 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No suggestions yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Click "Generate Now" to get AI-powered recommendations, or wait for the daily run.
          </p>
          <p className="text-gray-400 text-xs mt-2">Requires OPENAI_API_KEY to be configured.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {suggestions.map((s) => (
            <div
              key={s.id}
              className={clsx(
                "rounded-xl border p-5 transition-opacity",
                TYPE_COLORS[s.suggestion_type],
                s.is_acted_on && "opacity-60"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <div className="mt-0.5 text-gray-500 flex-shrink-0">
                    {TYPE_ICONS[s.suggestion_type]}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-gray-900">{s.title}</p>
                      {s.priority && (
                        <span className={clsx("badge", PRIORITY_BADGE[s.priority])}>{s.priority}</span>
                      )}
                      {s.is_acted_on && (
                        <span className="badge badge-green">✓ Done</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{s.rationale}</p>
                    {s.action_text && (
                      <p className="text-sm font-medium text-gray-800 mt-2 flex items-center gap-1">
                        <Zap className="w-3 h-3 text-amber-500 flex-shrink-0" />
                        {s.action_text}
                      </p>
                    )}
                    <div className="flex items-center gap-4 mt-3">
                      <span className="text-xs text-gray-400">
                        Confidence: {Math.round(s.confidence_score * 100)}%
                      </span>
                      <span className="text-xs text-gray-400">
                        Goal alignment: {Math.round(s.goal_alignment_score * 100)}%
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(s.generated_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 flex-shrink-0">
                  {!s.is_acted_on && (
                    <button
                      onClick={() => feedback.mutate({ id: s.id, data: { is_acted_on: true } })}
                      title="Mark as done"
                      className="text-gray-400 hover:text-green-500 transition-colors"
                    >
                      <CheckCircle className="w-5 h-5" />
                    </button>
                  )}
                  {!s.is_dismissed && (
                    <button
                      onClick={() => feedback.mutate({ id: s.id, data: { is_dismissed: true } })}
                      title="Dismiss"
                      className="text-gray-400 hover:text-red-400 transition-colors"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
