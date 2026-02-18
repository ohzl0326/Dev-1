"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function NewConnectionPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    current_title: "",
    current_company: "",
    location: "",
    linkedin_url: "",
    email: "",
    how_met: "",
    seniority: "",
    warmth: "cold",
    is_hiring_manager: false,
    is_recruiter: false,
    relevance_notes: "",
    industry: "Asset Management",
  });

  const create = useMutation({
    mutationFn: () => connectionsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      router.push("/connections");
    },
  });

  const set = (field: string, value: any) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Add Connection</h1>
        <p className="text-sm text-gray-500">Log a new networking contact</p>
      </div>

      <div className="card space-y-4">
        {[
          { label: "Full Name *", field: "name", placeholder: "Jane Smith" },
          { label: "Current Title", field: "current_title", placeholder: "Institutional RM" },
          { label: "Company", field: "current_company", placeholder: "BlackRock" },
          { label: "Location", field: "location", placeholder: "Singapore" },
          { label: "LinkedIn URL", field: "linkedin_url", placeholder: "https://linkedin.com/in/..." },
          { label: "Email", field: "email", placeholder: "jane@example.com" },
          { label: "How we met", field: "how_met", placeholder: "CFA Singapore networking event, Nov 2025" },
          { label: "Seniority", field: "seniority", placeholder: "VP, Director, MD..." },
        ].map(({ label, field, placeholder }) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input
              type="text"
              value={(form as any)[field]}
              onChange={(e) => set(field, e.target.value)}
              placeholder={placeholder}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-200"
            />
          </div>
        ))}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Warmth</label>
          <select
            value={form.warmth}
            onChange={(e) => set("warmth", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none"
          >
            <option value="cold">Cold</option>
            <option value="warm">Warm</option>
            <option value="hot">Hot</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Relevance Notes</label>
          <textarea
            value={form.relevance_notes}
            onChange={(e) => set("relevance_notes", e.target.value)}
            rows={3}
            placeholder="Why is this person valuable to your search?"
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-200"
          />
        </div>

        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_hiring_manager}
              onChange={(e) => set("is_hiring_manager", e.target.checked)}
              className="rounded"
            />
            Hiring Manager
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_recruiter}
              onChange={(e) => set("is_recruiter", e.target.checked)}
              className="rounded"
            />
            Recruiter
          </label>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            className="btn-primary flex-1"
            onClick={() => create.mutate()}
            disabled={!form.name || create.isPending}
          >
            {create.isPending ? "Saving..." : "Save Connection"}
          </button>
          <button className="btn-secondary" onClick={() => router.back()}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
