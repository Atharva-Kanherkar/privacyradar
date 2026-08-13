import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function privacyradarBin(): string {
  const fromVenv = path.resolve(__dirname, "../../worker/.venv/bin/privacyradar");
  if (fs.existsSync(fromVenv)) {
    return fromVenv;
  }
  return "privacyradar";
}

export default async function globalSetup(): Promise<void> {
  const bin = privacyradarBin();
  execFileSync(bin, ["migrate"], { stdio: "inherit", env: process.env });
  execFileSync(bin, ["seed-fixtures"], { stdio: "inherit", env: process.env });
}
