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
