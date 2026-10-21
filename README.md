# CS Tracker

A local course dashboard for University of Washington CSE students. Bring public course schedules, assignments, exams, and class materials into one workspace, with your notes and progress saved on your own device.

**Status:** working prototype, verified against CSE 123, 311, 351, 331, 332, and 312 for Autumn 2026. Runs with Python on Windows, macOS, and Linux; a standalone Windows x64 installer is built by GitHub Actions. Mobile installers are not included.

## Features

- Defaults to the current UW quarter using the official academic calendar; selects the upcoming quarter during breaks.
- Adds past and future courses by course code, quarter, and year.
- Imports deadlines, exams, and links to slides, readings, recordings, the syllabus, and Gradescope from supported public course pages.
- Includes exam times and locations when explicitly published in supported calendars or bounded linked exam/syllabus pages, with source links.
- Provides a current-courses dashboard, combined agenda, and searchable materials library.
- Includes a local UW Seattle CS BS planner with a course map, personalized suggestions, degree progress, and future-quarter plans.
- Searches all 75 mapped courses from any map view, including courses you have not taken.
- Uses current-quarter enrollments provisionally for future planning and labels in-progress fundamental requirements.
- Automatically counts approved completed natural science courses toward the five-credit CS science requirement.
- Includes light, dark, and device-controlled themes, with your preference saved locally across restarts.
- Saves personal completion checkboxes and course notes in SQLite.
- Optionally analyzes the two most recent PDF slide decks when importing a course; other decks can be analyzed individually.
- Flags slide passages mentioning deadlines, assignments, exams, or announcements, with page references for review.
- Supports Undo for the last 20 course-removal, assignment-completion, and planner changes, saved across restarts.
- Automatically refreshes current-quarter courses every 30 minutes while the app runs, with a course-update history.
- Preserves saved data when refreshes fail, highlights changed dates, and supports JSON backup export/import.

No account, hosted database, analytics, or AI API key is required.

## Install the Windows app

**[Download the latest Windows installer](https://github.com/sanyalarindam/UWCS-Course-Tracker/releases/latest)** — standalone desktop app; no separate Python installation needed.

1. Open [GitHub Releases](https://github.com/sanyalarindam/UWCS-Course-Tracker/releases/latest).
2. Download **CS-Tracker-Setup-VERSION-Windows-x64.exe** from the release assets.
3. Run Setup, then open **CS Tracker** from the Start menu. An optional desktop shortcut is available. The app, taskbar window, Start menu shortcut, and installer use the purple W app icon.

The installer includes Python and the required libraries; you do not need Python, Git, or a terminal to run the installed app. It opens in its own desktop window on Windows 10/11 x64. Setup checks/installs Microsoft Edge WebView2 Runtime using Microsoft's bootstrapper; internet access may be needed. The initial installer is not code-signed, so Windows may display an unrecognized-app warning. Release assets include **SHA256SUMS.txt** for checksum verification.

Each Windows user has a separate workspace at `%LOCALAPPDATA%/UWCS Tracker`. Updates and uninstall preserve this data; export a backup before moving to another device. Existing source-based workspaces using that default folder are reused. A development workspace started with `--data-dir` remains separate: export/import its backup to move it into the installed app. Closing the desktop window stops the local server and automatic refresh.

### Update an existing installation

Close CS Tracker, download the latest installer, and run it over the existing installation. The installer keeps the same application identity and preserves your local workspace. Releases from **v0.2.2** onward include the purple W logo in the executable, app window/taskbar, Start menu and desktop shortcuts, and Setup. Reinstalling an older release will not add the new icon.

The data folder retains its original `UWCS Tracker` name for compatibility; the installed app and shortcuts are named **CS Tracker**.

### Build the Windows installer

On Windows with Python 3.12 and [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-desktop.txt
.\packaging\build-windows.ps1
```

The build creates `dist/CS Tracker/CS Tracker.exe` and `dist/installer/CS-Tracker-Setup-0.2.0-Windows-x64.exe`. It smoke-tests the bundled server, planner data, and UI assets before compiling Setup. The WebView2 bootstrapper is downloaded from Microsoft and its Authenticode signature is verified before inclusion. Only app source, UI, and catalog/calendar snapshots are bundled; local workspaces, cached slides, backups, and credentials are excluded.

The **Windows installer** workflow runs on relevant pushes to `main` or manual dispatch. It tests the app, packages it, uploads a workflow artifact, and publishes a versioned GitHub release with the installer and checksums. The workflow uses a fresh Windows runner and does not upload local development data. macOS/Linux users can still run the source version below; installers for those platforms are not provided yet.

## Run from source

Install **Python 3.10 or newer** and Git, then run:

```sh
git clone https://github.com/sanyalarindam/UWCS-Course-Tracker.git
cd UWCS-Course-Tracker
python -m pip install --target .deps -r requirements.txt
python app.py
```

On macOS/Linux, use `python3` if needed. The app opens in your default browser. Its server listens only on `127.0.0.1`, using an available local port. Keep the terminal open while using it; press **Ctrl+C** to stop.

After installing dependencies, Windows users can double-click **launch.bat**. On macOS/Linux, run `sh launch.sh`.

### Try a course

New workspaces start with **no courses**. The course chooser is a list of available options, not a preloaded schedule. Courses are fetched and saved only after you explicitly import them. Existing workspaces retain courses you previously chose; restarting does not erase your selections.

1. Click **Add a course**.
2. Select one of the six course options, or type another CSE code. Nothing is selected by default.
3. Confirm the quarter and year; the current UW quarter is the default.
4. Keep recent-slide analysis selected if you want local PDF analysis during import, then choose **Find & import**.
5. Open the course dashboard for its agenda, materials, slide findings, syllabus snippets, and private notes.
6. Use **Refresh course** to check the public page again.

Before importing, the app checks [UW's public quarter offerings](https://www.washington.edu/students/timeschd/pub/AUT2026/cse.html) and, when needed, the [CSE course catalog](https://www.washington.edu/students/crscat/cse.html). Unknown codes and courses not offered in the selected quarter are rejected without creating a course card. A course that is listed but has a missing public website receives a separate error. If the quarter list is unpublished or cannot be verified, the app says so and does not add the course. Failed refreshes retain existing course data.

Import errors remain visible in the chooser and link to the official listing used for the decision. Successful listing lookups are cached for 15 minutes within the running app; network failures are not cached. Historical offerings can be confirmed by their quarter list even if a course is no longer in the current catalog.

### Verified imports

Live checks and minimized regression fixtures cover these Autumn 2026 pages. Counts reflect their published schedules when tested, not a promise that future offerings share the same layout.

| Course | Agenda items | Materials | Calendar format |
| --- | ---: | ---: | --- |
| CSE 123 | 8 | 40 | Numeric dates and assignment spans |
| CSE 311 | 11 | 104 | Configuration-based navigation and a linked month grid |
| CSE 351 | 68 | 26 | Separate schedule with homework, readings, labs, and quizzes |
| CSE 331 | 14 | 9 | Linked month grid with assignments and exams |
| CSE 332 | 17 | 37 | Date attributes and explicit assignment markers |
| CSE 312 | 11 | 90 | Lecture-by-lecture calendar |

CSE 123 project due dates use the final dated row of each assignment span and the stated submission time. Computer-quiz signup windows are not turned into deadlines. Review sessions are not treated as exams. Unpublished links do not prevent importing explicitly listed future deadlines; those entries link back to the source calendar.

Only publicly linked materials are discovered. The tested CSE 351 schedule supplies reading references and the CSE 331 calendar supplies lecture-page links; neither exposes direct PDF slide links in the imported calendar. Local PDF analysis was verified for the linked decks in CSE 123, 311, 332, and 312.

### Plan future courses

Open **Course planner** in the sidebar. It defaults to **UW Seattle Computer Science BS** with an empty history and plan.

1. Expand **Course history & interests**, enter completed courses and optional grades, and choose your interests.
2. Select a course in the **Course map** to inspect required AND/OR groups, minimum grades, recommended preparation, official catalog text, and downstream courses.
3. Start with **My course path**, showing only completed, current, and planned courses. Use **Classes taken only** or **Future classes (planned)** for smaller views. **Explore core pathways**, search, and **Show connections** let you expand the map when needed. Personal views keep other prerequisite nodes hidden; full AND/OR rules remain in the selected course checklist. **Find a course** always searches the entire catalog, including courses you have not taken or planned. Results open their prerequisite details automatically; use **Clear search** to return to the selected map view.
4. Choose **Plan into** and add courses to future quarters. Remove an entry before moving it to a different quarter.
5. Review prerequisite conflicts and **Degree progress**. Import a schedule separately when its quarter is published.

The bundled catalog snapshot contains 75 courses and supporting prerequisite nodes, sourced from the [UW CSE catalog](https://www.washington.edu/students/crscat/cse.html), [CS degree requirements](https://www.washington.edu/students/gencat/program/S/ComputerScience-210.html), and [core list](https://www.cs.washington.edu/academics/undergraduate/degree-requirements/courses/). Each course links to its official source. Interest tags and ranking are app-defined. This snapshot is curated, not a live catalog sync; external and unmodeled courses explicitly require a catalog check.

Completed history is self-reported, separate from assignment checkboxes and imported schedules. Future-quarter suggestions and course-map readiness provisionally include imported courses from the current UW quarter, with successful-completion assumptions shown. They do not increase degree progress or change completed history. Later planned quarters also consider valid earlier plans, with those assumptions shown. Same-quarter prerequisites do not qualify. Minimum grades are checked where modeled; missing grades prompt review. A tentative plan never confirms an offering, registration eligibility, or seat availability.

Checkpoints cover fundamentals, math routes, core counts, upper-level core counts, additional core/capstone, selected elective credits, and natural science credits calculated from recorded courses plus other self-reported approved credits. They do not replace a degree audit: general education, total degree credits, GPA, admission restrictions, substitutions, section-specific rules, and adviser approvals are not evaluated. Variable-credit courses need actual approved credits entered separately. History, interests, and plans are stored locally and included in JSON backups; importing a backup with planner data replaces the planner profile and plan. Older backups preserve existing planner data.

### Understand degree progress

Degree progress counts **completed courses recorded in your history**, rather than inferring credit from advanced courses or imported schedules.

- **Mathematics · either route** shows separate progress for the standard route (MATH 124, 125, 126, 208) and honors route (MATH 134, 135, 136). You need one complete route, not both.
- **2/4** means two qualifying courses from the four-course route are recorded. For example, entering MATH 126 and MATH 208 does not automatically add MATH 124 and MATH 125.
- If UW awarded specific course equivalents for AP, IB, or transfer credit, you can manually record those equivalent UW courses in your history. The app does not import transcripts or calculate equivalencies. Leave the optional grade blank when there is no numeric grade; the app will flag minimum-grade requirements for review.
- Placement into a higher course alone does not establish credit for earlier courses. Substitutions and exceptions need adviser confirmation and are not automatically recognized by the tracker.
- Recorded math and fundamental courses with grades below 2.0 do not satisfy their checkpoints. Blank grades count provisionally and require review.

**Example:** If you recorded MATH 126 and MATH 208, the tracker shows **2/4**. If your UW record also awards credit for MATH 124 and MATH 125, enter those equivalents to reflect that history; the tracker then shows **4/4**. This is a record of your entries, not an official degree-audit result.

### Record natural science courses

Open **Course planner → Course history & interests → Completed courses**, enter a course code and optional grade, then click **Add / update**. No schedule import is needed for completed science courses.

Add PHYS 121 or 141, CHEM 142/143/145, BIOL 180, or awarded BIOL 162 AP credit through **Completed courses**. They automatically contribute to the CS natural science requirement. PHYS 116 and PHYS 119 count only when both are completed. Removing a completion removes its contribution; failed courses do not count. Progress is capped at the required five credits.

Use **Other approved natural science credits** for adviser-approved credit outside these options, excluding courses already recorded. Previously entered manual science credits are preserved. The [official CS science list](https://www.cs.washington.edu/academics/undergraduate/degree-requirements/courses/) is narrower than UW's general Natural Sciences designation.

Degree progress separates completed, in-progress, and planned courses. It lists counted core and elective courses, missing math/fundamental courses, remaining core/upper-level requirements, and science credits from recorded courses versus manual entries. Current and planned courses do not increase completed requirement totals.

### Understand core-course counts

CSE 331 appears on UW's general core-course list with an exception: for **Computer Science BS**, it fulfills a required fundamental and does **not** also count toward the six additional core courses or elective credits. Recording CSE 331 can therefore increase Fundamentals while leaving Core courses at 0/6. The planner follows that CS-specific exception.

### Plan around courses in progress

Import your current-quarter course schedules under **Current courses**, then select a future quarter in the planner. A course can show **Ready after current courses** when its prerequisites include your current enrollments. For example, CSE 312 in progress can satisfy that prerequisite provisionally for a later CSE 446 plan, provided its other prerequisites are met.

In **Degree progress**, a current fundamental such as CSE 312 displays a clock symbol and **In progress** badge instead of an empty circle. It does not increase the completed count until you record completion.

These checks assume successful completion, including any required minimum grade. They do not mark the current course completed or increase degree progress. Current-quarter courses do not satisfy prior-course prerequisites for plans in that same quarter. **Offering unverified** means the plan has not established that the course will be offered in that quarter; schedule imports still run the separate offering check.

### Optional desktop window

For a separate application window, install pywebview:

```sh
python -m pip install pywebview
python app.py --desktop
```

pywebview may require web-engine dependencies on your operating system. This optional mode has not been verified on every platform. Browser mode works without it.

## Undo and automatic refresh

Use **Undo** in the top bar to reverse the latest course removal, assignment checklist change, or planner history/preferences/plan change. Undo restores removed courses with their notes; existing assignment completion marks are retained. The last 20 actions survive restarts. Imports, refreshes, backup restores, notes, appearance changes, and automatic-refresh settings are not undoable. Importing a backup clears undo history so older actions cannot overwrite restored data. Undo refuses to overwrite a removed course that has since been added again.

Automatic refresh is enabled by default. While the local app is running, it checks imported **current-quarter** courses every 30 minutes, beginning within a minute of startup when due. Past and future courses remain manual. Disable it in **Local settings → Automatic course refresh**. Refreshing does not run PDF analysis or mark work complete.

Open **Course updates** in the top bar for new agenda items, changed dates/exam times/locations, removed listings, new materials, and refresh errors. The latest 20 course reports are stored locally. Failed refreshes keep saved course data, notes, and completions. Update notifications poll every 30 seconds while the browser tab is visible; open Course updates to retrieve the latest state. Editors are not automatically replaced while you are working in a course or planner. The app must remain running; this is not an operating-system background service.

## Privacy and local storage

Each installation stores its own workspace. Default data locations:

| Platform | Data folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%/UWCS Tracker` |
| macOS | `~/Library/Application Support/UWCS Tracker` |
| Linux | `$XDG_DATA_HOME/uwcs-tracker`, or `~/.local/share/uwcs-tracker` |

This folder contains `tracker.sqlite3` and a `slides/` cache of analyzed PDFs. Override it with `--data-dir PATH` or the `UWCS_DATA_DIR` environment variable.

- Saved agenda entries, notes, completion marks, and findings work offline while the app runs.
- Refreshing pages and downloading uncached materials requires internet access and contacts public UW websites.
- Slide analysis runs locally using PDF text extraction and keyword matching. Documents are not sent to an AI service.
- Protected Canvas, Gradescope, and NetID content is not imported. Links can still open these services in your browser.
- Completion checkboxes are your personal checklist; they do not verify assignment submissions.

Use **Local settings > Export backup** to move courses, notes, progress, and findings to another installation. **Import backup** merges the JSON into the destination workspace and updates matching courses. Downloaded PDFs are not included in JSON backups.

Dependencies, local databases, generated files, and workspace backups are excluded from Git.

## Quarter detection

Quarter boundaries come from the [official UW academic calendar summary](https://www.washington.edu/students/reg/begendcal.html), from instruction start through the end of finals. During breaks, the next quarter becomes the default. You can override the quarter and year when adding a course.

A calendar snapshot downloaded October 20, 2026 supports offline startup. Refresh it in **Local settings**. The app uses Seattle's date for quarter detection and deadline comparisons. A due time is shown only when explicitly extracted; otherwise, the agenda says **Time unspecified**.

## Stack and structure

Python serves a browser interface built with JavaScript, HTML, and CSS. SQLite stores the workspace, Beautiful Soup parses HTML, and pypdf extracts slide text. No Node build step, cloud backend, or Rust toolchain is required.

```text
app.py                   Local server, background import jobs, and launcher
tracker/
  importer.py            Course discovery, calendar parsing, PDF analysis
  courses.py             Course choices, linked-page discovery, layout adapters
  availability.py        Official catalog and quarter-offering validation
  store.py               SQLite persistence and workspace backups
  planner.py             Prerequisite logic, suggestions, and requirement progress
web/                     Dashboard interface and styles
data/calendar.json       Official UW calendar snapshot
data/planner.json        Curated, source-linked planning catalog
tests/                   Importer, persistence, PDF, and HTTP tests
  fixtures/              Public HTML snapshots for repeatable tests
requirements.txt         Python dependencies
launch.bat / launch.sh   Platform launch shortcuts
```

Installed dependencies live in `.deps/`. A development workspace can live in `.local-data/`. Both are local-only and ignored by Git; on this Windows workspace they are also hidden to keep the project view tidy.

## Development and verification

```sh
python -B -m unittest discover -s tests -v
python -B app.py --no-browser --port 8765 --data-dir .local-data
```

With Node.js installed, you can also check JavaScript syntax:

```sh
node --check web/app.js
node --check web/planner.js
node --test tests/theme.test.cjs
```

The 41 Python tests and five JavaScript theme tests cover course existence and quarter availability, missing websites, unpublished listings, network failures, empty startup, explicit course selection, all six calendar formats, quarter and break boundaries, mismatched offerings, URL restrictions, completion persistence across date changes, backups, failed refresh preservation, slide page references, local HTTP request protections, saved appearance preferences, planner API persistence, AND/OR prerequisites, minimum grades, recommended preparation, quarter ordering, requirement counts, suggestion exclusions, and planner backups.

The app has been checked on Windows against all six live Autumn 2026 course pages and real linked PDF slides. Validation imports run in an isolated workspace and are never seeded into the user's dashboard. macOS/Linux and source-based desktop mode still need additional platform testing.

Exam logistics are extracted from explicit calendar entries and up to three same-offering linked HTML exam/syllabus pages. Missing or conflicting details remain unspecified; lecture rooms are not assumed to be exam rooms. Refresh existing courses to retrieve newly published exam details. PDF-only exam logistics are not automatically extracted by this importer.

## Current limitations

- Discovery constructs the standard CSE course/quarter URL and verifies its title. Alternate URLs and general web search are not implemented.
- The parser supports the six tested layouts, including bounded discovery of linked calendar pages and CSE 311's declared navigation configuration. Other websites may need dedicated parsers; unsupported schedules are flagged for review.
- Slide analysis uses text extraction and keyword matching, not semantic AI analysis. Image-only slides, diagrams, and OCR are not supported. Scans can miss information; findings do not automatically become deadlines.
- Syllabus rules appear as policy snippets. Recurring concept-check deadlines are not inferred.
- Current-quarter refreshes run automatically while the app is running; other quarters use manual refresh. Operating-system background refresh, push notifications, automatic device sync, and signed installers are future work.

UWCS Tracker is an independent student project and is not affiliated with the University of Washington. Check original course materials for authoritative deadlines.
