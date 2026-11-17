const fs = require('fs');
const { spawn } = require('child_process');

// Railway starts `node server.js` as PID 1, whatever the image CMD says.
// Node does not reap orphans, so every closed Chromium left zombie processes
// behind. Run the app under tini as a subreaper: orphans are re-parented to
// it and reaped. Outside a container (or already under tini) start directly.
const TINI = process.env.TINI_PATH || '/usr/bin/tini';

if (process.pid === 1 && !process.env.WA_SUPERVISED && fs.existsSync(TINI)) {
    const child = spawn(TINI, ['-s', '-g', '--', process.execPath, require.resolve('./app.js')], {
        stdio: 'inherit',
        env: { ...process.env, WA_SUPERVISED: '1' },
    });
    for (const signal of ['SIGTERM', 'SIGINT', 'SIGHUP']) {
        process.on(signal, () => child.kill(signal));
    }
    child.on('error', (err) => {
        console.error('Could not start tini:', err);
        process.exit(1);
    });
    child.on('exit', (code, signal) => {
        process.exit(code === null ? (signal ? 1 : 0) : code);
    });
} else {
    require('./app.js');
}
