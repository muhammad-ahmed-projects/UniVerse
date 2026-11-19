# Setup Guide: Fresh Windows PC to Running UniVerse

This guide takes a new team member from an empty Windows PC to a working
UniVerse setup: database, backend API, dashboard, and the AI scripts
running against a webcam or IP camera. Follow the steps in order. Each
step ends with a check, so you know it worked before you move on.

- **Time:** about 45-60 minutes. Most of that is downloads.
- **Disk space:** about 4 GB free. The Python packages are about 1.4 GB
  (PyTorch is most of it), the dashboard packages about 300 MB, and the
  face-recognition model about 300 MB.
- **Internet:** needed for the first setup. Daily use after that is
  local.
- **Shell:** every command below is for **PowerShell** (Windows
  Terminal or the VS Code terminal). Linux/macOS notes are at the end.

## How the pieces fit

| Piece | What it is | Where it runs |
|---|---|---|
| PostgreSQL | Database: users, cameras, alerts, incidents | Windows service, port `5432` |
| Backend API | FastAPI app in `backend/` | `http://127.0.0.1:8000` |
| Dashboard | React app in `frontend/` | `http://localhost:5173` |
| AI scripts | Python scripts in `backend/app/ai/prototypes/` | Started from the dashboard (Monitoring), or one terminal per script |

The AI scripts read a camera, detect events, and send alerts, evidence
photos and live video to the backend. The dashboard shows all of it live.

---

## Step 1: Install the tools (one time)

| Tool | Version | Download | During install |
|---|---|---|---|
| Git | Any recent | https://git-scm.com/download/win | Defaults are fine |
| Python | **3.12** | https://www.python.org/downloads/windows/ | Tick **"Add python.exe to PATH"** on the first screen |
| Node.js | **24.x** | https://nodejs.org/en/download | Defaults are fine |
| PostgreSQL | **17** | https://www.postgresql.org/download/windows/ (EDB installer) | Set a password for the `postgres` user and **write it down**. Keep port `5432`. Skip Stack Builder at the end. |
| VS Code | Optional | https://code.visualstudio.com/ | |

Use Python 3.12 specifically. Every package version in
`requirements.txt` is tested on 3.12, and other versions may fail to
install.

**Exact versions the team tested on:** Windows 11 Pro, Python 3.12.10,
Node.js 24.18.0 (npm 11.16.0), PostgreSQL 17.11, and Git 2.54.0. A newer
patch version (for example Python 3.12.11 or Node 24.19) is fine. You
don't choose package versions yourself: `backend/requirements.txt` pins
every Python package, and `frontend/package-lock.json` pins every npm
package. Key ones:

| Package | Version | Used for |
|---|---|---|
| FastAPI | 0.162.2 | Backend API |
| SQLAlchemy / Alembic | 2.1.8 / 1.20.1 | Database access and migrations |
| PyTorch | 2.15.0 (CPU build) | Runs the YOLO model; no GPU needed |
| Ultralytics (YOLOv8n) | 8.4.208 | Person detection + ByteTrack tracking |
| InsightFace (buffalo_l model) | 2.1 | Face recognition |
| OpenCV | 5.0.0.93 | Camera and video input |
| React / TypeScript / Tailwind CSS / Vite | 19 / 6.0 / 4 / 8 | Dashboard (exact versions in `package-lock.json`) |

Open a **new** PowerShell window (so it picks up the new PATH) and check:

```powershell
git --version
py -3.12 --version
node --version
npm --version
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" --version
```

Expected: a version for each. Python should be `3.12.x`, Node `v24.x`,
and psql `17.x`.

If `py` is not recognized, the Python launcher isn't on your PATH. Use
the full path to Python instead, everywhere this guide says `py -3.12`:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
```

Don't use a bare `python` until the venv is active (Step 4.1). On many
Windows PCs it opens the Microsoft Store instead of running Python.

Allow PowerShell to run the Python virtual-environment script. You only
do this once per Windows user. Answer `Y` if asked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Step 2: Get the code

```powershell
cd D:\
git clone https://github.com/muhammad-ahmed-projects/UniVerse.git
cd UniVerse
```

Clone into a **short path** such as `D:\UniVerse` or `C:\UniVerse`, not
deep inside Desktop or Documents. PyTorch installs files with very long
names, and Windows by default refuses paths over 260 characters, so a deep
folder makes Step 4.1 fail. If you must use a longer path, turn on long
path support once, in a PowerShell window opened with **Run as
administrator**, then restart the PC:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

If GitHub says `Repository not found`, the repository is private. Ask
Muhammad Ahmed to add your GitHub account as a collaborator, accept the
email invite, and run `git clone` again.

## Step 3: Create the database

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE universe_dev;"
```

Enter the `postgres` password from Step 1.

**Check:** the output is `CREATE DATABASE`.

You don't need to create the test database. The tests create
`universe_test` themselves.

## Step 4: Backend

### 4.1 Create the virtual environment and install packages

```powershell
cd D:\UniVerse\backend
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

After `Activate.ps1`, your prompt starts with `(venv)`. Every backend and
AI command needs this. If you open a new terminal, run
`venv\Scripts\Activate.ps1` again from `backend\`.

The install takes 5-15 minutes. Yellow warnings are fine. A red `ERROR`
line is not; see [Troubleshooting](#troubleshooting).

### 4.2 Create your `.env` file

The `.env` file holds your passwords and secrets. It is per-person and
is never committed to git.

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
notepad .env
```

The `python -c` command prints a 64-character random string. Copy it,
then fill in `.env`:

| Setting | What to put |
|---|---|
| `DATABASE_URL` | Replace `your_password_here` with your `postgres` password. If the password contains `@ : / #`, URL-encode those characters (for example `@` becomes `%40`). |
| `JWT_SECRET` | Paste the 64-character string. It must be at least 32 characters, or the API refuses to start. |
| `CORS_ORIGINS` | Leave as it is. |
| `MEDIA_DIR` | Leave empty. Evidence photos and face thumbnails then go to `backend\media\` (gitignored). |
| `EVIDENCE_RETENTION_DAYS` | Leave at `30`. Evidence photos older than this are deleted automatically. `0` keeps them forever. |
| `UNIVERSE_API_BASE` | Leave as it is. |
| `UNIVERSE_API_USERNAME` | `ai_service` (the AI scripts' own account) |
| `UNIVERSE_API_PASSWORD` | `ai_service123` (the dev password that the seed script creates) |

Save and close Notepad.

### 4.3 Create the tables and the demo data

```powershell
alembic upgrade head
python -m app.db.seed
```

**Check:** Alembic prints `Running upgrade ...` lines and the seed script
prints `Seed complete.` You can run the seed script again safely; it
doesn't create duplicates.

The seed script creates:

| Type | Name | Details |
|---|---|---|
| Account | `admin` / `admin123` | Role: admin (can change cameras, people, settings) |
| Account | `operator` / `operator123` | Role: security operator (reviews alerts and incidents) |
| Account | `ai_service` / `ai_service123` | Role: AI service. The AI scripts log in with it; don't use it for the dashboard. It is the only non-admin account that can read face data. |
| Camera | Test Camera 1 | ID `1`, source `0` (first webcam) |
| Camera | Test Camera 2 | ID `2`, source `1` |

### 4.4 Start the API

```powershell
python -m uvicorn app.main:app --reload
```

**Check:**
- The terminal shows `Uvicorn running on http://127.0.0.1:8000`.
- http://127.0.0.1:8000/ shows `{"status":"ok","service":"universe-backend"}`.
- http://127.0.0.1:8000/docs shows the interactive API docs.

Leave this terminal open. The API stops when you close it.

## Step 5: Dashboard

Open a **second** terminal:

```powershell
cd D:\UniVerse\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

You don't need to edit the frontend `.env`. It already points at
`http://127.0.0.1:8000`.

**Check:** open http://localhost:5173 and sign in with `admin` /
`admin123`. The Overview page shows "Cameras online 0 / 2", because the
two test cameras have no script reporting yet. The sidebar has
Dashboard, Live View, Cameras, Alerts, Incidents, Registered People, and
Settings.

If Vite prints `Port 5173 is in use, trying another one...`, another dev
server is already running. Close it and run `npm run dev` again.
Otherwise sign-in fails, because the backend only accepts the URLs in
`CORS_ORIGINS`.

## Step 6: Turn a camera on (from the dashboard)

The easiest way: the dashboard starts the AI analysis for you.

1. Close every other app that uses the webcam (Camera app, Zoom, Teams,
   a browser tab). On Windows, only one program can use a USB webcam at
   a time.
2. Sign in as `admin`, open **Cameras**, and click **Monitoring** on
   Test Camera 1 (stream source `0`, your webcam).
3. Choose what to run, then click **Start monitoring**:

   | Analysis | What it does |
   |---|---|
   | People, restricted area & unusual activity | Boxes and IDs for people; alerts on entering the restricted zone, staying too long, a crowd, running, a possible fall and an unattended bag |
   | Face recognition | Names registered people, updates their "last seen", alerts on unknown faces |
   | Tamper detection | Alerts when the camera is covered, moved or out of focus |
   | Camera health only | Watches whether the feed is up; no detection |

   A USB webcam takes one analysis at a time. An IP camera can run
   several together.
4. Within a few seconds the dialog shows the live video, the camera's
   status turns **online**, and **Script output** shows what the analysis
   is doing. The **Live View** page shows every camera the same way;
   click a tile to open its monitoring dialog.
5. Click **Stop monitoring** to turn it off. The camera's status becomes
   **unknown**, because nothing is watching it any more.

If an analysis stops on its own (for example, the camera can't be
opened), the camera turns **offline**, the dialog says "stopped with
error", and the last lines of **Script output** say why.

Monitoring started from the dashboard runs inside the backend, so it
stops when you stop the backend. Start it again after a restart.

On the Cameras page an admin can also **Edit** a camera (name, location,
stream source) or **Delete** it. Deleting also deletes the camera's
alerts, incidents and evidence photos.

### Review alerts, tune unusual activity, read the audit log

- **Alerts**: mark each alert **Real** or **False alarm** (**undo** puts
  it back). The **Detection accuracy** card at the top turns these into
  precision and false-alarm rate, overall and per alert type. Creating an
  incident from an alert also counts it as real. Operators can review too.
- **Settings > Unusual Activity** (per camera, admin only):
  - **Crowd: people**: how many people in view at once raise a crowd alert.
  - **Running: speed**: in frame widths per second (0.6 means crossing
    the picture in under 2 seconds).
  - **Unattended bag (s)**: how long a backpack, handbag or suitcase may
    stay still with nobody near it.
  - **Fall: lying (s)**: how long someone who was standing must stay lying.

  Set any of them to `0` to turn that alert off. Restart the camera's
  monitoring to apply changes. To test quickly, set **Crowd: people** to
  `1` and stand in front of the webcam.
- **Audit Log** (admin only, in the sidebar): every sign-in and failed
  sign-in, account change, camera and settings change, monitoring
  start/stop, face-photo access, alert review and incident action, with
  the user, time and IP. Filter by category or search by username.

## Step 7: Run the AI scripts from a terminal (optional)

The dashboard runs the same scripts. Running them yourself is useful for
testing and for options the dashboard doesn't offer (`--help` lists them
all). Don't start a script for a camera the dashboard is already
monitoring.

Open a **third** terminal:

```powershell
cd D:\UniVerse\backend
venv\Scripts\Activate.ps1
```

### 7.1 First test: person detection

```powershell
python -m app.ai.prototypes.person_detection --source 0
```

The first run downloads the YOLO model (`yolov8n.pt`, about 6 MB). A
window opens with boxes around people. Press **`q`** in that window to
stop.

`--source 0` is the first webcam. Try `1` if you have more than one. You
can also pass a video file path or an RTSP URL.

### 7.2 Connect a script to the dashboard

Add `--camera-id <ID>` to connect a script to the dashboard. The ID is in
the **ID** column on the Cameras page. The script logs in with
`UNIVERSE_API_USERNAME` and `UNIVERSE_API_PASSWORD` from `backend\.env`,
and then it:
- reads its thresholds from the Settings page,
- streams its annotated video to the **Live View** page,
- sends real alerts, each with 3 evidence photos.

Try it with the dashboard's **Live View** page open in your browser:

```powershell
python -m app.ai.prototypes.roi_loitering --source 0 --camera-id 1
```

Within a few seconds, Test Camera 1's tile shows your webcam with a red
**LIVE** label. Walk into the restricted zone, the light-blue box. Your
box turns red when you're inside it. A `ROI_ENTRY` alert appears on the
Alerts page without a refresh, with photo thumbnails in the **Evidence**
column; click one to see it full size. Stay in the zone longer than the
loitering threshold and a `LOITERING` alert follows. Promote an alert to
an incident, and the incident keeps its evidence photos.

Add `--headless` if you don't want the script's own window; the
dashboard still shows the video.

| Script | What it does | With `--camera-id` it raises |
|---|---|---|
| `person_detection` | Boxes around people | (no alerts) |
| `tracking` | Same, plus a stable ID per person | (no alerts) |
| `roi_loitering` | Restricted zone + time in zone | `ROI_ENTRY`, `LOITERING` |
| `tamper_detection` | Covered / moved / out-of-focus camera | `TAMPER_COVERED`, `TAMPER_MOVED`, `TAMPER_DEFOCUSED` |
| `face_recognition` | Known vs unknown faces | `UNKNOWN_FACE` (at most once per 30 s), and "last seen" on the People page |
| `camera_health` | Camera online / offline | `CAMERA_OFFLINE`, `CAMERA_ONLINE`, and the live status on the Cameras page |

`person_detection` and `tracking` are the early prototypes and have no
`--camera-id`. Every other script streams to Live View when it has one.

Run every script the same way: `python -m app.ai.prototypes.<script> --source ...`.
Add `--help` to any script to see all its options.

The scripts read the Settings page only when they start. After you
change a camera's settings, stop its scripts with `q` and start them
again.

## Step 8: Register faces and recognize people

Register people only with their consent. Face data is stored in the
database and in `backend\media\faces\`, and only admins can see it.

1. Sign in as `admin` and open **Registered People**.
2. Click **Register Person**, type the name, tick the consent box, and
   click **Next: add photos**.
3. Add 3-5 photos of the person: looking straight at the camera, then
   turned slightly left and right. Use **Upload photos** for existing
   photos, or **Use camera** to take them with the laptop camera.
   - Each photo must show exactly one face. The dashboard tells you if it
     finds no face or several faces.
   - The first photo takes a few seconds longer, because the backend
     loads the face model. The first time ever, it also downloads the
     model (about 300 MB) into `C:\Users\<you>\.insightface\models\`.
   - **Use camera** can't open the webcam while monitoring (or any AI
     script) is using it. Stop monitoring first, or upload photos instead.
4. Click **Done**. The table shows the number of photos per person.

Then turn on recognition: **Cameras > Monitoring** on a camera, choose
**Face recognition**, and click **Start monitoring** (or, from a
terminal: `python -m app.ai.prototypes.face_recognition --source 0
--camera-id 1`). Then:

- Registered people get a green box with their name; everyone else is a
  red "Unknown" box and raises an `UNKNOWN_FACE` alert with evidence.
- The People page shows each recognized person's **Last seen** camera
  and time, updated live.
- People you register while the script runs are picked up within 30
  seconds; no restart needed.
- If recognition confuses people or misses someone, change **Face
  Recognition > Match threshold** on the Settings page (higher means
  stricter), then stop and start monitoring again.
- On a laptop CPU, face recognition processes about 1 frame per second,
  so its live view updates slowly. That's normal without a GPU.

## Step 9: IP cameras (RTSP)

1. Set up the camera with its brand's mobile app and connect it to the
   **same Wi-Fi or router** as the PC.
2. Find the camera's IP address in the brand app or in your router's
   list of connected devices. In the router, give the camera a fixed IP
   (often called "DHCP reservation"), so the address doesn't change
   before the demo.
3. In the camera settings, turn on RTSP (sometimes listed as ONVIF) if
   there is a switch for it. Note the camera's username and password.
4. Find the RTSP URL format in the camera manual. Two common formats:
   - Hikvision: `rtsp://user:pass@192.168.1.64:554/Streaming/Channels/101`
   - Dahua: `rtsp://user:pass@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`

   For other brands, search for "<camera model> RTSP URL".
5. **Test the URL in VLC first:** Media > Open Network Stream, then paste
   the URL. If VLC can't play it, UniVerse can't either.
6. On the dashboard Cameras page (as admin), click **Add Camera** and use
   the RTSP URL as the stream source. The dashboard hides the camera
   password in every response; to change it later, **Edit** the camera
   and type the full URL again.
7. Click **Monitoring** on the new camera, tick the analyses you want,
   and click **Start monitoring**.

An IP camera accepts several connections at once, unlike a USB webcam,
so several analyses (for example camera health, people/restricted area,
and tamper detection) can run on it together. Live View shows one of
them: a detection script's annotated video takes priority over camera
health's raw video, and otherwise the first one started keeps the view.
The others print `camera N's live view is coming from another script` in
Script output, which is expected.

From a terminal, put the URL in **single quotes**; PowerShell treats `&`
in a URL as a command separator without them:

```powershell
python -m app.ai.prototypes.camera_health --source 'rtsp://user:pass@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0' --camera-id 3
```

Monitoring started from the dashboard uses the stream source saved on
the Cameras page. A terminal script uses the `--source` you pass it.

---

## Daily start

PostgreSQL starts with Windows, so you only start the rest:

| Terminal | Commands |
|---|---|
| 1. Backend | `cd D:\UniVerse\backend` then `venv\Scripts\Activate.ps1` then `python -m uvicorn app.main:app --reload` |
| 2. Dashboard | `cd D:\UniVerse\frontend` then `npm run dev` |
| 3+. AI scripts (optional) | Only if you run scripts yourself (Step 7): `cd D:\UniVerse\backend` then `venv\Scripts\Activate.ps1` then one script per terminal |

Then start monitoring for each camera from the dashboard (Step 6).
Monitoring stops whenever the backend stops, so start it again after a
backend restart.

Press `Ctrl+C` in a terminal to stop it, or `q` in an AI script's window.

### After `git pull`

Someone may have added packages or database changes. Run this after
every pull, then restart the backend and the dashboard:

```powershell
cd D:\UniVerse\backend
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
cd ..\frontend
npm install
```

## Check that everything works

Run these before you push changes.

Backend (from `backend\`, with the venv active and PostgreSQL running):

```powershell
python -m pytest
python -m ruff check app tests
python -m ruff format --check app tests
```

`pytest` must end with `passed` and no `failed`. The tests use their own
`universe_test` database and never touch your dev data.

Dashboard (from `frontend\`). Windows PowerShell 5.1 does not support
`&&`, so use `;`:

```powershell
npm run build; npm run lint
```

To try the API by hand, import `http://127.0.0.1:8000/openapi.json` into
Postman, or use the `curl` examples in
[`api-reference.md`](api-reference.md).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded because running scripts is disabled on this system` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (Step 1), then try again. |
| `py` is not recognized, or `python` opens the Microsoft Store | Reinstall Python 3.12 and tick "Add python.exe to PATH". Also open Settings > Apps > Advanced app settings > App execution aliases and turn off `python.exe` and `python3.exe`. |
| `pip install` fails with `OSError: [Errno 2] No such file or directory: '...\torch\include\...'` and a hint about "Long Path support" | The project folder's path is too long for Windows. Move the clone to a short path such as `D:\UniVerse`, or enable long paths (see Step 2), then delete `venv` and redo Step 4.1. |
| `password authentication failed for user "postgres"` | The password is wrong. Use the one you set in Step 1, both in `psql` and in `DATABASE_URL`. |
| `RuntimeError: DATABASE_URL is not set in the environment (.env)` | `backend\.env` is missing, or you aren't in `backend\`. Do Step 4.2. |
| `RuntimeError: JWT_SECRET must be at least 32 bytes long` | Generate a secret as shown in Step 4.2 and paste it into `JWT_SECRET`. |
| `ModuleNotFoundError: No module named 'fastapi'` (or any other package) | The venv isn't active; the prompt has no `(venv)`. Run `venv\Scripts\Activate.ps1` from `backend\`. |
| `ModuleNotFoundError: No module named 'app'` | Run scripts from `backend\` as `python -m app.ai.prototypes.<script>`, not by file path. |
| `relation "users" does not exist` | The tables weren't created. Run `alembic upgrade head`. |
| `[WinError 10048]` or "address already in use" on port 8000 | Another backend is already running. Close that terminal first. |
| Sign-in fails with a network error | Check that the backend terminal is running, and that the dashboard is on `http://localhost:5173` (see Step 5). After you change `CORS_ORIGINS`, restart the backend. |
| Every dashboard action takes about 2 seconds | `frontend\.env` uses `localhost`. Change it to `127.0.0.1`, then restart `npm run dev`. On Windows, `localhost` tries IPv6 first, and the backend doesn't listen on IPv6. |
| Suddenly back on the sign-in page | Your login expired (after 8 hours) or someone changed `JWT_SECRET`. Sign in again. |
| `RuntimeError: Could not open video source: 0` | Another app or script is using the webcam, or the index is wrong (try `1`). Also check Windows Settings > Privacy & security > Camera > "Let desktop apps access your camera". |
| `--camera-id given but no credentials: ...` | Set `UNIVERSE_API_USERNAME` and `UNIVERSE_API_PASSWORD` in `backend\.env`. |
| `user 'operator' may not read face embeddings: ...` | Face recognition needs the `ai_service` account. Set `UNIVERSE_API_USERNAME=ai_service` and `UNIVERSE_API_PASSWORD=ai_service123` in `backend\.env`, and run `python -m app.db.seed` if that account doesn't exist yet. |
| Live View says "No live feed" while a script is running | Only scripts started with `--camera-id` stream, and only to that camera's tile. Check that the ID matches the tile. |
| Dashboard says "The camera is busy" under **Use camera** | An AI script is using the webcam. Stop it, or upload photos instead. |
| A registered person still shows as "Unknown" | Add more photos (different angles, good light), or lower the Match threshold a little on the Settings page and restart the script. |
| A script with `--camera-id` stops at start with a 404 error | No camera has that ID. Check the ID column on the Cameras page. |
| `RuntimeError: No face captured -- make sure exactly one face is visible to the camera.` | Improve the light, face the camera, and make sure nobody else is in view. |
| `face_recognition` takes minutes to start the first time | It is downloading the model (about 300 MB). This happens only once. |
| The RTSP camera works in the brand app but not in VLC or UniVerse | RTSP is off, the URL format is wrong for that model, or the PC is on a different network. Check Step 9, points 1-5. |
| Monitoring shows "stopped with error" | Read the last lines of Script output in the Monitoring dialog. `Could not open video source` means the camera is busy (close other apps, stop other monitoring on that webcam) or the stream source is wrong (Edit the camera). |

## Rules for the team

- Never commit `.env`, `backend/media/` (evidence photos and face
  thumbnails), `face_db/`, or model files (`*.pt`). `.gitignore` already
  excludes them. Don't force-add them.
- The seed passwords (`admin123`, `operator123`, `ai_service123`) are
  public in this repository. Use them only on your own PC. For the demo,
  sign in as admin, open **Users**, create accounts with strong passwords
  (the AI scripts need one with the **AI service** role, set in
  `backend\.env`), and reset or deactivate the seed accounts. Everyone can
  change their own password on the **Profile** page (user menu > My
  profile).
- Get a person's consent before you register their face.
- After a change that someone else will pull, run the checks in
  [Check that everything works](#check-that-everything-works).

## Linux / macOS

The steps are the same, with these differences:

- Create the venv with `python3.12 -m venv venv` and activate it with
  `source venv/bin/activate`.
- Create the database with `createdb -U postgres universe_dev`.
- Use `cp` instead of `Copy-Item`, and any editor instead of `notepad`.
- Skip the `Set-ExecutionPolicy` step.
- `localhost` works normally, but `127.0.0.1` is fine too.
