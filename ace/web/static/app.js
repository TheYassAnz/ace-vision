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
    v.play();
    stopAt = t + 1.0;
  }));
}
