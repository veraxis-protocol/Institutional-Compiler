#!/usr/bin/env node
/**
 * IEEE-754 differential: compare Python veip_core.canonical float serialization
 * against ECMAScript Number::toString (Node.js String()).
 *
 * Reads differential_corpus.jsonl from the path in argv[2], or from
 * <package-root>/inputs/differential_corpus.jsonl.
 * Each line: {"bits": "<16-hex-chars>", "py": "<python canonical string>"}
 *
 * For each value, reconstructs the float from bits, calls String(),
 * and compares against "py".
 *
 * Writes JSON result to stdout:
 * {"total": N, "pass": N, "fail": N, "failures": [...first 20...]}
 */
'use strict';

const fs = require('fs');
const path = require('path');

const corpusPath = process.argv[2] ||
  path.join(__dirname, '..', 'inputs', 'differential_corpus.jsonl');

const lines = fs.readFileSync(corpusPath, 'utf-8').split('\n').filter(Boolean);
const total = lines.length;

let pass = 0;
let fail = 0;
const failures = [];

for (const line of lines) {
  const { bits, py } = JSON.parse(line);
  const buf = Buffer.from(bits, 'hex');
  const view = new DataView(buf.buffer.slice(buf.byteOffset, buf.byteOffset + 8));
  const f = view.getFloat64(0, false); // big-endian IEEE-754
  const js = String(f);
  if (py === js) {
    pass++;
  } else {
    fail++;
    if (failures.length < 20) {
      failures.push({ bits, py, js });
    }
  }
}

const result = { total, pass, fail, failures };
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
process.exit(fail > 0 ? 1 : 0);
