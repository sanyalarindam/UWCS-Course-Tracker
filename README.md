# UWCS Tracker

A local course dashboard for University of Washington CSE students. Bring public course schedules, assignments, exams, and class materials into one workspace, with your notes and progress saved on your own device.

**Status:** working prototype, verified against CSE 312 Autumn 2026. Runs with Python on Windows, macOS, and Linux; a packaged installer and mobile app are not included yet.

## Features

- Defaults to the current UW quarter using the official academic calendar; selects the upcoming quarter during breaks.
- Adds past and future courses by course code, quarter, and year.
- Imports deadlines, exams, and links to slides, readings, recordings, the syllabus, and Gradescope from supported public course pages.
- Provides a current-courses dashboard, combined agenda, and searchable materials library.
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

1. Click **Add a course**.
2. Enter **CSE 312**, **Autumn**, **2026**, or another supported offering.
3. Keep recent-slide analysis selected if you want local PDF analysis during import.
4. Open the course dashboard for its agenda, materials, slide findings, syllabus snippets, and private notes.
5. Use **Refresh course** to check the public page again.

The CSE 312 test snapshot imports **9 problem-set deadlines, 2 exams, and 90 linked materials**. If a future course page returns 404, the course is saved with an unavailable-schedule message so you can retry later.

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
  store.py               SQLite persistence and workspace backups
web/                     Dashboard interface and styles
data/calendar.json       Official UW calendar snapshot
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
```

The eight automated tests cover real course extraction, quarter and break boundaries, mismatched offerings, URL restrictions, completion persistence across date changes, backups, failed refresh preservation, slide page references, and local HTTP request protections.

The app has been checked on Windows against the live CSE 312 course page and real PDF slides. macOS/Linux and optional pywebview mode still need platform testing.

## Current limitations

- Discovery constructs the standard CSE course/quarter URL and verifies its title. Alternate URLs and general web search are not implemented.
- The parser supports CSE 312's calendar layout and a limited table fallback. Other websites may need dedicated parsers; unsupported schedules are flagged for review.
- Slide analysis uses text extraction and keyword matching, not semantic AI analysis. Image-only slides, diagrams, and OCR are not supported. Scans can miss information; findings do not automatically become deadlines.
- Syllabus rules appear as policy snippets. Recurring concept-check deadlines are not inferred.
- Course refreshes are manual. Scheduled refreshes, notifications, automatic device sync, and signed installers are future work.

UWCS Tracker is an independent student project and is not affiliated with the University of Washington. Check original course materials for authoritative deadlines.
