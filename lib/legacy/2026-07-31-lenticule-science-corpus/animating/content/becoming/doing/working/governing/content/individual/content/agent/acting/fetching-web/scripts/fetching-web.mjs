// fetching-web: URL → web-document
// Variance: restriction of articulating-class to HTTP-fetching enactor.
// Aperiodic morphism: each fetch may return novel content (web is aperiodic).

/**
 * @param {string} url
 * @param {{method?: string, headers?: Record<string,string>, body?: string, fetchImpl?: typeof fetch}} [options]
 * @returns {Promise<{url: string, status: number, headers: Record<string,string>, body: string, fetchedAt: string}>}
 */
export default async function fetchingWeb(url, options = {}) {
  if (typeof url !== "string" || url.length === 0) {
    throw new Error("fetching-web: url must be a non-empty string");
  }
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: options.method ?? "GET",
    headers: options.headers,
    body: options.body
  });
  const body = await response.text();
  const headers = {};
  if (typeof response.headers?.forEach === "function") {
    response.headers.forEach((v, k) => {
      headers[k] = v;
    });
  } else if (response.headers && typeof response.headers === "object") {
    Object.assign(headers, response.headers);
  }
  return {
    url,
    status: response.status,
    headers,
    body,
    fetchedAt: new Date().toISOString()
  };
}
