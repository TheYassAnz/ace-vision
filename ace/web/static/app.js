// Poll the status every 2 s; reload when the analysis is over.
function pollStatus(url) {
  setInterval(async () => {
    try {
      const s = await (await fetch(url)).json();
      document.getElementById("bar").value = s.progress;
      if (s.status !== "running") location.reload();
    } catch (e) { /* server busy: retry on next tick */ }
  }, 2000);
}

// Clip buttons: seek to t-1.5 s, play, pause at t+1.0 s.
function clipButtons(videoId) {
  const v = document.getElementById(videoId);
  let stopAt = null;
  v.addEventListener("timeupdate", () => { if (stopAt !== null && v.currentTime >= stopAt) { v.pause(); stopAt = null; } });
  v.addEventListener("pause", () => { stopAt = null; });
  document.querySelectorAll("[data-t]").forEach((b) => b.addEventListener("click", () => {
    const t = parseFloat(b.dataset.t);
    v.currentTime = Math.max(0, t - 1.5);
    v.play().catch(() => {});
    stopAt = t + 1.0;
  }));
}

// Note-taking page: D/R/S/A add a note at the current time, Backspace undoes, Space toggles play.
function noteStrokes(videoId, url) {
  const v = document.getElementById(videoId), notes = [];
  const kinds = { d: "forehand", r: "backhand", s: "serve", a: "other" };
  const count = () => { document.getElementById("count").textContent = `${notes.length} coup${notes.length > 1 ? "s" : ""} noté${notes.length > 1 ? "s" : ""}`; };
  document.addEventListener("keydown", (e) => {
    if (e.repeat || e.metaKey || e.ctrlKey || e.altKey || e.target.closest("input,textarea,select,button")) return;
    if (e.key === " ") { e.preventDefault(); v.paused ? v.play().catch(() => {}) : v.pause(); }
    else if (e.key === "Backspace") { e.preventDefault(); notes.pop(); count(); }
    else if (kinds[e.key.toLowerCase()]) { notes.push({ t: v.currentTime, kind: kinds[e.key.toLowerCase()] }); count(); }
  });
  document.getElementById("save").addEventListener("click", async () => {
    const msg = document.getElementById("msg");
    try {
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(notes) });
      if (!r.ok) throw new Error();
      const s = await r.json();
      msg.textContent = `Enregistré : ${Math.round(s.found_rate * 100)} % trouvés, ${Math.round(s.class_rate * 100)} % bien classés.`;
    } catch (e) { msg.textContent = "Échec de l'enregistrement."; }
  });
}
