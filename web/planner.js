/* Interactive prerequisite graph and local, explainable course planning. */
(() => {
  const escape = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const label = (code) => code.replace(/^([A-Z]+)(\d)/, "$1 $2");
  let state,
    helpers,
    selected = "CSE311",
    graphMode = "mine",
    search = "",
    target = "",
    profileOpen = false,
    busy = false;
  let positions = new Map(),
    dimensions = { width: 1280, height: 600 };
  const corePath = new Set([
    "CSE123",
    "CSE143",
    "CSE311",
    "CSE312",
    "CSE331",
    "CSE332",
    "CSE351",
    "CSE333",
    "CSE344",
    "CSE421",
    "CSE446",
    "CSE451",
    "CSE452",
    "CSE473",
    "CSE484",
    "MATH126",
    "MATH208",
  ]);
  const byCode = () =>
    new Map(state.planner.courses.map((course) => [course.code, course]));
  const termKey = (t) => `${t.quarter} ${t.year}`;
  const termIndex = (t) =>
    t.year * 4 + ["Winter", "Spring", "Summer", "Autumn"].indexOf(t.quarter);
  const sourceLink = (url, text) =>
    `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(text)} ↗</a>`;

  function futureTerms() {
    const first = state.term || {
      quarter: "Autumn",
      year: Number(state.today.slice(0, 4)),
    };
    const result = [];
    for (let i = 1; i <= 12; i++) {
      const n = termIndex(first) + i;
      result.push({
        quarter: ["Winter", "Spring", "Summer", "Autumn"][n % 4],
        year: Math.floor(n / 4),
      });
    }
    for (const p of state.planner.plan)
      if (!result.some((t) => termKey(t) === termKey(p)))
        result.push({ quarter: p.quarter, year: p.year });
    return result.sort((a, b) => termIndex(a) - termIndex(b));
  }

  function depth(code, seen = new Set()) {
    if (seen.has(code)) return 0;
    const course = byCode().get(code);
    if (!course) return 0;
    const next = new Set([...seen, code]);
    const parents = course.prerequisites
      .flatMap((g) => g.any_of)
      .filter((c) => byCode().has(c));
    return parents.length
      ? Math.min(5, 1 + Math.max(...parents.map((p) => depth(p, next))))
      : 0;
  }

  function graphCourses() {
    const courses = state.planner.courses,
      map = byCode();
    const personal = ["mine", "taken", "future"].includes(graphMode);
    let visible = new Set(
      courses
        .filter((c) => {
          if (graphMode === "mine")
            return ["completed", "current", "planned"].includes(c.status);
          if (graphMode === "taken") return c.status === "completed";
          if (graphMode === "future") return c.status === "planned";
          if (graphMode === "all") return true;
          if (graphMode === "ready") return c.readiness.met;
          if (graphMode === "interests")
            return c.tags.some((t) =>
              state.planner.profile.interests.includes(t),
            );
          return corePath.has(c.code);
        })
        .map((c) => c.code),
    );
    if (graphMode === "focus") {
      visible = new Set([selected]);
      const visit = (code) => {
        const c = map.get(code);
        if (!c) return;
        for (const p of c.prerequisites.flatMap((g) => g.any_of))
          if (!visible.has(p)) {
            visible.add(p);
            visit(p);
          }
      };
      visit(selected);
      for (const code of map.get(selected)?.unlocks || []) visible.add(code);
    }
    if (search.trim()) {
      const query = search.trim().toLowerCase();
      return courses.filter(
        (c) =>
          `${label(c.code)} ${c.code} ${c.name}`
            .toLowerCase()
            .includes(query) ||
          c.code.toLowerCase().includes(query.replace(/\s+/g, "")),
      );
    }
    // Personal views stay limited to the user's courses; details retain full AND/OR rules.
    if (!personal && !search)
      for (const code of [...visible])
        for (const p of map.get(code)?.prerequisites.flatMap((g) => g.any_of) ||
          [])
          visible.add(p);
    return courses.filter((c) => visible.has(c.code));
  }

  function searchHint() {
    if (search.trim())
      return `${graphCourses().length} ${graphCourses().length === 1 ? "result" : "results"} from all courses · select a result to view prerequisites and plan it.`;
    return (
      {
        mine: "Your completed, current, and planned courses. Search above to add something new.",
        taken: "Only courses you recorded as completed.",
        future: "Only courses you added to your quarter plan.",
      }[graphMode] ||
      "Explore courses, then select one to see its prerequisites."
    );
  }
  function refreshMap() {
    const courses = graphCourses();
    if (!courses.some((c) => c.code === selected))
      selected = courses[0]?.code || "";
    document.querySelector("#planner-graph").innerHTML = graph();
    document.querySelector("#planner-detail").innerHTML = detail();
    document.querySelector("#planner-search-hint").textContent = searchHint();
    document.querySelector("#clear-course-search").hidden = !search;
    positionGraph();
  }

  function graph() {
    const courses = graphCourses(),
      rows = new Map();
    positions = new Map();
    const columns = [...new Set(courses.map((c) => depth(c.code)))].sort(
      (a, b) => a - b,
    );
    for (const course of courses.sort((a, b) => a.code.localeCompare(b.code))) {
      const column = columns.indexOf(depth(course.code));
      const row = rows.get(column) || 0;
      positions.set(course.code, { x: 24 + column * 252, y: 48 + row * 94 });
      rows.set(column, row + 1);
    }
    dimensions = {
      width: Math.max(1020, 48 + (Math.max(0, ...rows.keys()) + 1) * 252),
      height: Math.max(360, 70 + Math.max(0, ...rows.values()) * 94),
    };
    const edges = [];
    for (const course of courses) {
      const end = positions.get(course.code);
      for (const group of course.prerequisites)
        for (const code of group.any_of) {
          const start = positions.get(code);
          if (!start) continue;
          const x1 = start.x + 208,
            y1 = start.y + 32,
            x2 = end.x,
            y2 = end.y + 32;
          edges.push(
            `<path class="prereq-edge ${group.any_of.length > 1 ? "alternative" : ""} ${selected === course.code || selected === code ? "highlight" : ""}" d="M ${x1} ${y1} C ${x1 + 26} ${y1},${x2 - 26} ${y2},${x2} ${y2}" marker-end="url(#planner-arrow)"><title>${escape(label(code))} → ${escape(label(course.code))}${group.any_of.length > 1 ? " (one alternative)" : ""}</title></path>`,
          );
        }
      for (const code of course.recommended) {
        const start = positions.get(code);
        if (!start) continue;
        edges.push(
          `<path class="prereq-edge recommended" d="M ${start.x + 208} ${start.y + 32} C ${start.x + 240} ${start.y + 32},${end.x - 26} ${end.y + 32},${end.x} ${end.y + 32}"><title>${escape(label(code))} is recommended before ${escape(label(course.code))}; not a formal prerequisite</title></path>`,
        );
      }
    }
    return `<div class="planner-graph-viewport" tabindex="0" aria-label="Scrollable prerequisite web. Select a course to inspect prerequisites and next steps."><div class="planner-graph-canvas"><svg width="${dimensions.width}" height="${dimensions.height}" aria-hidden="true"><defs><marker id="planner-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 z" class="edge-arrow" /></marker></defs>${edges.join("")}</svg>${Array.from({ length: Math.max(0, ...rows.keys()) + 1 }, (_, i) => `<span class="graph-stage" data-stage="${i}">${`COURSE GROUP ${i + 1}`}</span>`).join("")}${courses.map((c) => `<button type="button" class="graph-node status-${c.status} ${selected === c.code ? "selected" : ""}" data-select-course="${c.code}" aria-pressed="${selected === c.code}" aria-label="${escape(label(c.code) + " " + c.name + "; " + statusLabel(c))}"><b>${escape(label(c.code))}<span class="node-status-dot" aria-hidden="true"></span></b><span>${escape(c.name)}</span></button>`).join("")}${courses.length ? "" : `<p class="empty">${search.trim() ? "No courses found. Try a course code or title." : "Nothing here yet. Add completed courses in Course history & interests, or search for a course to plan."}</p>`}</div></div>`;
  }

  function statusLabel(c) {
    return {
      completed: "Completed",
      current: "Imported in current quarter",
      planned: "In your future plan",
      ready: "Prerequisites met",
      review: "Check catalog prerequisites",
      blocked: "Prerequisites missing",
    }[c.status];
  }
  function missingText(readiness) {
    return readiness.missing
      .map((group) => group.map(label).join(" or "))
      .join("; and ");
  }
  function gradeWarning(r) {
    return r.grade_review.length
      ? `<p class="planner-caution">Grade check: ${r.grade_review
          .map(
            (g) =>
              g.any_of.map(label).join(" or ") +
              " needs at least " +
              g.minimum_grade.toFixed(1),
          )
          .map(escape)
          .join("; ")}. Add the grade to your history.</p>`
      : "";
  }

  function detail() {
    const c = byCode().get(selected);
    if (!c) return '<div class="empty">Select a course in the web.</div>';
    const completed = state.planner.profile.completed.find(
      (r) => r.code === c.code,
    );
    return `<aside class="planner-course-detail panel"><div class="planner-detail-head"><span class="course-code">${escape(label(c.code))}</span><span class="tag">${c.credits ?? "Variable"} credits</span><h2>${escape(c.name)}</h2><span class="planner-status status-${c.status}">${escape(statusLabel(c))}</span></div><div class="planner-detail-body"><h3>Before you take this course</h3>${c.prerequisites.length ? `<p class="note">Meet every group below; choose any one course within an “or” group.</p>${c.prerequisites.map((g) => `<div class="prereq-group">${g.any_of.map((code) => `<button type="button" class="prereq-chip ${state.planner.profile.completed.some((r) => r.code === code) ? "is-complete" : ""}" data-select-course="${code}">${escape(label(code))}</button>`).join('<span class="prereq-or">or</span>')}${g.minimum_grade ? `<small>Minimum ${g.minimum_grade.toFixed(1)}</small>` : ""}</div>`).join("")}` : `<p class="note">${c.external || !c.modeled ? "Prerequisites for this course are not modeled. Use its catalog link." : "No formal prerequisite listed; verify placement and prior experience."}</p>`}${gradeWarning(c.readiness)}${c.recommended.length ? `<h3>Recommended preparation</h3><p class="note">${c.recommended.map(label).map(escape).join(", ")}. Recommendations do not block your plan.</p>` : ""}<details class="prereq-source"><summary>Official prerequisite text</summary><p>${escape(c.prerequisite_text)}</p>${sourceLink(c.source, "Course catalog")}</details><h3>What you can take next</h3><div class="unlock-list">${c.unlocks.map((code) => `<button type="button" class="text-button" data-select-course="${code}">${escape(label(code))}</button>`).join("") || '<span class="note">No downstream courses mapped in this catalog.</span>'}</div><div class="planner-course-actions">${completed ? `<span class="note">Completed${completed.grade !== null ? " · grade " + completed.grade.toFixed(1) : " · grade not entered"}</span><button type="button" class="secondary" data-plan-action="uncomplete" data-code="${c.code}">Remove completion</button>` : `<button type="button" class="primary" data-plan-action="plan" data-code="${c.code}">Plan for ${escape(target)}</button><button type="button" class="secondary" data-plan-action="complete" data-code="${c.code}">Record as completed</button>`}<button type="button" class="text-button" data-plan-action="import" data-code="${c.code}" ${!c.code.startsWith("CSE") ? "disabled" : ""}>Import course schedule ↗</button></div></div></aside>`;
  }

  function profile() {
    const p = state.planner.profile;
    return `<details class="planner-profile panel" ${profileOpen ? "open" : ""}><summary>Course history & interests <span>${p.completed.length} completed · ${p.interests.length} interests</span></summary><div class="planner-profile-body"><div><h3>Completed courses</h3><p class="note">Only record courses you actually completed. Importing an assignment schedule does not mark a course complete. Optional grades help check minimum-grade prerequisites.</p><form id="planner-completed-form" class="history-form"><label class="visually-hidden" for="completed-code">Completed course</label><input id="completed-code" list="planner-catalog-options" placeholder="CSE 123, MATH 126…" required autocomplete="off"><datalist id="planner-catalog-options">${state.planner.courses.map((c) => `<option value="${escape(label(c.code))}">${escape(c.name)}</option>`).join("")}</datalist><label class="visually-hidden" for="completed-grade">Grade, optional</label><input id="completed-grade" type="number" min="0" max="4" step="0.1" placeholder="Grade (optional)"><button class="secondary" type="submit">Add / update</button></form><div class="history-chips">${p.completed.map((c) => `<span class="history-chip">${escape(label(c.code))}${c.grade !== null ? " · " + c.grade.toFixed(1) : ""}<button type="button" data-plan-action="uncomplete" data-code="${c.code}" aria-label="Remove completed ${escape(label(c.code))}">×</button></span>`).join("") || '<span class="note">Your course history is empty.</span>'}</div></div><form id="planner-profile-form"><label>Planning mode<select name="major"><option value="cs" ${p.major === "cs" ? "selected" : ""}>Computer Science BS · UW Seattle</option><option value="explore" ${p.major === "explore" ? "selected" : ""}>Explore without a degree plan</option></select></label><fieldset class="interest-options"><legend>Your interests</legend>${state.planner.interests.map((i) => `<label><input type="checkbox" name="interests" value="${i.id}" ${p.interests.includes(i.id) ? "checked" : ""}>${escape(i.label)}</label>`).join("")}</fieldset><div class="planner-credit-inputs"><label>Other approved elective credits<input name="other_elective_credits" type="number" min="0" max="150" value="${p.other_elective_credits}" required><small>Exclude credits already counted from your recorded courses.</small></label><label>Approved natural science credits<input name="science_credits" type="number" min="0" max="150" value="${p.science_credits}" required></label></div><label class="checkbox-label"><input name="capstone_confirmed" type="checkbox" ${p.capstone_confirmed ? "checked" : ""}>I have an adviser-confirmed completed capstone</label><button class="primary" type="submit">Save preferences</button></form></div></details>`;
  }

  function requirements() {
    const r = state.planner.requirements;
    if (state.planner.profile.major === "explore") return "";
    return `<details class="planner-requirements panel"><summary>Degree progress <span>Self-reported progress</span></summary><div class="requirement-grid"><div><h3>Fundamentals · ${r.fundamentals_done}/6</h3>${r.fundamentals.map((g) => `<p class="requirement-line ${g.done ? "is-complete" : ""}"><span>${g.done ? "✓" : "○"}</span>${g.any_of.map(label).map(escape).join(" or ")}</p>`).join("")}</div><div><h3>Core & electives</h3><p>${r.core_done}/6 core courses · ${r.upper_core_done}/4 at the CSE 400 level</p><p>${r.extra_core_or_capstone_done ? "✓" : "○"} One additional core course or a confirmed capstone</p><p>${r.elective_credits}/33 additional core/elective credits</p><p>${r.science_credits}/5 approved natural science credits</p></div><div><h3>Mathematics · either route</h3>${r.math_routes.map((route) => `<p>${route.done}/${route.courses.length}: ${route.courses.map(label).map(escape).join(", ")}</p>`).join("")}<p class="note">Math and fundamentals below 2.0 do not satisfy these checkpoints. Missing grades require review.</p></div></div><p class="note planner-scope">Based on the published UW CS general catalog and core-course list. This tracks selected major requirements, not general education, total degree credits, GPA, admission status, or an official graduation audit. ${r.variable_credit_review.length ? "Variable-credit courses need their actual section credits recorded under other approved elective credits. " : ""}${sourceLink(state.planner.sources.requirements, "Official degree requirements")} · ${sourceLink(state.planner.sources.core, "Core course list")}</p></details>`;
  }

  function suggestions() {
    return `<section><div class="section-title"><h2>Courses to consider</h2><small>Based on your history, CS requirements, and interests</small></div><div class="suggestion-grid">${
      state.planner.suggestions
        .slice(0, 6)
        .map((s) => {
          const c = byCode().get(s.code);
          return `<article class="suggestion-card panel"><button class="text-button suggestion-code" type="button" data-select-course="${c.code}">${escape(label(c.code))} →</button><h3>${escape(c.name)}</h3><span class="planner-status ${s.readiness.met ? "status-ready" : "status-blocked"}">${s.readiness.met ? "Prerequisites met" : "Prerequisites missing"}</span>${s.reasons.map((reason) => `<p class="suggestion-reason">${escape(reason)}</p>`).join("")}${s.readiness.missing.length ? `<p class="planner-caution">Needs ${escape(missingText(s.readiness))}</p>` : ""}${gradeWarning(s.readiness)}<button class="secondary" type="button" data-plan-action="plan" data-code="${c.code}">Plan for ${escape(target)}</button></article>`;
        })
        .join("") ||
      '<div class="empty">Add interests or update your course history to explore more suggestions.</div>'
    }</div></section>`;
  }

  function planBoard() {
    const terms = futureTerms(),
      used = new Set(state.planner.plan.map(termKey));
    const visible = terms.filter((t, i) => i < 4 || used.has(termKey(t)));
    return `<section><div class="section-title"><h2>Quarter plan</h2><small>Tentative plans · offerings are not confirmed</small></div><div class="quarter-board">${visible
      .map(
        (t) =>
          `<article class="quarter-column panel"><h3>${escape(termKey(t))}</h3>${
            state.planner.plan
              .filter((p) => termKey(p) === termKey(t))
              .map((p) => {
                const c = byCode().get(p.code),
                  r = p.readiness;
                return `<div class="planned-course"><div><button class="text-button" type="button" data-select-course="${c.code}">${escape(label(c.code))}</button><button class="remove-planned" type="button" data-plan-action="unplan" data-code="${c.code}" aria-label="Remove ${escape(label(c.code))} from plan">×</button></div><p>${escape(c.name)}</p>${r.missing.length ? `<p class="planner-caution">Needs ${escape(missingText(r))} before this quarter.</p>` : r.needs_catalog_review ? '<p class="planner-caution">Check this course’s catalog prerequisites.</p>' : '<small class="plan-valid">Prerequisite order looks consistent</small>'}${p.same_quarter_prerequisites.length && r.missing.length ? '<p class="planner-caution">Same-quarter courses do not satisfy prior-course prerequisites.</p>' : ""}${p.assumed_prerequisites.length ? `<p class="note">Assumes successful completion of ${escape(p.assumed_prerequisites.map(label).join(", "))}.</p>` : ""}${gradeWarning(r)}<small>Offering unverified</small></div>`;
              })
              .join("") ||
            '<p class="empty-quarter">No courses planned yet.</p>'
          }</article>`,
      )
      .join("")}</div></section>`;
  }

  function render(nextState) {
    state = nextState;
    if (
      ["mine", "taken", "future"].includes(graphMode) &&
      !graphCourses().some((c) => c.code === selected)
    )
      selected = graphCourses()[0]?.code || "";
    const terms = futureTerms();
    if (!target || !terms.some((t) => termKey(t) === target))
      target = termKey(terms[0]);
    const r = state.planner.requirements;
    return `<div id="planner-root"><div class="planner-intro"><div><span class="tag">${state.planner.profile.major === "cs" ? "UW Seattle · Computer Science BS" : "Course exploration"}</span><p>Build a path, see what unlocks next, and keep your future quarters separate from assignment tracking.</p></div><label class="target-quarter-label">Plan into<select id="planner-target">${terms.map((t) => `<option ${termKey(t) === target ? "selected" : ""}>${escape(termKey(t))}</option>`).join("")}</select></label></div>${profile()}<div class="planner-stats">${[
      [
        "Completed",
        state.planner.profile.completed.length,
        "Courses you entered",
      ],
      [
        "Fundamentals",
        state.planner.profile.major === "cs" ? r.fundamentals_done + "/6" : "—",
        "CS course checkpoints",
      ],
      [
        "Core courses",
        state.planner.profile.major === "cs" ? r.core_done + "/6" : "—",
        "Includes " + r.upper_core_done + " CSE 400-level courses",
      ],
      [
        "Elective credits",
        state.planner.profile.major === "cs" ? r.elective_credits + "/33" : "—",
        "From recorded + approved credits",
      ],
    ]
      .map(
        ([title, value, hint]) =>
          `<div class="stat"><span class="stat-label">${title}</span><div class="stat-value">${value}</div><small class="stat-hint">${hint}</small></div>`,
      )
      .join(
        "",
      )}</div><div class="planner-layout"><section class="panel planner-map-panel"><div class="planner-map-heading"><div><h2>Course map</h2><p>Find a course, check its prerequisites, then add it to a future quarter.</p></div><button class="secondary" type="button" data-plan-action="focus">Show connections</button></div><div class="planner-map-filters"><label class="visually-hidden" for="graph-filter">Map view</label><select id="graph-filter">${[
      ["mine", "My course path"],
      ["taken", "Classes taken only"],
      ["future", "Future classes (planned)"],
      ["pathways", "Explore core pathways"],
      ["all", "All mapped courses"],
      ["ready", "Prerequisites recorded"],
      ["interests", "My interests"],
      ["focus", "Selected course & connections"],
    ]
      .map(
        ([value, text]) =>
          `<option value="${value}" ${graphMode === value ? "selected" : ""}>${text}</option>`,
      )
      .join(
        "",
      )}</select><input id="graph-search" aria-label="Search the prerequisite web" placeholder="Find any course — CSE 446, machine learning…" value="${escape(search)}"><button type="button" class="secondary" data-plan-action="clear-search" id="clear-course-search" ${search ? "" : "hidden"}>Clear search</button></div><p class="note planner-search-hint" id="planner-search-hint" aria-live="polite">${searchHint()}</p><div class="graph-legend"><span class="legend-completed">Completed</span><span class="legend-current">Current</span><span class="legend-planned">Planned</span><span class="legend-ready">Prerequisites recorded</span><span>Solid: required</span><span>Dashed: alternative</span><span>Dotted: recommended</span></div><div id="planner-graph">${graph()}</div><p class="note planner-map-note">Arrows point from a prerequisite to the course it prepares you for. Click a course for the full checklist. Search always includes the entire catalog; clear it to return to your chosen view.</p></section><div id="planner-detail">${detail()}</div></div>${suggestions()}${planBoard()}${requirements()}<p class="note">Catalog snapshot: ${escape(state.planner.version)}. Interest tags and ranking are app suggestions. Planning a course does not establish that it is offered or that you can register. ${sourceLink(state.planner.sources.pathways, "UW suggested pathways")}</p></div>`;
  }

  function positionGraph() {
    const canvas = document.querySelector(".planner-graph-canvas");
    if (!canvas) return;
    canvas.style.width = dimensions.width + "px";
    canvas.style.height = dimensions.height + "px";
    for (const node of canvas.querySelectorAll("[data-select-course]")) {
      const p = positions.get(node.dataset.selectCourse);
      node.style.left = p.x + "px";
      node.style.top = p.y + "px";
    }
    for (const stage of canvas.querySelectorAll("[data-stage]"))
      stage.style.left = 24 + Number(stage.dataset.stage) * 252 + "px";
  }

  async function saveProfile(profile) {
    await helpers.api("/api/planner/profile", profile);
    await helpers.reload();
  }
  async function savePlan(plan) {
    await helpers.api(
      "/api/planner/plan",
      plan.map(({ code, quarter, year }) => ({ code, quarter, year })),
    );
    await helpers.reload();
  }

  function mount(nextHelpers) {
    helpers = nextHelpers;
    positionGraph();
    const root = document.querySelector("#planner-root");
    root
      .querySelector(".planner-profile")
      .addEventListener("toggle", (event) => {
        profileOpen = event.target.open;
      });
    root.addEventListener("click", async (event) => {
      const button = event.target.closest("button");
      if (!button || busy) return;
      if (button.dataset.selectCourse) {
        selected = button.dataset.selectCourse;
        document.querySelector("#planner-detail").innerHTML = detail();
        for (const n of root.querySelectorAll(".graph-node"))
          n.classList.toggle("selected", n.dataset.selectCourse === selected);
        document.querySelector("#planner-graph").innerHTML = graph();
        positionGraph();
        return;
      }
      const action = button.dataset.planAction;
      if (!action) return;
      if (action === "clear-search") {
        search = "";
        root.querySelector("#graph-search").value = "";
        refreshMap();
        return;
      }
      if (action === "focus") {
        graphMode = "focus";
        search = "";
        await helpers.reload();
        return;
      }
      if (action === "import") {
        const [quarter, year] = target.split(" ");
        helpers.importCourse(button.dataset.code, {
          quarter,
          year: Number(year),
        });
        return;
      }
      busy = true;
      button.disabled = true;
      try {
        const p = state.planner.profile,
          code = button.dataset.code;
        if (action === "complete")
          await saveProfile({
            ...p,
            completed: [
              ...p.completed.filter((c) => c.code !== code),
              { code, grade: null },
            ],
          });
        if (action === "uncomplete")
          await saveProfile({
            ...p,
            completed: p.completed.filter((c) => c.code !== code),
          });
        if (action === "plan") {
          if (state.planner.plan.some((p) => p.code === code))
            throw Error(
              "This course is already planned. Remove it from its quarter before moving it.",
            );
          const [quarter, year] = target.split(" ");
          await savePlan([
            ...state.planner.plan,
            { code, quarter, year: Number(year) },
          ]);
          helpers.toast(
            `${label(code)} added to your tentative ${target} plan.`,
          );
        }
        if (action === "unplan")
          await savePlan(state.planner.plan.filter((p) => p.code !== code));
      } catch (error) {
        helpers.toast(error.message, 10000);
      } finally {
        busy = false;
        button.disabled = false;
      }
    });
    root.querySelector("#planner-completed-form").onsubmit = async (event) => {
      event.preventDefault();
      if (busy) return;
      busy = true;
      try {
        const code = root
          .querySelector("#completed-code")
          .value.replace(/\s+/g, "")
          .toUpperCase();
        const value = root.querySelector("#completed-grade").value;
        const grade = value === "" ? null : Number(value);
        const p = state.planner.profile;
        await saveProfile({
          ...p,
          completed: [
            ...p.completed.filter((c) => c.code !== code),
            { code, grade },
          ],
        });
      } catch (error) {
        helpers.toast(error.message, 10000);
      } finally {
        busy = false;
      }
    };
    root.querySelector("#planner-profile-form").onsubmit = async (event) => {
      event.preventDefault();
      if (busy) return;
      busy = true;
      try {
        const data = new FormData(event.target);
        await saveProfile({
          ...state.planner.profile,
          major: data.get("major"),
          interests: data.getAll("interests"),
          other_elective_credits: Number(data.get("other_elective_credits")),
          science_credits: Number(data.get("science_credits")),
          capstone_confirmed: data.has("capstone_confirmed"),
        });
        helpers.toast("Planning preferences saved on this device.");
      } catch (error) {
        helpers.toast(error.message, 10000);
      } finally {
        busy = false;
      }
    };
    root.querySelector("#planner-target").onchange = async (event) => {
      target = event.target.value;
      await helpers.reload();
    };
    root.querySelector("#graph-filter").onchange = (event) => {
      graphMode = event.target.value;
      refreshMap();
    };
    root.querySelector("#graph-search").oninput = (event) => {
      search = event.target.value;
      refreshMap();
    };
  }
  window.UWCSPlanner = { render, mount };
})();
