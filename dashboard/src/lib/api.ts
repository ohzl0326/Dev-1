import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { "Content-Type": "application/json" },
});

// --- Types ---

export type JobStatus =
  | "new" | "reviewing" | "shortlisted" | "applied"
  | "interviewing" | "offer" | "accepted" | "rejected" | "withdrawn" | "closed";

export type EventStatus =
  | "discovered" | "interested" | "registered" | "attended" | "missed" | "skipped";

export type OutreachStatus =
  | "new" | "pending" | "outreach_sent" | "responded"
  | "call_scheduled" | "met" | "nurturing" | "referred" | "stale" | "inactive";

export type ApplicationStage =
  | "preparing" | "submitted" | "screening" | "interview_1" | "interview_2"
  | "interview_3" | "assessment" | "reference" | "offer" | "negotiating"
  | "accepted" | "declined" | "rejected" | "ghosted" | "withdrawn";

export type SuggestionType = "job" | "event" | "connection" | "action";

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
  description?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  market_type?: string;
  is_asset_management: boolean;
  relevance_score: number;
  score_breakdown?: Record<string, number>;
  status: JobStatus;
  notes?: string;
  is_starred: boolean;
  posted_date?: string;
  discovered_at: string;
}

export interface Event {
  id: number;
  name: string;
  organiser?: string;
  url: string;
  source: string;
  event_type?: string;
  themes?: string[];
  location?: string;
  is_online: boolean;
  city?: string;
  is_free?: boolean;
  cost?: string;
  description?: string;
  relevance_score: number;
  networking_value?: number;
  status: EventStatus;
  notes?: string;
  is_starred: boolean;
  event_date?: string;
  registration_deadline?: string;
}

export interface Connection {
  id: number;
  name: string;
  current_title?: string;
  current_company?: string;
  location?: string;
  linkedin_url?: string;
  email?: string;
  how_met?: string;
  industry?: string;
  seniority?: string;
  is_hiring_manager: boolean;
  is_recruiter: boolean;
  relevance_notes?: string;
  warmth?: string;
  status: OutreachStatus;
  outreach_history?: Array<{
    date: string;
    channel: string;
    summary: string;
    outcome?: string;
  }>;
  last_contact_date?: string;
  next_followup_date?: string;
  follow_up_notes?: string;
  notes?: string;
  is_starred: boolean;
  added_at: string;
}

export interface Application {
  id: number;
  job_id: number;
  job_title: string;
  company: string;
  stage: ApplicationStage;
  stage_history?: Array<{ stage: string; date: string }>;
  submitted_date?: string;
  last_activity_date?: string;
  next_action_date?: string;
  recruiter_name?: string;
  recruiter_agency?: string;
  hiring_manager_name?: string;
  cv_version?: string;
  cover_letter_used: boolean;
  referral_used: boolean;
  offer_salary?: number;
  offer_currency?: string;
  offer_details?: string;
  notes?: string;
  interview_notes?: any[];
  lessons_learned?: string;
  is_starred: boolean;
  created_at: string;
  updated_at: string;
}

export interface Suggestion {
  id: number;
  suggestion_type: SuggestionType;
  title: string;
  rationale: string;
  action_text?: string;
  priority?: string;
  linked_job_id?: number;
  linked_event_id?: number;
  linked_connection_id?: number;
  external_url?: string;
  confidence_score: number;
  goal_alignment_score: number;
  is_dismissed: boolean;
  is_acted_on: boolean;
  generated_at: string;
}

export interface DashboardSummary {
  goal: {
    deadline: string;
    days_remaining: number;
    target_locations: string[];
    target_roles: string[];
  };
  jobs: {
    total_discovered: number;
    new_unreviewed: number;
    active_applications: number;
  };
  events: {
    upcoming: number;
    registered: number;
  };
  connections: {
    total: number;
    overdue_followups: number;
  };
  suggestions: {
    active: number;
  };
}

// --- API helpers ---

export const dashboardApi = {
  getSummary: () => api.get<DashboardSummary>("/dashboard").then((r) => r.data),
};

export const jobsApi = {
  list: (params?: Record<string, any>) =>
    api.get<{ total: number; items: Job[] }>("/jobs", { params }).then((r) => r.data),
  get: (id: number) => api.get<Job>(`/jobs/${id}`).then((r) => r.data),
  update: (id: number, data: Partial<Job>) =>
    api.patch<Job>(`/jobs/${id}`, data).then((r) => r.data),
  stats: () => api.get("/jobs/stats/summary").then((r) => r.data),
  triggerScrape: () => api.post("/scrape/jobs").then((r) => r.data),
};

export const eventsApi = {
  list: (params?: Record<string, any>) =>
    api.get<{ total: number; items: Event[] }>("/events", { params }).then((r) => r.data),
  get: (id: number) => api.get<Event>(`/events/${id}`).then((r) => r.data),
  update: (id: number, data: Partial<Event>) =>
    api.patch<Event>(`/events/${id}`, data).then((r) => r.data),
  stats: () => api.get("/events/stats/summary").then((r) => r.data),
  triggerScrape: () => api.post("/scrape/events").then((r) => r.data),
};

export const connectionsApi = {
  list: (params?: Record<string, any>) =>
    api.get<{ total: number; items: Connection[] }>("/connections", { params }).then((r) => r.data),
  get: (id: number) => api.get<Connection>(`/connections/${id}`).then((r) => r.data),
  create: (data: Partial<Connection>) =>
    api.post<Connection>("/connections", data).then((r) => r.data),
  update: (id: number, data: Partial<Connection>) =>
    api.patch<Connection>(`/connections/${id}`, data).then((r) => r.data),
  logOutreach: (id: number, entry: any) =>
    api.post<Connection>(`/connections/${id}/outreach`, { entry }).then((r) => r.data),
  stats: () => api.get("/connections/stats/summary").then((r) => r.data),
};

export const applicationsApi = {
  list: (params?: Record<string, any>) =>
    api
      .get<{ total: number; items: Application[] }>("/applications", { params })
      .then((r) => r.data),
  get: (id: number) => api.get<Application>(`/applications/${id}`).then((r) => r.data),
  create: (data: Partial<Application>) =>
    api.post<Application>("/applications", data).then((r) => r.data),
  update: (id: number, data: Partial<Application>) =>
    api.patch<Application>(`/applications/${id}`, data).then((r) => r.data),
  addInterviewNote: (id: number, note: any) =>
    api.post<Application>(`/applications/${id}/interview-notes`, note).then((r) => r.data),
  pipeline: () => api.get("/applications/stats/pipeline").then((r) => r.data),
};

export const suggestionsApi = {
  list: (params?: Record<string, any>) =>
    api.get<Suggestion[]>("/suggestions", { params }).then((r) => r.data),
  feedback: (id: number, data: { is_dismissed?: boolean; is_acted_on?: boolean; user_feedback?: string }) =>
    api.patch<Suggestion>(`/suggestions/${id}/feedback`, data).then((r) => r.data),
  generate: () => api.post("/suggestions/generate").then((r) => r.data),
};
