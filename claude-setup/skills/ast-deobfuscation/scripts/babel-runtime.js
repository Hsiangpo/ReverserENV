"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const laoheSkillRoot = path.resolve(__dirname, "..");
const lao_1_heProjectRoot = path.resolve(laoheSkillRoot, "..", "..", "..");
const munianCacheRoot = path.join(
  lao_1_heProjectRoot,
  ".claude",
  "skills-next",
  "dependency-cache",
  "ast-deobfuscation",
);
const sourcePackage = path.join(laoheSkillRoot, "package.json");
const sourceLock = path.join(laoheSkillRoot, "package-lock.json");
const cachePackage = path.join(munianCacheRoot, "package.json");
const cacheLock = path.join(munianCacheRoot, "package-lock.json");
const cacheNodeModules = path.join(munianCacheRoot, "node_modules");

let loadedBabel = null;

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function fail(reason) {
  throw new Error(
    `${reason}. Run: node .claude/skills/ast-deobfuscation/scripts/install-dependencies.js`,
  );
}

function requireRegularFile(filePath, label) {
  if (!fs.existsSync(filePath)) fail(`${label} is missing`);
  const stat = fs.lstatSync(filePath);
  if (!stat.isFile() || stat.isSymbolicLink()) fail(`${label} is not a regular file`);
}

function isInside(child, parent) {
  const relative = path.relative(parent, child);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative);
}

function loadBabel() {
  if (loadedBabel) return loadedBabel;

  for (const [filePath, label] of [
    [sourcePackage, "Skill package.json"],
    [sourceLock, "Skill package-lock.json"],
    [cachePackage, "dependency-cache package.json"],
    [cacheLock, "dependency-cache package-lock.json"],
  ]) {
    requireRegularFile(filePath, label);
  }
  if (!fs.existsSync(cacheNodeModules) || !fs.lstatSync(cacheNodeModules).isDirectory()) {
    fail("dependency-cache node_modules is missing");
  }
  if (sha256(sourcePackage) !== sha256(cachePackage) || sha256(sourceLock) !== sha256(cacheLock)) {
    fail("dependency-cache manifests are stale");
  }

  const lock = JSON.parse(fs.readFileSync(sourceLock, "utf8"));
  const cacheRequire = createRequire(cachePackage);
  const realNodeModules = fs.realpathSync(cacheNodeModules);
  const modules = {};
  for (const name of ["@babel/parser", "@babel/traverse", "@babel/generator", "@babel/types"]) {
    const expectedVersion = lock.packages?.[`node_modules/${name}`]?.version;
    if (!expectedVersion) fail(`lockfile has no direct entry for ${name}`);
    const installedPackage = path.join(cacheNodeModules, ...name.split("/"), "package.json");
    requireRegularFile(installedPackage, `${name} package.json`);
    const actualVersion = JSON.parse(fs.readFileSync(installedPackage, "utf8")).version;
    if (actualVersion !== expectedVersion) {
      fail(`${name} version drift: expected ${expectedVersion}, got ${actualVersion || "unknown"}`);
    }
    const resolved = fs.realpathSync(cacheRequire.resolve(name));
    if (!isInside(resolved, realNodeModules)) fail(`${name} resolved outside the dependency cache`);
    modules[name] = cacheRequire(name);
  }

  loadedBabel = {
    parser: modules["@babel/parser"],
    traverse: modules["@babel/traverse"].default,
    generator: modules["@babel/generator"].default,
    types: modules["@babel/types"],
  };
  return loadedBabel;
}

module.exports = {
  loadBabel,
};
