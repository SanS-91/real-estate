const BASE = "https://api.github.com/repos/SanS-91/real-estate";
const HOURS = new Set([0,2,4,6,8,10,12,14]);

export function slotAt(timestamp) {
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime()) || !HOURS.has(date.getUTCHours())) {
    throw new Error("Invalid recovery schedule");
  }
  date.setUTCMinutes(20, 0, 0);
  return date.toISOString().replace(".000Z", "Z");
}

export async function recover(time, token, requester = fetch) {
  if (!token) throw new Error("Missing GITHUB_TOKEN secret");
  const slot = slotAt(time);
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "news-rss-fallback"
  };
  try {
    const result = await requester(BASE + "/contents/data/state/news-ingestion-health.json?ref=main", { headers });
    if (!result.ok) throw new Error("GitHub health unavailable");
    const file = await result.json();
    const content = JSON.parse(atob(file.content.replace(/\s/g, "")));
    if (Date.parse(content.checked_at) >= Date.parse(slot)) return { status: "already-checked", slot };
  } catch (error) {
    console.warn("Checking health failed, trying dispatch", String(error));
  }
  const result = await requester(BASE + "/actions/workflows/market-news-rss.yml/dispatches", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs: { trigger_source: "cloudflare-fallback", scheduled_slot: slot } })
  });
  if (result.status !== 204) throw new Error("GitHub dispatch HTTP " + result.status);
  return { status: "dispatched", slot };
}


const MACRO_HOURS = new Set([3, 9]);

export function macroSlotAt(timestamp) {
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime()) || !MACRO_HOURS.has(date.getUTCHours())
      || date.getUTCMinutes() !== 45) {
    throw new Error("Unexpected Macro recovery cron time");
  }
  date.setUTCMinutes(15, 0, 0);
  return date.toISOString().replace(".000Z", "Z");
}

export async function recoverMacro(time, token, requester = fetch) {
  if (!token) throw new Error("Missing GITHUB_TOKEN secret");
  const slot = macroSlotAt(time);
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "market-intelligence-macro-fallback"
  };
  try {
    const response = await requester(
      BASE + "/actions/workflows/macro-candidate.yml/runs?branch=main&per_page=30",
      { headers }
    );
    if (!response.ok) throw new Error("Unable to read Macro runs: HTTP " + response.status);
    const payload = await response.json();
    const runs = (payload.workflow_runs || []).filter(run =>
      run.head_branch === "main"
      && Date.parse(run.created_at) >= Date.parse(slot)
      && ["schedule", "workflow_dispatch"].includes(run.event)
    );
    if (runs.some(run => ["queued", "pending", "in_progress", "waiting"].includes(run.status))) {
      return { status: "already-running", slot };
    }
    if (runs.some(run => run.status === "completed" && run.conclusion === "success")) {
      return { status: "already-success", slot };
    }
  } catch (error) {
    // The GitHub collector retains data-integrity gates. On a transient read
    // failure we try a single dispatch rather than silently miss a slot.
    console.warn("Macro run lookup unavailable; attempting recovery:", String(error));
  }
  const result = await requester(
    BASE + "/actions/workflows/macro-candidate.yml/dispatches",
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        ref: "main",
        inputs: { source: "daily-markets-production" }
      })
    }
  );
  if (result.status !== 204) {
    throw new Error("GitHub Macro dispatch failed: HTTP " + result.status);
  }
  return { status: "dispatched", slot };
}

export default {
  async scheduled(controller, env, ctx) {
    const when = new Date(controller.scheduledTime);
    const isMacro = when.getUTCMinutes() === 45 && MACRO_HOURS.has(when.getUTCHours());
    const task = isMacro
      ? recoverMacro(controller.scheduledTime, env.GITHUB_TOKEN)
      : recover(controller.scheduledTime, env.GITHUB_TOKEN);
    ctx.waitUntil(task.then(result => {
      console.log(isMacro ? "Macro recovery" : "News RSS recovery", JSON.stringify(result));
    }));
  }
};
