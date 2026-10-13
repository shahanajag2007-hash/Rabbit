// Runs the FastAPI backend and the Vite dev server together: `npm run dev:all` (from frontend/).
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const rootDir = path.resolve(frontendDir, '..')
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')

const procs = [
  spawn(python, ['-m', 'uvicorn', 'api.main:app', '--reload', '--port', '8000'], { cwd: rootDir, stdio: 'inherit', shell: process.platform === 'win32' }),
  spawn('npx', ['vite'], { cwd: frontendDir, stdio: 'inherit', shell: process.platform === 'win32' }),
]

const stop = () => procs.forEach((p) => p.kill())
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
procs.forEach((p) => p.on('exit', (code) => {
  if (code) {
    console.error(`[dev-all] a process exited with code ${code}; stopping.`)
    stop()
    process.exit(code)
  }
}))
