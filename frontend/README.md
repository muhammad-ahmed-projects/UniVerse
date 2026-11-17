# UniVerse — Dashboard (frontend)

React + TypeScript + Tailwind dashboard for the UniVerse surveillance
system: live camera status, alerts, incident review (acknowledge/resolve),
registered people, and per-camera detection settings.

Built on the free [TailAdmin React](https://github.com/TailAdmin/free-react-tailwind-admin-dashboard)
template (MIT, see `LICENSE.md`); its demo pages were removed and its UI
components reused.

## Run

```sh
npm install
cp .env.example .env     # points at the backend, default http://127.0.0.1:8000
npm run dev
```

The backend must be running first — see `/docs/setup.md` in the repo root.

## Checks

```sh
npm run build   # tsc -b + production build
npm run lint    # oxlint + eslint
```
