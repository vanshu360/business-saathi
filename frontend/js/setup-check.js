async function checkSystem() {
  const health = document.getElementById("health");
  const sarvam = document.getElementById("sarvam");
  try {
    const h = await fetch("/api/health").then((r) => r.json());
    health.textContent = `Server: ${h.status}, database: ${h.database}`;
    health.className = "ok";
    const s = await fetch("/api/system/status").then((r) => r.json());
    sarvam.textContent = s.sarvam_message;
    sarvam.className = s.sarvam_configured ? "ok" : "warn";
  } catch (err) {
    health.textContent = "Cannot reach the server. Is it running?";
    health.className = "warn";
  }
}
checkSystem();
