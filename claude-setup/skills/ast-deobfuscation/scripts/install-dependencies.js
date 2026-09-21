#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const laoheSkillRoot = path.resolve(__dirname, "..");
const lao_1_heProjectRoot = path.resolve(laoheSkillRoot, "..", "..", "..");
const munianCacheRoot = path.join(
  lao_1_heProjectRoot,
  ".claude",
  "skills-next",
  "dependency-cache",
  "ast-deobfuscation",
);

function fail(message) {
  process.stderr.write(`[ast-deobfuscation] ${message}\n`);
  process.exit(1);
}

function assertInsideProject(target) {
  const relative = path.relative(lao_1_heProjectRoot, target);
  if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    fail(`refusing dependency path outside the project: ${target}`);
  }
}

function assertNoLinksOnExistingPath(target) {
  assertInsideProject(target);
  let cursor = path.resolve(target);
  const projectRoot = path.resolve(lao_1_heProjectRoot);
  while (cursor !== projectRoot) {
    if (fs.existsSync(cursor)) {
      const stat = fs.lstatSync(cursor);
      if (stat.isSymbolicLink()) fail(`refusing reparse/symlink dependency path: ${cursor}`);
      if (cursor !== target && !stat.isDirectory()) fail(`dependency parent is not a directory: ${cursor}`);
    }
    const parent = path.dirname(cursor);
    if (parent === cursor) fail(`dependency path escaped project root: ${target}`);
    cursor = parent;
  }
}

for (const fileName of ["package.json", "package-lock.json"]) {
  const source = path.join(laoheSkillRoot, fileName);
  if (!fs.existsSync(source) || !fs.lstatSync(source).isFile()) fail(`missing ${source}`);
}

assertNoLinksOnExistingPath(munianCacheRoot);
assertNoLinksOnExistingPath(path.join(munianCacheRoot, "node_modules"));
fs.mkdirSync(munianCacheRoot, { recursive: true });
for (const fileName of ["package.json", "package-lock.json"]) {
  fs.copyFileSync(path.join(laoheSkillRoot, fileName), path.join(munianCacheRoot, fileName));
}

const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
const result = spawnSync(
  npmCommand,
  ["ci", "--prefix", munianCacheRoot, "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund"],
  { stdio: "inherit", windowsHide: true, shell: process.platform === "win32" },
);
if (result.error) fail(`npm ci failed to start: ${result.error.message}`);
if (result.status !== 0) fail(`npm ci exited with code ${result.status}`);

try {
  require("./babel-runtime").loadBabel();
} catch (error) {
  fail(`installed cache failed validation: ${error.message}`);
}
process.stdout.write(`[ast-deobfuscation] dependency cache ready: ${path.relative(lao_1_heProjectRoot, munianCacheRoot)}\n`);
