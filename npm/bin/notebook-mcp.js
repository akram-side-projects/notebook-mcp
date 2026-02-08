#!/usr/bin/env node

const { launch } = require("../lib/launcher");

launch(process.argv.slice(2)).catch((err) => {
  const msg = err && err.stack ? err.stack : String(err);
  process.stderr.write(msg + "\n");
  process.exit(1);
});
