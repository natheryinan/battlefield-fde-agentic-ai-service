
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

  
    if (!url.pathname.startsWith("/view")) {
      return new Response("Not Found", { status: 404 });
    }

    
    const email =
      request.headers.get("cf-access-authenticated-user-email");

    if (!email) {
      return new Response("Unauthorized", { status: 401 });
    }

    
    const key = `burn:${email}:${url.pathname}`;

    
    const alreadySeen = await env.GATES.get(key);

    if (alreadySeen) {
      return new Response(
        "This page has been destroyed.",
        { status: 410 }
      );
    }

    
    await env.GATES.put(key, "1", {
      expirationTtl: 300 
    });

    
        return new Response(
      `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8"/>
          <title>pp-gate</title>
        </head>
        <body>
          <pre>
/*
  Huawei Confidential – Read Once
  This material self-destructs after viewing.
*/
          
function gateWalker() {
  // pseudo-code only
  return "restricted";
}
          </pre>

          <!-- Cloudflare Web Analytics -->
          <script defer src="https://static.cloudflareinsights.com/beacon.min.js"
            data-cf-beacon='{"token":"325f8945fe34382ba8b2ae287c6016e"}'>
          </script>
          <!-- End Cloudflare Web Analytics -->

        </body>
      </html>
      `,
      { headers: { "Content-Type": "text/html; charset=UTF-8" } }
    );
