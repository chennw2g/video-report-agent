#!/usr/bin/env node
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const DEFAULT_DOMAINS = [
  "youtube.com",
  "google.com",
  "googleusercontent.com",
  "googlevideo.com",
  "ytimg.com",
];

function parseArgs(argv) {
  const out = new Map();
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const eq = arg.indexOf("=");
    if (eq >= 0) {
      out.set(arg.slice(2, eq), arg.slice(eq + 1));
      continue;
    }
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith("--")) {
      out.set(key, next);
      i += 1;
    } else {
      out.set(key, "true");
    }
  }
  return out;
}

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJsonWithRetry(url, attempts = 20) {
  let lastError = null;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const res = await fetch(url);
      if (res.ok) return await res.json();
      lastError = new Error(`HTTP ${res.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw lastError ?? new Error(`Unable to fetch ${url}`);
}

class CdpClient {
  constructor(url) {
    this.url = url;
    this.nextId = 1;
    this.pending = new Map();
  }

  async connect() {
    if (typeof WebSocket !== "function") {
      throw new Error("Node.js WebSocket support is unavailable; use Node 22+ or 24+.");
    }
    this.ws = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("CDP WebSocket timeout")), 5000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timeout);
        resolve();
      });
      this.ws.addEventListener("error", (event) => {
        clearTimeout(timeout);
        reject(new Error(`CDP WebSocket error: ${event.message ?? "unknown"}`));
      });
    });
    this.ws.addEventListener("message", (event) => {
      const payload =
        typeof event.data === "string" ? event.data : Buffer.from(event.data).toString("utf8");
      const msg = JSON.parse(payload);
      if (!msg.id) return;
      const pending = this.pending.get(msg.id);
      if (!pending) return;
      this.pending.delete(msg.id);
      if (msg.error) {
        pending.reject(new Error(msg.error.message ?? JSON.stringify(msg.error)));
      } else {
        pending.resolve(msg.result ?? {});
      }
    });
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(payload);
    });
  }

  close() {
    this.ws?.close();
  }
}

function cookieDomainMatches(domain, includeDomains) {
  const normalized = domain
    .replace(/^#HttpOnly_/, "")
    .replace(/^\./, "")
    .toLowerCase();
  return includeDomains.some(
    (candidate) => normalized === candidate || normalized.endsWith(`.${candidate}`),
  );
}

function safeField(value) {
  return String(value ?? "").replace(/[\r\n\t]/g, "");
}

function toNetscapeLine(cookie) {
  const domainRaw = safeField(cookie.domain);
  const domain =
    cookie.httpOnly && !domainRaw.startsWith("#HttpOnly_") ? `#HttpOnly_${domainRaw}` : domainRaw;
  const includeSubdomains = domainRaw.startsWith(".") ? "TRUE" : "FALSE";
  const pathValue = safeField(cookie.path || "/");
  const secure = cookie.secure ? "TRUE" : "FALSE";
  const expires =
    typeof cookie.expires === "number" && Number.isFinite(cookie.expires) && cookie.expires > 0
      ? String(Math.floor(cookie.expires))
      : "0";
  const name = safeField(cookie.name);
  const value = safeField(cookie.value);
  return `${domain}\t${includeSubdomains}\t${pathValue}\t${secure}\t${expires}\t${name}\t${value}`;
}

const args = parseArgs(process.argv.slice(2));
const port = Number(args.get("port") ?? "9223");
const output = args.get("output");
const includeDomains = (args.get("domains") ?? DEFAULT_DOMAINS.join(","))
  .split(",")
  .map((entry) => entry.trim().replace(/^\./, "").toLowerCase())
  .filter(Boolean);

if (!output) {
  console.error("Missing --output <path>.");
  process.exit(2);
}
if (!Number.isFinite(port) || port <= 0) {
  console.error("Invalid --port.");
  process.exit(2);
}

const version = await fetchJsonWithRetry(`http://127.0.0.1:${port}/json/version`);
const wsUrl = version.webSocketDebuggerUrl;
if (typeof wsUrl !== "string" || wsUrl.length === 0) {
  console.error("Chrome DevTools endpoint did not expose webSocketDebuggerUrl.");
  process.exit(2);
}

const client = new CdpClient(wsUrl);
await client.connect();
try {
  const result = await client.send("Storage.getCookies", {});
  const cookies = Array.isArray(result.cookies) ? result.cookies : [];
  const selected = cookies
    .filter(
      (cookie) =>
        cookie?.name && cookie?.domain && cookieDomainMatches(cookie.domain, includeDomains),
    )
    .sort((a, b) => `${a.domain}\t${a.name}`.localeCompare(`${b.domain}\t${b.name}`));

  if (selected.length === 0) {
    console.error(`No matching cookies were available from Chrome for: ${includeDomains.join(",")}`);
    process.exit(3);
  }

  const lines = [
    "# Netscape HTTP Cookie File",
    "# Generated by video-bundle-agent cookie refresh; do not commit this file.",
    ...selected.map(toNetscapeLine),
    "",
  ];
  await mkdir(path.dirname(output), { recursive: true });
  await writeFile(output, lines.join("\n"), "utf8");
  console.log(
    JSON.stringify({ ok: true, output, cookies: selected.length, domains: includeDomains }),
  );
} finally {
  client.close();
}
