#!/usr/bin/env node
// pm2-managed regenerator: keeps the public/ dashboard in sync with every
// live Hermes Kanban board by shelling out to generate.py once per interval.
// generate.py scans boards/*/kanban.db and emits public/index.html (portfolio)
// plus public/<board>.html (per-board) in a single pass.
const { execFile } = require('child_process');
const path = require('path');

const APP_DIR = __dirname;
const INTERVAL = (parseInt(process.env.REGEN_INTERVAL || '15', 10)) * 1000;

function run() {
  execFile('python3', [
    path.join(APP_DIR, 'generate.py'),
    // generate.py handles board discovery + multi-file output itself
  ], (err, stdout, stderr) => {
    if (err) {
      console.error('[regen error]', (stderr || err.message || '').trim());
    } else {
      console.log('[regen ok]', (stdout || '').trim().split('\n').join(' '));
    }
  });
}

run();
setInterval(run, INTERVAL);
console.log(`regenerator running (generate.py every ${INTERVAL / 1000}s, writes public/)`);
