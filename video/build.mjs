// Mux narration onto the recorded video: each scene's clip starts when its scene started on screen.
//   node build.mjs [--run out/run] [--audio out/audio] [--out out/wekil-demo.mp4]
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const HERE = path.dirname(new URL(import.meta.url).pathname);
const RUN = path.resolve(HERE, arg("--run", "out/run"));
const AUDIO = path.resolve(HERE, arg("--audio", "out/audio"));
const OUT = path.resolve(HERE, arg("--out", "out/wekil-demo.mp4"));
const LEAD = 0.35; // seconds of picture before each scene's first word

const scenes = JSON.parse(fs.readFileSync(path.join(RUN, "scenes.json"), "utf8"))
  .filter((s) => fs.existsSync(path.join(AUDIO, `${s.id}.wav`)));
const inputs = ["-i", path.join(RUN, "video.mp4")];
const filters = [];
scenes.forEach((s, i) => {
  inputs.push("-i", path.join(AUDIO, `${s.id}.wav`));
  const ms = Math.max(0, Math.round((s.start + LEAD) * 1000));
  filters.push(`[${i + 1}:a]aresample=48000,adelay=${ms}|${ms}[a${i}]`);
});
filters.push(`${scenes.map((_, i) => `[a${i}]`).join("")}amix=inputs=${scenes.length}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]`);
execFileSync("ffmpeg", ["-v", "error", "-y", ...inputs, "-filter_complex", filters.join(";"), "-map", "0:v", "-map", "[aout]",
  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT]);
console.log("wrote", OUT);
