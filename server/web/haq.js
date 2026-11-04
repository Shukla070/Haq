// Haq on the web: the same screens as the Android app, over the same API (docs/APP_API.md).
// Everything the server sends is shown with textContent, never as HTML: a complaint can
// quote text from a customer's file, and that text must never run as code here.
"use strict";

(() => {
  const VOICE_ONLY_STORY = "I explained what happened in my voice note.";
  const PRIVACY_POLICY = "https://github.com/Shukla070/Haq/blob/main/docs/PRIVACY.md";
  const SOURCE = "https://github.com/Shukla070/Haq";
  const MAX_UPLOAD = 32 * 1024 * 1024;
  const MAX_VOICE_SECONDS = 5 * 60;
  const POLL_MS = 2500;

  // ---------- Storage and the device token ----------

  const store = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); return true; } catch { return false; } },
  };

  function newToken() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  // A case belongs to the browser that made it, as it belongs to the app install that made it.
  let device = store.get("haq.device");
  if (!device || !/^[A-Za-z0-9_-]{32,128}$/.test(device)) {
    device = newToken();
    store.set("haq.device", device);
  }
  const deviceKept = store.get("haq.device") === device;

  // ---------- The API ----------

  class ApiError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }

  function sentence(text) {
    const t = String(text).trim();
    return t ? t[0].toUpperCase() + t.slice(1) : t;
  }

  async function call(method, path, body) {
    const headers = { "X-Haq-Device": device, Accept: "application/json" };
    let payload;
    if (body instanceof FormData) payload = body;
    else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
    let response;
    try {
      response = await fetch(path, { method, headers, body: payload });
    } catch {
      throw new ApiError(0, "Can't reach the Haq server. Check your connection and try again.");
    }
    const text = await response.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = null; }
    if (!response.ok) {
      let detail = data && data.detail;
      if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
      throw new ApiError(response.status, typeof detail === "string" && detail ? sentence(detail) : `The server returned an error (${response.status}).`);
    }
    return data;
  }

  async function callBlob(path) {
    let response;
    try {
      response = await fetch(path, { headers: { "X-Haq-Device": device } });
    } catch {
      throw new ApiError(0, "Can't reach the Haq server. Check your connection and try again.");
    }
    if (!response.ok) throw new ApiError(response.status, `Couldn't get that file (${response.status}).`);
    return response.blob();
  }

  // ---------- Building the page ----------

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      if (key === "class") el.className = value;
      else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat()) {
      if (child == null || child === false) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  }

  const ICONS = {
    help: "M11,18h2v-2h-2v2zM12,2C6.48,2 2,6.48 2,12s4.48,10 10,10 10,-4.48 10,-10S17.52,2 12,2zM12,20c-4.41,0 -8,-3.59 -8,-8s3.59,-8 8,-8 8,3.59 8,8 -3.59,8 -8,8zM12,6c-2.21,0 -4,1.79 -4,4h2c0,-1.1 0.9,-2 2,-2s2,0.9 2,2c0,2 -3,1.75 -3,5h2c0,-2.25 3,-2.5 3,-5 0,-2.21 -1.79,-4 -4,-4z",
    chevron: "M10,6L8.59,7.41 13.17,12l-4.58,4.59L10,18l6,-6z",
    refresh: "M17.65,6.35C16.2,4.9 14.21,4 12,4c-4.42,0 -7.99,3.58 -7.99,8s3.57,8 7.99,8c3.73,0 6.84,-2.55 7.73,-6h-2.08c-0.82,2.33 -3.04,4 -5.65,4 -3.31,0 -6,-2.69 -6,-6s2.69,-6 6,-6c1.66,0 3.14,0.69 4.22,1.78L13,11h7V4l-2.35,2.35z",
    back: "M20,11H7.83l5.59,-5.59L12,4l-8,8 8,8 1.41,-1.41L7.83,13H20v-2z",
  };

  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", ICONS[name]);
    svg.append(path);
    return svg;
  }

  function button(text, onclick, { kind = "", icon: iconName = null, wide = false, disabled = false } = {}) {
    return h("button", { type: "button", class: `btn ${kind}${wide ? " wide" : ""}`, onclick, disabled }, iconName && icon(iconName), text);
  }

  function link(text, href, { kind = "", wide = false } = {}) {
    return h("a", { class: `btn ${kind}${wide ? " wide" : ""}`, href }, text);
  }

  const section = (text) => h("h2", { class: "section" }, text);
  const label = (text) => h("p", { class: "label" }, text);
  const sheet = (...children) => h("div", { class: "sheet" }, ...children);
  const info = (key, value, tone) => h("div", { class: "info" }, h("span", { class: "k" }, key), h("span", { class: `v ${tone || ""}` }, value));

  function toast(text) {
    const el = document.getElementById("toast");
    el.textContent = text;
    el.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.classList.remove("show"), 2200);
  }

  const root = () => document.getElementById("app");
  const show = (...nodes) => root().replaceChildren(...nodes);

  // ---------- Words, as the app says them ----------

  const india = new Intl.NumberFormat("en-IN");
  const rupees = (amount) => "₹" + india.format(amount);

  function day(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return iso || "";
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]}`;
  }

  function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  const caseKind = (type) => ({ upi_failed_debit: "Failed UPI payment", ecommerce_refund: "Online order refund" })[type] || "Your case";

  const STATUS = {
    new: "Not started",
    working: "Working on it",
    draft_ready: "Complaint ready",
    waiting: "Waiting for a reply",
    needs_input: "Needs your answer",
    referred: "Go elsewhere",
    resolved: "Resolved",
    filed: "Escalated",
    sent: "Complaint sent",
    paused: "Interrupted",
  };
  const statusLabel = (status) => STATUS[status] || status;

  const STATUS_HELP = {
    working: "Haq is reading your proof and writing your complaint.",
    draft_ready: "Your complaint is written and checked. Read it, then send it yourself.",
    waiting: "You sent your complaint, so now they have time to reply.",
    needs_input: "Haq needs one more detail from you before it can finish.",
    referred: "Haq can't take this case, but these services can help.",
    resolved: "You told Haq this has been fixed.",
    filed: "You took your complaint to the next step. Keep its acknowledgement and reference number.",
    sent: "You sent your complaint. Tell Haq whether it has been fixed.",
    paused: "Haq stopped before it finished. Your case and proof are saved.",
    new: "Haq hasn't started on this case yet.",
  };

  const PROOF_KIND = {
    image: "Photo or screenshot",
    text: "Text file",
    pdf: "PDF",
    voice: "Your voice note",
    marked_image: "Your photo, with the damage marked by Haq",
  };

  const untilLabel = (status) => (status === "waiting" ? "Reply due by" : "Next step on");

  // ---------- Small tools ----------

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = h("textarea", { class: "offscreen" });
      area.value = text;
      document.body.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    toast("Copied");
  }

  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = h("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  /** A calendar file for the reply date: the web has no reminder notification. */
  function calendarFile(caseId, until) {
    const [y, m, d] = until.split("-").map(Number);
    const next = new Date(Date.UTC(y, m - 1, d + 1));
    const ymd = (date) => date.toISOString().slice(0, 10).replace(/-/g, "");
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
    const lines = [
      "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Haq//Reminder//EN", "BEGIN:VEVENT",
      `UID:${caseId}-${until}@haq`, `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${until.replace(/-/g, "")}`, `DTEND;VALUE=DATE:${ymd(next)}`,
      "SUMMARY:Has your complaint been fixed?",
      `DESCRIPTION:Its reply date has come. Open Haq to tell it what to do next: ${location.origin}/#/case/${caseId}`,
      "END:VEVENT", "END:VCALENDAR",
    ];
    download(new Blob([lines.join("\r\n") + "\r\n"], { type: "text/calendar" }), "haq-reminder.ics");
  }

  /** Records a voice note in the browser and hands back a File. */
  function voiceRecorder(onDone, { buttonText = "Record a voice note", disabled = false } = {}) {
    const box = h("div", { class: "field" });
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      box.append(h("p", { class: "muted small" }, "This browser can't record voice notes. Typing works just as well."));
      return box;
    }
    const types = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus", "audio/webm"];
    const type = types.find((t) => MediaRecorder.isTypeSupported(t)) || "";
    const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
    let recorder = null;
    let timer = null;
    let started = 0;
    const status = h("p", { class: "muted small" }, "Speak in Hindi, English or both.");
    const btn = button(buttonText, toggle, { disabled });
    box.append(btn, status);

    async function toggle() {
      if (recorder) { recorder.stop(); return; }
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        status.textContent = "Haq needs the microphone for voice notes. Typing works just as well.";
        status.className = "error small";
        return;
      }
      const chunks = [];
      recorder = type ? new MediaRecorder(stream, { mimeType: type }) : new MediaRecorder(stream);
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        clearInterval(timer);
        stream.getTracks().forEach((t) => t.stop());
        recorder = null;
        btn.lastChild.textContent = buttonText;
        status.className = "muted small";
        const blob = new Blob(chunks, { type: type.split(";")[0] || "audio/webm" });
        if (blob.size < 1000) { status.textContent = "That recording didn't work. Please try again."; return; }
        status.textContent = "Speak in Hindi, English or both.";
        onDone(blob, ext);
      };
      recorder.start();
      started = Date.now();
      btn.lastChild.textContent = "Stop recording";
      status.className = "recording small";
      const tick = () => {
        const s = Math.floor((Date.now() - started) / 1000);
        status.textContent = `Recording… ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
        if (s >= MAX_VOICE_SECONDS && recorder) recorder.stop();
      };
      tick();
      timer = setInterval(tick, 500);
    }
    return box;
  }

  // ---------- Home ----------

  function header() {
    return h("header", { class: "top" },
      h("div", { class: "wrap" },
        h("div", { class: "logo", lang: "hi" }, "हक़"),
        h("h1", {}, "Get back money a company owes you."),
        h("p", {}, "Tell us what happened and share your proof. Haq writes the complaint the rules entitle you to, and you send it yourself."),
        h("div", { class: "actions" },
          link("Start a new case", "#/new", { kind: "main", wide: true }),
          h("a", { class: "btn ghost wide", href: "#/guide" }, icon("help"), h("span", { class: "grow" }, "How Haq works"), icon("chevron"))),
        h("p", { class: "note-top" }, "An early test version. Read every complaint before you send it.")));
  }

  function footer() {
    return h("footer", { class: "wrap small muted" },
      h("p", {}, "Haq is not a lawyer and can make mistakes, and it can't promise you'll get your money back."),
      h("p", {}, h("a", { href: PRIVACY_POLICY, rel: "noopener" }, "Privacy policy"), "  ·  ", h("a", { href: SOURCE, rel: "noopener" }, "Source on GitHub")));
  }

  function caseCard(c) {
    return h("a", { class: "card", href: `#/case/${c.id}` },
      h("div", { class: "body" },
        h("div", { class: "title" }, h("span", {}, caseKind(c.dispute_type)), icon("chevron")),
        c.title && h("p", { class: "told" }, c.title),
        h("hr"),
        info("Current status", c.running ? "Working on it" : statusLabel(c.status), "primary"),
        c.compensation_owed > 0 && info("Compensation owed so far", rupees(c.compensation_owed), "owed"),
        c.until && info(untilLabel(c.status), day(c.until))));
  }

  function showHome() {
    const list = h("div", { class: "cases" }, h("p", { class: "muted" }, "Loading your cases…"));
    const refresh = button("Refresh", load, { icon: "refresh" });
    show(
      header(),
      h("main", { class: "wrap" },
        !deviceKept && h("p", { class: "banner" }, "This browser isn't keeping data, so your cases will be lost when you close it. Turn off private browsing to keep them."),
        h("div", { class: "row between" }, h("h2", { class: "display" }, "Your cases"), refresh),
        list),
      footer());

    async function load() {
      refresh.disabled = true;
      try {
        const cases = await call("GET", "/cases");
        list.replaceChildren(...(cases.length ? cases.map(caseCard)
          : [h("p", { class: "muted" }, "No cases yet. When you start one, it appears here with its status and what you're owed.")]));
      } catch (e) {
        list.replaceChildren(h("p", { class: "error" }, e.message), h("p", { class: "muted" }, "Your cases couldn't load. They're still saved, so tap Refresh to try again."));
      } finally {
        refresh.disabled = false;
      }
    }
    load();
  }

  // ---------- A new case ----------

  function showNew() {
    const files = [];
    const story = h("textarea", { id: "story", placeholder: "For example: On 12 October I sent Rs 4,500 on UPI. The app said failed but the money was cut from my account." });
    const picker = h("input", { type: "file", multiple: true, accept: "image/*,application/pdf,.pdf,text/plain,.txt,audio/*", hidden: true });
    const list = h("div", { class: "files" });
    const name = h("input", { type: "text", id: "name", autocomplete: "name", maxlength: "80" });
    name.value = store.get("haq.name") || "";
    const status = h("p", { class: "muted", role: "status" });
    const go = button("Get my money back", start, { kind: "main", wide: true });
    let busy = false;

    function voiceCount() { return files.filter((f) => f.name.startsWith("Voice note ")).length; }

    function refreshList() {
      list.replaceChildren(...files.map((file, i) => h("div", { class: "file" },
        h("span", {}, file.name),
        h("button", { type: "button", class: "linkbtn", onclick: () => { files.splice(i, 1); refreshList(); } }, "Remove"))));
      check();
    }

    function check() {
      go.disabled = busy || !name.value.trim() || !(story.value.trim() || voiceCount() > 0);
    }

    picker.addEventListener("change", () => {
      for (const file of picker.files) {
        if (file.size > MAX_UPLOAD) { status.textContent = `${file.name} is over 32 MB, so Haq can't take it.`; status.className = "error"; continue; }
        files.push(file);
      }
      picker.value = "";
      refreshList();
    });
    story.addEventListener("input", check);
    name.addEventListener("input", check);

    const recorder = voiceRecorder((blob, ext) => {
      files.push(new File([blob], `Voice note ${voiceCount() + 1}.${ext}`, { type: blob.type }));
      refreshList();
    });

    async function start() {
      busy = true;
      check();
      status.className = "muted";
      let caseId = null;
      try {
        status.textContent = "Creating your case…";
        const told = story.value.trim() || VOICE_ONLY_STORY;
        const created = await call("POST", "/cases", { story: told, name: name.value.trim() });
        caseId = created.id;
        store.set("haq.name", name.value.trim());
        for (const [i, file] of files.entries()) {
          status.textContent = `Reading ${file.name} (${i + 1} of ${files.length})…`;
          const form = new FormData();
          form.append("note", "");
          form.append("file", file, file.name);
          await call("POST", `/cases/${caseId}/evidence`, form);
        }
        status.textContent = "Starting…";
        await call("POST", `/cases/${caseId}/run`);
        location.hash = `#/case/${caseId}`;
      } catch (e) {
        busy = false;
        check();
        status.className = "error";
        status.textContent = e.message;
        if (caseId) {
          status.append(" ", h("a", { href: `#/case/${caseId}` }, "Your case is saved: open it to try again."));
        }
      }
    }

    show(h("main", { class: "wrap" },
      h("div", {}, link("← Back", "#/")),
      h("h1", { class: "display" }, "What happened?"),
      h("label", { class: "label", for: "story" }, "Tell Haq in your own words"),
      story,
      section("Your proof"),
      h("p", { class: "muted small" }, "Screenshots of the payment or order, bank SMS, invoices, statements (PDF), or a photo of a damaged item. Card numbers, Aadhaar and OTPs are hidden from the agent working on your case."),
      button("Add proof", () => picker.click()),
      picker,
      list,
      h("p", { class: "label" }, "Or tell it out loud"),
      recorder,
      h("div", { class: "field" },
        h("label", { class: "label", for: "name" }, "Your name, as on your account or order"),
        name,
        h("p", { class: "muted small" }, "Haq signs your complaint with it.")),
      go,
      status));
    check();
  }

  // ---------- One case ----------

  let stopPolling = () => {};

  function showCase(id) {
    const body = h("div", { class: "stack" }, h("p", { class: "muted" }, "Loading your case…"));
    show(h("main", { class: "wrap" }, h("div", {}, link("← Your cases", "#/")), body));
    let alive = true;
    let timer = null;
    let view = null;
    let error = null;
    let busy = false;
    let complaintOpen = false;
    stopPolling = () => { alive = false; clearTimeout(timer); };

    async function load() {
      clearTimeout(timer);
      try {
        const fresh = await call("GET", `/cases/${id}`);
        if (!alive) return;
        view = fresh;
        draw();
        if (view.running) timer = setTimeout(load, POLL_MS);
      } catch (e) {
        if (!alive) return;
        if (e.status === 404) {
          body.replaceChildren(h("p", {}, "This case doesn't exist, or it was started in another browser. Cases stay with the browser that started them."));
        } else if (view) {
          error = e.message;
          draw();
          timer = setTimeout(load, POLL_MS * 2);
        } else {
          body.replaceChildren(h("p", { class: "error" }, e.message), button("Try again", load));
        }
      }
    }

    async function act(work, after) {
      if (busy) return;
      busy = true;
      error = null;
      draw();
      try {
        const result = await work();
        if (after === "view" && result) view = result;
        if (after === "home") { location.hash = "#/"; return; }
      } catch (e) {
        error = e.message;
      } finally {
        busy = false;
      }
      if (!alive) return;
      if (after === "poll") await load(); else draw();
    }

    const actions = {
      run: () => act(() => call("POST", `/cases/${id}/run`), "poll"),
      answer: (text) => act(() => call("POST", `/cases/${id}/answer`, { text }), "poll"),
      answerVoice: (blob, ext) => act(async () => {
        const form = new FormData();
        form.append("note", "");
        form.append("file", new File([blob], `Voice answer.${ext}`, { type: blob.type }), `Voice answer.${ext}`);
        await call("POST", `/cases/${id}/evidence`, form);
        return call("POST", `/cases/${id}/answer`, { text: "I recorded a voice note with my answer." });
      }, "poll"),
      sent: () => act(() => call("POST", `/cases/${id}/sent`, {}), "view"),
      fixed: () => act(() => call("POST", `/cases/${id}/fixed`), "view"),
      notFixed: () => act(() => call("POST", `/cases/${id}/not-fixed`), "poll"),
      remove: () => {
        if (confirm("Delete this case? The case and your evidence are removed from Haq's server. This cannot be undone.")) {
          act(() => call("DELETE", `/cases/${id}`), "home");
        }
      },
    };

    function draw() {
      const v = view;
      const parts = [];
      parts.push(h("h1", { class: "display" }, caseKind(v.dispute_type)));
      if (v.title) parts.push(h("div", {}, label("What you told Haq"), h("p", { class: "pre" }, v.title)));
      if (error) parts.push(h("p", { class: "banner", role: "alert" }, error));
      if (busy) parts.push(h("div", { class: "working" }, h("div", { class: "spinner" }), "One moment…"));

      if (v.running) {
        parts.push(working(v));
      } else {
        parts.push(sheet(label("Current status"), h("p", { class: "status-value" }, statusLabel(v.status)),
          STATUS_HELP[v.status] && h("p", {}, STATUS_HELP[v.status])));
        if (v.status !== "resolved") parts.push(owed(v));
        if (v.status === "draft_ready" && v.draft) parts.push(...draftReady(v));
        if (["waiting", "resolved", "sent"].includes(v.status) && v.hold) parts.push(...waiting(v));
        else if (v.status === "sent") parts.push(...fixedQuestion());
        if (v.status === "needs_input") parts.push(...question(v));
        if (v.status === "referred" && v.referral) parts.push(...referred(v.referral));
        if (v.status === "paused" || v.status === "new") parts.push(button("Try again", actions.run, { kind: "main", disabled: busy }));
        if (v.status !== "draft_ready" && (v.sent || []).length && v.draft) parts.push(...sentComplaint(v.draft));
      }
      parts.push(...proof(v));
      if (!v.running) parts.push(h("div", {}, button("Delete this case", actions.remove, { kind: "danger", disabled: busy })));
      body.replaceChildren(...parts.filter(Boolean));
    }

    function working(v) {
      const steps = (v.progress && v.progress.steps) || [];
      return h("div", { class: "field" },
        h("div", { class: "working" }, h("div", { class: "spinner" }), (v.progress && v.progress.current) || "Starting"),
        steps.slice(0, -1).map((s) => h("p", { class: "done" }, "✓  " + s)),
        h("p", { class: "muted small" }, "This usually takes one to two minutes. Haq checks every fact against your proof and every rule against the official text. You can leave this page and come back."));
    }

    function owed(v) {
      const e = v.entitlement;
      if (!e || !(e.compensation_owed > 0)) return null;
      const why = [
        e.reversal_due_by && `Your money should have been back by ${day(e.reversal_due_by)}.`,
        e.days_late != null && `RBI rules give you ₹100 for each day it's late, and it's ${e.days_late} days late.`,
        e.compensation_still_growing && "This grows by ₹100 every day until the money is back.",
      ].filter(Boolean).join(" ");
      return sheet(label("Compensation owed so far"), h("p", { class: "amount" }, rupees(e.compensation_owed)), why && h("p", {}, why));
    }

    function complaintText(d) {
      return [label("Send it to"), h("p", { class: "pre" }, d.recipient),
        label("Subject"), h("p", { class: "pre strong" }, d.subject),
        label("Message"), h("p", { class: "pre" }, d.body)];
    }

    function draftReady(v) {
      const d = v.draft;
      const full = d.subject + "\n\n" + d.body;
      const mail = `mailto:?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
      const heldBack = v.evidence.filter((e) => e.masked && e.kind !== "voice").map((e) => e.original_name);
      return [
        section("Your complaint"),
        sheet(...complaintText(d), h("span", { class: "stamp" }, "Checked against your proof")),
        h("p", { class: "muted small" }, "Checked before you see it: every fact against your proof, every rule against the official text, every amount against your evidence."),
        h("div", { class: "row" },
          button("Copy complaint", () => copy(full), { kind: "main" }),
          h("a", { class: "btn", href: mail }, "Open in email")),
        h("p", { class: "muted small" }, "Add the address yourself: look for the grievance officer or customer care email on the company's website or app. Attach your proof from the list below. If the email comes out cut short, use Copy instead."),
        heldBack.length && h("p", { class: "muted small" }, `Not for attaching: ${heldBack.join(", ")}. It shows a card number, Aadhaar or OTP. Cover that number before you send it.`),
        button("I've sent it", actions.sent, { wide: true, disabled: busy }),
        d.next_steps && section("What to do next"),
        d.next_steps && h("p", { class: "pre" }, d.next_steps),
      ];
    }

    function fixedQuestion() {
      return [section("Has this been fixed?"),
        h("div", { class: "row" },
          button("Yes, it's fixed", actions.fixed, { kind: "main", disabled: busy }),
          button("No, not fixed", actions.notFixed, { disabled: busy }))];
    }

    function waiting(v) {
      const until = v.hold.until;
      const parts = [section("What happens next")];
      if (until) parts.push(info(untilLabel(v.status), day(until)));
      if (v.hold.message) parts.push(h("p", { class: "pre" }, v.hold.message));
      if (v.status === "waiting" && until && until >= todayIso()) {
        parts.push(h("p", { class: "small muted" }, `On the web Haq can't send you a reminder, so put ${day(until)} in your calendar.`),
          h("div", {}, button("Add to calendar", () => calendarFile(v.id, until))));
      }
      if (v.status !== "resolved") parts.push(...fixedQuestion());
      return parts;
    }

    function question(v) {
      const answer = h("textarea", { id: "answer", class: "short" });
      const send = button("Send answer", () => actions.answer(answer.value.trim()), { kind: "main", disabled: true });
      answer.addEventListener("input", () => { send.disabled = busy || !answer.value.trim(); });
      return [
        section("Haq's question"),
        sheet(h("p", { class: "pre" }, (v.question && v.question.question) || "")),
        h("label", { class: "label", for: "answer" }, "Your answer"),
        answer,
        h("div", {}, send),
        label("Or answer with a voice note"),
        voiceRecorder(actions.answerVoice, { buttonText: "Record your answer", disabled: busy }),
      ];
    }

    function referred(r) {
      return [section("What to do now"), h("p", { class: "pre" }, r.where),
        h("div", { class: "row" },
          link("Call 1930 (cyber fraud)", "tel:1930"),
          link("Call 1915 (consumer helpline)", "tel:1915"),
          link("Call 14448 (RBI)", "tel:14448"))];
    }

    function sentComplaint(d) {
      const toggle = button(complaintOpen ? "Hide your complaint" : "See the complaint you sent",
        () => { complaintOpen = !complaintOpen; draw(); }, { wide: true });
      if (!complaintOpen) return [toggle];
      return [toggle, sheet(...complaintText(d)), h("div", {}, button("Copy", () => copy(d.subject + "\n\n" + d.body)))];
    }

    function proof(v) {
      if (!v.evidence || !v.evidence.length) return [];
      const items = v.evidence.map((item) => {
        const notes = [PROOF_KIND[item.kind] || "File"];
        if (item.masked) notes.push("sensitive numbers hidden");
        if (item.instruction_like && item.instruction_like.length) notes.push("contains text trying to instruct an AI; ignored");
        const row = h("div", { class: "item" },
          h("div", {}, h("p", { class: "name" }, item.original_name), h("p", { class: "small muted" }, notes.join("  ·  "))),
          item.attachable && button("Download", async () => {
            try { download(await callBlob(`/cases/${v.id}/evidence/${item.id}/file`), item.original_name); }
            catch (e) { toast(e.message); }
          }));
        const parts = [h("hr"), row];
        if (item.kind === "marked_image") {
          const img = h("img", { alt: "Your photo with the damage marked" });
          callBlob(`/cases/${v.id}/evidence/${item.id}/file`).then((blob) => { img.src = URL.createObjectURL(blob); }).catch(() => img.remove());
          parts.push(img, h("p", { class: "small muted" }, "Haq's AI marked this copy. If the mark is wrong, don't attach it."));
        }
        return parts;
      });
      return [section("Your proof"), h("div", { class: "proof" }, ...items.flat())];
    }

    load();
  }

  // ---------- How Haq works ----------

  function showGuide() {
    const steps = [
      ["Tell Haq what happened", "Type it, or record a voice note in Hindi, English or both."],
      ["Add your proof", "Screenshots, bank SMS, invoices, statements, or a photo of a damaged item."],
      ["Read your complaint", "In a minute or two, Haq works out what the rules give you and writes the complaint. It checks every fact against your proof and every rule against the official text."],
      ["Send it yourself", "Copy it, or open it in your email app, and attach your proof. Haq never sends anything. Then tap I've sent it, and Haq tells you when the company's time is up and helps with the next step."],
    ];
    show(h("main", { class: "wrap" },
      h("div", {}, link("← Back", "#/")),
      h("h1", { class: "display" }, "How Haq works"),
      h("div", { class: "steps" }, steps.map(([title, text], i) =>
        h("div", { class: "step" }, h("div", { class: "n" }, String(i + 1)), h("div", {}, h("p", { class: "strong" }, title), h("p", {}, text))))),
      sheet(
        h("p", { class: "strong" }, "What Haq can help with"),
        h("p", {}, "A failed UPI payment that took your money, and refunds for online orders."),
        h("p", { class: "error" }, "Lost money to a scam or fraud? Call 1930 right away. Haq can't help with that.")),
      sheet(
        h("p", { class: "strong" }, "Your data"),
        h("p", {}, "What you add goes to Meta's AI models and is kept on Haq's server until you delete the case. Never share a PIN, password or OTP."),
        h("p", {}, "Your cases stay with this browser. Clearing its data, or switching browser or device, means you can't open them any more, so delete the ones you no longer need first."),
        h("p", {}, h("a", { href: PRIVACY_POLICY, rel: "noopener" }, "Privacy policy"))),
      h("p", { class: "muted small" }, "Haq is not a lawyer and can make mistakes, and it can't promise you'll get your money back. Read your complaint before you send it."),
      link("Start a new case", "#/new", { kind: "main", wide: true })));
  }

  // ---------- Routing ----------

  function route() {
    stopPolling();
    stopPolling = () => {};
    const path = location.hash.slice(1) || "/";
    const match = /^\/case\/(case-\d{8}-\d{6}-[0-9a-f]{6})$/.exec(path);
    if (path === "/new") showNew();
    else if (path === "/guide") showGuide();
    else if (match) showCase(match[1]);
    else showHome();
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", route);
  route();
})();
