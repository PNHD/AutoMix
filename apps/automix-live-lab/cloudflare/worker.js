/**
 * P0-M8-R2 preview deployment worker.
 *
 * Serves the AutoMix Live Lab static app (index.html, src/*) unchanged via
 * the Workers static-assets binding, and proxies exactly the LocalDSP
 * chain's audio file requests (/work_local/local_dsp_chain/*) to the R2
 * bucket they were uploaded to byte-for-byte (no re-encoding, no
 * transcoding). Every other request falls through to static assets.
 *
 * This exists purely so the app's existing `audioBaseUrl` default
 * ("/work_local/local_dsp_chain") resolves correctly in this deployment
 * too, with zero changes to any app/product source file.
 */
const AUDIO_PREFIX = "/work_local/local_dsp_chain/";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith(AUDIO_PREFIX)) {
      const key = url.pathname.slice(AUDIO_PREFIX.length);
      if (!key || key.includes("..") || key.includes("/")) {
        return new Response("NOT_FOUND", { status: 404 });
      }
      const object = await env.AUDIO_BUCKET.get(key);
      if (!object) return new Response("NOT_FOUND", { status: 404 });
      const headers = new Headers();
      object.writeHttpMetadata(headers);
      headers.set("etag", object.httpEtag);
      headers.set("content-type", "audio/wav");
      headers.set("cache-control", "public, max-age=31536000, immutable");
      headers.set("access-control-allow-origin", "*");
      return new Response(object.body, { headers });
    }

    return env.ASSETS.fetch(request);
  },
};
