#!/usr/bin/env node

import { spawn } from "child_process";
import { existsSync } from "fs";
import { homedir } from "os";

const BRIDGE = `${homedir()}/.blitz/blitz-mcp-bridge.sh`;
const APP = "/Applications/Blitz.app";

if (!existsSync(APP)) {
  console.error("Blitz.app not found. Install from: https://github.com/blitzdotdev/blitz-mac/releases");
  process.exit(1);
}

if (!existsSync(BRIDGE)) {
  console.error("Bridge script not found at ~/.blitz/blitz-mcp-bridge.sh — launch Blitz.app first.");
  process.exit(1);
}

const child = spawn("bash", [BRIDGE], {
  stdio: ["inherit", "inherit", "inherit"],
});
child.on("exit", (code) => process.exit(code ?? 1));
