/** Runtime reverse-proxy: forwards /api/* to the FastAPI backend.
 *
 *  Read at REQUEST time (not build time), so the backend URL is configured by
 *  the SENTINEL_API_TARGET env var on Cloud Run / locally — unlike next.config
 *  rewrites, which bake their destination at build. Streams the response body
 *  through unchanged, so Server-Sent Events (the live agent run) pass straight
 *  to the browser.
 */
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const TARGET = process.env.SENTINEL_API_TARGET || "http://localhost:8000";

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = `${TARGET}/api/${(path ?? []).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  const accept = req.headers.get("accept");
  if (contentType) headers.set("content-type", contentType);
  if (accept) headers.set("accept", accept);

  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer();

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body,
    // @ts-expect-error - Node fetch needs duplex for streamed request bodies
    duplex: "half",
  });

  // Pass the (possibly streaming) body through; drop hop-by-hop encoding headers.
  const outHeaders = new Headers(upstream.headers);
  outHeaders.delete("content-encoding");
  outHeaders.delete("content-length");
  outHeaders.delete("transfer-encoding");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
