# UWCS Tracker

A local course dashboard for University of Washington CSE students. Bring public course schedules, assignments, exams, and class materials into one workspace, with your notes and progress saved on your own device.

**Status:** working prototype, verified against CSE 123, 311, 351, 331, 332, and 312 for Autumn 2026. Runs with Python on Windows, macOS, and Linux; a packaged installer and mobile app are not included yet.

## Features

- Defaults to the current UW quarter using the official academic calendar; selects the upcoming quarter during breaks.
- Adds past and future courses by course code, quarter, and year.
- Imports deadlines, exams, and links to slides, readings, recordings, the syllabus, and Gradescope from supported public course pages.
- Provides a current-courses dashboard, combined agenda, and searchable materials library.
- Includes a local CS BS course planner with a prerequisite web, interest-based suggestions, requirement checkpoints, and future-quarter plans.
- Includes light, dark, and device-controlled themes, with your preference saved locally across restarts.
- Saves personal completion checkboxes and course notes in SQLite.
- Optionally analyzes the two most recent PDF slide decks when importing a course; other decks can be analyzed individually.
- Flags slide passages mentioning deadlines, assignments, exams, or announcements, with page references for review.
- Preserves saved data when refreshes fail, highlights changed dates, and supports JSON backup export/import.

No account, hosted database, analytics, or AI API key is required.

## Quick start

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
5. Review prerequisite conflicts and the **Degree progress**. Import a schedule separately when its quarter is published.

The bundled catalog snapshot contains 66 courses and supporting prerequisite nodes, sourced from the [UW CSE catalog](https://www.washington.edu/students/crscat/cse.html), [CS degree requirements](https://www.washington.edu/students/gencat/program/S/ComputerScience-210.html), and [core list](https://www.cs.washington.edu/academics/undergraduate/degree-requirements/courses/). Each course links to its official source. Interest tags and ranking are app-defined. This snapshot is curated, not a live catalog sync; external and unmodeled courses explicitly require a catalog check.

Completed history is self-reported, separate from assignment checkboxes and imported schedules. Future-quarter suggestions and course-map readiness provisionally include imported courses from the current UW quarter, with successful-completion assumptions shown. They do not increase degree progress or change completed history. Later planned quarters also consider valid earlier plans, with those assumptions shown. Same-quarter prerequisites do not qualify. Minimum grades are checked where modeled; missing grades prompt review. A tentative plan never confirms an offering, registration eligibility, or seat availability.

Checkpoints cover fundamentals, math routes, core counts, upper-level core counts, additional core/capstone, selected elective credits, and self-reported approved science credits. They do not replace a degree audit: general education, total degree credits, GPA, admission restrictions, substitutions, section-specific rules, and adviser approvals are not evaluated. Variable-credit courses need actual approved credits entered separately. History, interests, and plans are stored locally and included in JSON backups; importing a backup with planner data replaces the planner profile and plan. Older backups preserve existing planner data.

### Optional desktop window

For a separate application window, install pywebview:

```sh
python -m pip install pywebview
python app.py --desktop
```

pywebview may require web-engine dependencies on your operating system. This optional mode has not been verified on every platform. Browser mode works without it.

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

The 31 Python tests and five JavaScript theme tests cover course existence and quarter availability, missing websites, unpublished listings, network failures, empty startup, explicit course selection, all six calendar formats, quarter and break boundaries, mismatched offerings, URL restrictions, completion persistence across date changes, backups, failed refresh preservation, slide page references, local HTTP request protections, saved appearance preferences, planner API persistence, AND/OR prerequisites, minimum grades, recommended preparation, quarter ordering, requirement counts, suggestion exclusions, and planner backups.

The app has been checked on Windows against all six live Autumn 2026 course pages and real linked PDF slides. Validation imports run in an isolated workspace and are never seeded into the user's dashboard. macOS/Linux and optional pywebview mode still need platform testing.

## Current limitations

- Discovery constructs the standard CSE course/quarter URL and verifies its title. Alternate URLs and general web search are not implemented.
- The parser supports the six tested layouts, including bounded discovery of linked calendar pages and CSE 311's declared navigation configuration. Other websites may need dedicated parsers; unsupported schedules are flagged for review.
- Slide analysis uses text extraction and keyword matching, not semantic AI analysis. Image-only slides, diagrams, and OCR are not supported. Scans can miss information; findings do not automatically become deadlines.
- Syllabus rules appear as policy snippets. Recurring concept-check deadlines are not inferred.
- Course refreshes are manual. Scheduled refreshes, notifications, automatic device sync, and signed installers are future work.

UWCS Tracker is an independent student project and is not affiliated with the University of Washington. Check original course materials for authoritative deadlines.
