import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

import httpProxy from 'http-proxy';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const cliArgs = parseCliArgs(process.argv.slice(2));

const BACKEND_PORT = cliArgs.backendPort ?? process.env.BACKEND_PORT ?? '8001';
const FRONTEND_PORT = cliArgs.frontendPort ?? process.env.FRONTEND_PORT ?? '5174';
const PROXY_PORT = cliArgs.proxyPort ?? process.env.PROXY_PORT ?? '5173';
const DEV_HOST = cliArgs.host ?? process.env.HOST ?? '127.0.0.1';
const TARGET_HOST = DEV_HOST === '0.0.0.0' ? '127.0.0.1' : DEV_HOST;

const projectDir = path.join(ROOT, 'mcp-security-demo');
const backendDir = path.join(projectDir, 'backend');
const frontendDir = path.join(projectDir, 'frontend');

const pythonOverride = cliArgs.python ?? process.env.PYTHON;
const npmOverride = cliArgs.npm ?? process.env.NPM;

const resolvedPython = resolvePythonCommand({
  override: pythonOverride,
  backendDir,
});
const pythonCmd = resolvedPython.command;
const pythonPreArgs = resolvedPython.preArgs;
const resolvedNpm = resolveNpmCommand({ override: npmOverride });
const npmCmd = resolvedNpm.command;
const npmPreArgs = resolvedNpm.preArgs;

const children = [];
let server;

function spawnProcess(command, args, options) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: false,
    ...options,
  });

  child.on('exit', (code, signal) => {
    if (signal === 'SIGTERM' || signal === 'SIGINT') {
      return;
    }
    if (code !== 0) {
      console.error(`[orchestrator] ${command} exited with code ${code}`);
      shutdown(code ?? 1);
    } else {
      console.log(`[orchestrator] ${command} exited.`);
      shutdown(0);
    }
  });

  children.push(child);
  return child;
}

function shutdown(code = 0) {
  if (server) {
    server.close(() => {
      process.exit(code);
    });
  } else {
    process.exit(code);
  }
  for (const child of children) {
    if (!child.killed) {
      child.kill('SIGTERM');
    }
  }
}

console.log(`[orchestrator] backend python: ${resolvedPython.display}`);
console.log(`[orchestrator] frontend npm: ${resolvedNpm.display}`);

spawnProcess(pythonCmd, [...pythonPreArgs, '-m', 'uvicorn', 'backend.main:app', '--host', DEV_HOST, '--port', BACKEND_PORT, '--reload'], {
  cwd: projectDir,
});

spawnProcess(npmCmd, [...npmPreArgs, 'run', 'dev', '--', '--host', DEV_HOST, '--port', FRONTEND_PORT], {
  cwd: frontendDir,
});

const proxy = httpProxy.createProxyServer({
  ws: true,
  changeOrigin: true,
});

function selectTarget(urlPath = '/') {
  if (urlPath.startsWith('/api') || urlPath.startsWith('/ws')) {
    return `http://${TARGET_HOST}:${BACKEND_PORT}`;
  }
  return `http://${TARGET_HOST}:${FRONTEND_PORT}`;
}

server = http.createServer((req, res) => {
  const target = selectTarget(req.url ?? '/');
  proxy.web(
    req,
    res,
    { target },
    (err) => {
      console.error('[proxy] http error:', err.message);
      if (!res.headersSent) {
        res.writeHead(502, { 'content-type': 'text/plain' });
      }
      res.end('Reverse proxy error');
    },
  );
});

server.on('upgrade', (req, socket, head) => {
  const target = selectTarget(req.url ?? '/', true);
  proxy.ws(
    req,
    socket,
    head,
    { target },
    (err) => {
      console.error('[proxy] ws error:', err.message);
      socket.destroy();
    },
  );
});

server.listen(PROXY_PORT, () => {
  console.log(`[proxy] listening on http://localhost:${PROXY_PORT}`);
  console.log(`[proxy] /api and /ws -> backend:${BACKEND_PORT}`);
  console.log(`[proxy] static + HMR -> frontend:${FRONTEND_PORT}`);
});

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

function parseCliArgs(tokens) {
  const result = {};
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (!token.startsWith('--')) {
      continue;
    }
    let key = token.slice(2);
    let value;
    const eqIndex = key.indexOf('=');
    if (eqIndex >= 0) {
      value = key.slice(eqIndex + 1);
      key = key.slice(0, eqIndex);
    } else if (i + 1 < tokens.length && !tokens[i + 1].startsWith('--')) {
      value = tokens[i + 1];
      i += 1;
    } else {
      value = 'true';
    }
    const camelKey = key.replace(/-([a-z0-9])/g, (_match, char) => char.toUpperCase());
    result[camelKey] = value;
  }
  return result;
}

function resolvePythonCommand({ override, backendDir }) {
  const candidates = [];

  if (override) {
    const overrideTokens = tokenizeCommand(override);
    if (overrideTokens.length > 0) {
      candidates.push({
        command: overrideTokens[0],
        preArgs: overrideTokens.slice(1),
        display: override,
      });
    }
  }

  candidates.push(...detectVenvCandidates(backendDir));

  const platformDefaults = process.platform === 'win32'
    ? [
        { command: 'python.exe', preArgs: [], display: 'python.exe' },
        { command: 'python', preArgs: [], display: 'python' },
        { command: 'py', preArgs: ['-3'], display: 'py -3' },
        { command: 'py', preArgs: [], display: 'py' },
      ]
    : [
        { command: 'python3', preArgs: [], display: 'python3' },
        { command: 'python', preArgs: [], display: 'python' },
      ];

  candidates.push(...platformDefaults);

  for (const candidate of candidates) {
    if (candidate.command.includes(path.sep) && !fs.existsSync(candidate.command)) {
      continue;
    }
    if (commandRuns(candidate.command, candidate.preArgs)) {
      return candidate;
    }
  }

  throw new Error('[orchestrator] Unable to find a Python interpreter. Set --python, $PYTHON, or create backend/.venv.');
}

function detectVenvCandidates(backendDir) {
  const venvRoot = path.join(backendDir, '.venv');
  const variants = process.platform === 'win32'
    ? [['Scripts', 'python.exe'], ['Scripts', 'python']]
    : [['bin', 'python3'], ['bin', 'python']];

  return variants
    .map((segments) => path.join(venvRoot, ...segments))
    .filter((candidatePath) => fs.existsSync(candidatePath))
    .map((candidatePath) => ({
      command: candidatePath,
      preArgs: [],
      display: candidatePath,
    }));
}

function commandRuns(command, preArgs) {
  try {
    const probe = spawnSync(command, [...preArgs, '--version'], {
      stdio: 'ignore',
    });
    return probe.status === 0;
  } catch {
    return false;
  }
}

function tokenizeCommand(rawValue) {
  const tokens = [];
  let current = '';
  let quote = null;
  for (let i = 0; i < rawValue.length; i += 1) {
    const char = rawValue[i];
    if ((char === '"' || char === "'")) {
      if (quote === char) {
        quote = null;
        continue;
      }
      if (!quote) {
        quote = char;
        continue;
      }
    }
    if (!quote && /\s/.test(char)) {
      if (current) {
        tokens.push(current);
        current = '';
      }
      continue;
    }
    current += char;
  }
  if (current) {
    tokens.push(current);
  }
  return tokens;
}

function resolveNpmCommand({ override }) {
  if (override) {
    const overrideTokens = tokenizeCommand(override);
    if (overrideTokens.length > 0) {
      return {
        command: overrideTokens[0],
        preArgs: overrideTokens.slice(1),
        display: override,
      };
    }
  }

  const npmNodeExec = process.env.npm_node_execpath;
  const npmCliPath = process.env.npm_execpath;

  if (npmNodeExec && npmCliPath && fs.existsSync(npmNodeExec) && fs.existsSync(npmCliPath)) {
    return {
      command: npmNodeExec,
      preArgs: [npmCliPath],
      display: `${npmNodeExec} ${npmCliPath}`,
    };
  }

  const fallback = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  return {
    command: fallback,
    preArgs: [],
    display: fallback,
  };
}

