/**
 * Anonymous client-side event tracking. Writes directly to the Supabase events
 * table via the public insert RLS policy. No PII captured; session ID is a
 * random string stored in sessionStorage so it resets when the tab closes.
 *
 * Why this exists: the Phase 3 data moat (response verification) requires
 * months of accumulated event data. We start collecting from day 1 even though
 * the data is not displayed yet.
 */

"use client";

import { supabase, DEFAULT_SCHOOL } from "./supabase";

const SESSION_KEY = "sd_session_id";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = window.sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export type EventType =
  | "page_view"
  | "company_card_click"
  | "company_detail_view"
  | "careers_link_click"
  | "filter_change";

export async function track(
  eventType: EventType,
  options: { companyId?: number; payload?: Record<string, unknown> } = {}
): Promise<void> {
  if (typeof window === "undefined") return;

  try {
    await supabase.from("events").insert({
      session_id: getSessionId(),
      school_slug: DEFAULT_SCHOOL,
      event_type: eventType,
      company_id: options.companyId ?? null,
      payload: options.payload ?? null,
    });
  } catch (err) {
    // Tracking must never break the page. Swallow errors silently.
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.warn("track failed", err);
    }
  }
}
