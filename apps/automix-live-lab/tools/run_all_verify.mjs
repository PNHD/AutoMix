import { readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const files = readdirSync(HERE).filter((f) => f.startsWith("verify_") && f.endsWith(".mjs")).sort();

let totalPass = 0;
let totalChecks = 0;
let failedFiles = [];
for (const f of files) {
  let out = "";
  let code = 0;
  try {
    out = execFileSync("node", [path.join(HERE, f)], { encoding: "utf-8" });
  } catch (e) {
    out = (e.stdout || "") + (e.stderr || "");
    code = e.status ?? 1;
  }
  const m = out.match(/RESULT:\s*(\d+)\/(\d+)\s*PASS/);
  if (m) {
    const [, pass, checks] = m;
    totalPass += Number(pass);
    totalChecks += Number(checks);
    console.log(`${code === 0 ? "OK  " : "FAIL"} ${f}: ${pass}/${checks}`);
    if (code !== 0) failedFiles.push(f);
  } else {
    console.log(`FAIL ${f}: no RESULT line found (exit ${code})`);
    console.log(out.split("\n").slice(-15).join("\n"));
    failedFiles.push(f);
  }
}
console.log(`\n=== TOTAL: ${totalPass}/${totalChecks} PASS across ${files.length} suites ===`);
if (failedFiles.length) console.log(`FAILED SUITES: ${failedFiles.join(", ")}`);
process.exit(failedFiles.length ? 1 : 0);
