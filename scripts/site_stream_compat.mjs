// Cross-repo proof for `run.progress` (ADR 020): the pinned portfolio site parses every v1 example
// stream, and it either never opts in to progress or accepts the opted-in stream.
// Usage: node scripts/site_stream_compat.mjs <portfolio checkout>
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const site = resolve(process.argv[2] ?? "artifacts/compat-site");
const { readSse } = await import(
  pathToFileURL(join(site, "src/features/assistant/adapters/sse.ts")).href
);
const examples = JSON.parse(
  readFileSync(new URL("../contracts/sse.examples.json", import.meta.url), "utf8"),
);

function stream(events) {
  const bytes = new TextEncoder().encode(
    events.map((event) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join(""),
  );
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
}

async function parse(events) {
  const seen = [];
  const terminal = await readSse(stream(events), (event) => seen.push(event.type));
  return { terminal, seen };
}

function sources(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.(ts|tsx|js|mjs)$/.test(name) ? [path] : [];
  });
}

const v1 = {
  success_abstention: examples.success_abstention,
  failure: [examples.success_abstention[0], { ...examples.failure, sequence: 1 }],
  cancelled: [examples.success_abstention[0], { ...examples.cancelled, sequence: 1 }],
};
for (const [name, events] of Object.entries(v1)) {
  const { terminal, seen } = await parse(events);
  if (!terminal || seen.length !== events.length) throw new Error(`site rejected v1 ${name}`);
  console.log(`ok v1 ${name}: ${seen.length} events`);
}

const optsIn = sources(join(site, "src")).some((path) =>
  /x-assistant-progress/i.test(readFileSync(path, "utf8")),
);
if (optsIn) {
  const { terminal } = await parse(examples.opt_in_progress);
  if (!terminal) throw new Error("site opts in to run.progress but does not accept it");
  console.log("ok site opts in and accepts run.progress");
} else {
  let rejected = false;
  try {
    await parse(examples.opt_in_progress);
  } catch {
    rejected = true;
  }
  console.log(
    `ok site never sends X-Assistant-Progress, so it never receives run.progress` +
      ` (its parser ${rejected ? "rejects" : "accepts"} the event; default-on needs a site change)`,
  );
}
