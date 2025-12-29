(async () => {
  const VIEW_KEY = "huawei_once_viewed_v1";

  
  let meta = null;
  try {
    const r = await fetch("./meta.json", { cache: "no-store" });
    meta = await r.json();
  } catch (e) {}

  const created = meta?.created_utc ? Date.parse(meta.created_utc) : 0;
  const ttlH = Number(meta?.ttl_hours ?? 0);
  const once = meta?.access_policy?.once_view === true;

  const now = Date.now();
  const expired = !created || !ttlH || (now - created > ttlH * 3600_000);
  const alreadyViewed = once && localStorage.getItem(VIEW_KEY) === "1";

  
  if (expired || alreadyViewed) {
    document.documentElement.innerHTML = `
      <head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow,noarchive"></head>
      <body style="font-family:system-ui;padding:32px">
        <h2>Document expired.</h2>
      </body>`;
    return;
  }


  if (once) localStorage.setItem(VIEW_KEY, "1");

  
  try {
    const payload = {
      t_utc_ms: now,
      path: location.pathname,
      ua: navigator.userAgent
    };
    navigator.sendBeacon?.("./view", JSON.stringify(payload));
  } catch (e) {}
})();
