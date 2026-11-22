// Cross-repo proof for `run.progress` (ADR 020). Feeds the pinned portfolio site's own `readSse`
// parser with (1) the committed v1 examples and (2) the exact wire text rendered by the API's
// `execute_run` without and with the opt-in header (`python -m scripts.sse_sample`). Every v1 stream
// must parse with the v1 event set only, and the site must either never send `X-Assistant-Progress`
// or accept the opted-in stream.
// Usage: node scripts/site_stream_compat.mjs <portfolio checkout> <sse-sample.json>
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const site = resolve(process.argv[2] ?? "artifacts/compat-site");
const sample = JSON.parse(readFileSync(resolve(process.argv[3] ?? "artifacts/sse-sample.json"), "utf8"));
const { readSse } = await import(
  pathToFileURL(join(site, "src/features/assistant/adapters/sse.ts")).href
);
const examples = JSON.parse(
  readFileSync(new URL("../contracts/sse.examples.json", import.meta.url), "utf8"),
);
const V1 = new Set([
  "run.started",
  "run.status",
  "message.delta",
  "message.completed",
  "run.completed",
  "run.failed",
  "run.cancelled",
]);

const frames = (events) =>
  events.map((event) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join("");

async function parse(text) {
  const bytes = new TextEncoder().encode(text);
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
  const seen = [];
  const terminal = await readSse(body, (event) => seen.push(event.type));
  if (!terminal) throw new Error("stream ended without a terminal event");
  return seen;
}

async function accepts(text) {
  try {
    await parse(text);
    return true;
  } catch {
    return false;
  }
}

function sources(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.(ts|tsx|js|mjs)$/.test(name) ? [path] : [];
  });
}

const v1 = {
  "example success_abstention": frames(examples.success_abstention),
  "example failure": frames([examples.success_abstention[0], { ...examples.failure, sequence: 1 }]),
  "example cancelled": frames([examples.success_abstention[0], { ...examples.cancelled, sequence: 1 }]),
  ...Object.fromEntries(Object.entries(sample.v1).map(([name, text]) => [`rendered ${name}`, text])),
};
for (const [name, text] of Object.entries(v1)) {
  const seen = await parse(text);
  const extra = seen.filter((type) => !V1.has(type));
  if (extra.length) throw new Error(`${name}: non-v1 events without the opt-in: ${extra}`);
  console.log(`ok v1 ${name}: ${seen.length} events`);
}

const optsIn = sources(join(site, "src")).some((path) =>
  /x-assistant-progress/i.test(readFileSync(path, "utf8")),
);
const optInStreams = [frames(examples.opt_in_progress), ...Object.values(sample.opt_in)];
if (!optInStreams.every((text) => text.includes("event: run.progress")))
  throw new Error("opted-in streams carry no run.progress event");
const accepted = (await Promise.all(optInStreams.map(accepts))).every(Boolean);
if (optsIn && !accepted) throw new Error("the site opts in to run.progress but rejects it");
console.log(
  optsIn
    ? "ok the site opts in and accepts run.progress"
    : `ok the site never sends X-Assistant-Progress (its parser ${accepted ? "accepts" : "rejects"}` +
        " run.progress, so default-on needs a site change first)",
);
