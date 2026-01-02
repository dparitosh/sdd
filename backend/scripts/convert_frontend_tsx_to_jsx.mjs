#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { transformAsync } from '@babel/core';

const repoRoot = process.cwd();
const frontendSrcRoot = path.join(repoRoot, 'frontend', 'src');

function isTsxFile(filePath) {
  return filePath.endsWith('.tsx');
}

function walk(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  const results = [];

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(fullPath));
      continue;
    }
    if (entry.isFile() && isTsxFile(fullPath)) {
      results.push(fullPath);
    }
  }

  return results;
}

function gitMv(fromAbs, toAbs) {
  const fromRel = path.relative(repoRoot, fromAbs);
  const toRel = path.relative(repoRoot, toAbs);
  try {
    execFileSync('git', ['mv', fromRel, toRel], { stdio: 'inherit' });
  } catch {
    // Some workspaces have files present but not tracked by git.
    // Fall back to a plain filesystem rename to keep the conversion moving.
    fs.renameSync(fromAbs, toAbs);
  }
}

async function convertFile(tsxAbsPath) {
  const jsxAbsPath = tsxAbsPath.replace(/\.tsx$/i, '.jsx');

  if (!fs.existsSync(tsxAbsPath)) {
    return;
  }
  if (fs.existsSync(jsxAbsPath)) {
    // Already converted (or a previous partial run created the destination).
    return;
  }

  const input = fs.readFileSync(tsxAbsPath, 'utf8');

  const result = await transformAsync(input, {
    filename: tsxAbsPath,
    babelrc: false,
    configFile: false,
    sourceMaps: false,
    // Keep output reasonably close to input; formatting will be handled by existing tooling if desired.
    generatorOpts: {
      retainLines: true,
      comments: true,
      compact: false,
    },
    presets: [
      ['@babel/preset-typescript', { isTSX: true, allExtensions: true }],
      ['@babel/preset-react', { runtime: 'automatic' }],
    ],
  });

  if (!result?.code) {
    throw new Error(`Babel produced no output for ${tsxAbsPath}`);
  }

  gitMv(tsxAbsPath, jsxAbsPath);
  fs.writeFileSync(jsxAbsPath, result.code.endsWith('\n') ? result.code : `${result.code}\n`, 'utf8');
}

async function main() {
  if (!fs.existsSync(frontendSrcRoot)) {
    console.error(`Not found: ${frontendSrcRoot}`);
    process.exit(1);
  }

  const tsxFiles = walk(frontendSrcRoot);
  tsxFiles.sort();

  if (tsxFiles.length === 0) {
    console.log('No TSX files found under frontend/src.');
    return;
  }

  console.log(`Converting ${tsxFiles.length} TSX files to JSX...`);

  // Convert sequentially to keep output readable and avoid overwhelming git/FS.
  for (const tsxFile of tsxFiles) {
    await convertFile(tsxFile);
  }

  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
