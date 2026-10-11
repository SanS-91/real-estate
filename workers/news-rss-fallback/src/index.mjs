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
    const content = JSON.parse(atob(file.content.replace(/\\s/g, "")));
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

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(recover(controller.scheduledTime, env.GITHUB_TOKEN).then(result => {
      console.log("News RSS recovery", JSON.stringify(result));
    }));
  }
};
