/**
 * Minimal GitHub REST client (REST API, API version 2022-11-28). `fetchImpl` is injectable for tests.
 * Pagination follows the `Link: <...>; rel="next"` header (RFC 8288).
 */
/** The array inside a list response: the body itself, or its one array-valued member. */
export function listOf(data, path = "") {
  if (Array.isArray(data)) return data;
  const arrays = Object.values(data ?? {}).filter(Array.isArray);
  if (arrays.length !== 1) throw new Error(`${path}: list response has ${arrays.length} array members, expected 1`);
  return arrays[0];
}

/**
 * `budgetFloor`: every token of one GitHub user shares that user's hourly budget per resource (core, graphql,
 * search). Once a response reports fewer than `budgetFloor` requests remaining, later requests to that
 * resource fail at once with status 429 and code GITHUB_BUDGET_FLOOR, so a batch operation stops itself
 * instead of spending the budget every other caller needs (https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
 *
 * `token` is a token, or `(account) => token` for a GitHub App (github-app.mjs `installationTokens`): each
 * request is then made as the installation of the account it names (`/repos/{owner}`, `/orgs/{org}`,
 * `/users/{owner}`, or a GraphQL query's `owner` variable), and each account's budget is kept apart.
 */
/** The account a request names: its path's owner, or a GraphQL query's `owner` variable. */
export const accountOf = (path, body) => (/^\/(?:repos|orgs|users)\/([^/?]+)/u.exec(path)?.[1] ?? body?.variables?.owner ?? null)?.toLowerCase() ?? null;

/**
 * How long to wait out a secondary rate limit (403 or 429 saying so, or carrying `retry-after`), as GitHub prescribes
 * (https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api#exceeding-the-rate-limit):
 * `retry-after` seconds; else, with none remaining, until `x-ratelimit-reset`; else a minute, doubling per attempt.
 * Null when the response is no secondary limit, or the wait is past `maxWaitMs`.
 */
export function secondaryLimitWait({ status, headers, message, attempt, now = Date.now(), maxWaitMs = 15 * 60_000 }) {
  if (![403, 429].includes(status) || !(headers.has("retry-after") || /secondary rate limit/iu.test(message ?? ""))) return null;
  const after = Number(headers.get("retry-after")), reset = Number(headers.get("x-ratelimit-reset"));
  const wait = Number.isFinite(after) && after >= 0 && headers.has("retry-after") ? after * 1000
    : headers.get("x-ratelimit-remaining") === "0" && Number.isFinite(reset) ? Math.max(0, reset * 1000 - now)
      : 60_000 * 2 ** attempt;
  return wait <= maxWaitMs ? wait : null;
}

export function createClient({ token, fetchImpl = globalThis.fetch, base = "https://api.github.com", budgetFloor = 0, secondaryRetries = 3,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) }) {
  const remaining = new Map(), resets = new Map(), perAccount = typeof token === "function";
  const resourceOf = (path) => (path.startsWith("/graphql") ? "graphql" : path.startsWith("/search/") ? "search" : "core");
  const keyOf = (resource, account) => (perAccount ? `${account ?? ""}:${resource}` : resource);
  /** Whether `resource` (of `account`, for an App) is below the floor now; a window past its `X-RateLimit-Reset` is full again. */
  const belowFloor = (resource = "core", account = null) => budgetFloor > 0 && (remaining.get(keyOf(resource, account)) ?? Infinity) < budgetFloor
    && Date.now() < (resets.get(keyOf(resource, account)) ?? Infinity) * 1000;
  async function raw(method, path, body, paginationAccount) {
    const target = new URL(path, base);
    if (target.origin !== new URL(base).origin || target.username || target.password)
      throw new Error("GitHub provider URL left the configured API origin");
    const requestPath = target.pathname + target.search;
    const namedAccount = perAccount ? accountOf(requestPath, body) : null;
    if (perAccount && paginationAccount !== undefined && namedAccount !== null && namedAccount !== paginationAccount)
      throw new Error("GitHub pagination left the originating account");
    const resource = resourceOf(requestPath);
    const account = perAccount ? (paginationAccount === undefined ? namedAccount : paginationAccount) : null;
    if (belowFloor(resource, account)) {
      const error = new Error(`${method} ${path}: GitHub ${resource} budget below ${budgetFloor} (GITHUB_BUDGET_FLOOR); stopped so other callers keep theirs`);
      error.status = 429;
      error.code = "GITHUB_BUDGET_FLOOR";
      throw error;
    }
    const credential = perAccount ? await token(account) : token;
    const send = () => fetchImpl(target.href, {
      method,
      redirect: "error",
      signal: AbortSignal.timeout(30_000),
      headers: {
        accept: "application/vnd.github+json",
        "x-github-api-version": "2022-11-28",
        "user-agent": "github-engineering-services-section estate-reconcile",
        ...(credential ? { authorization: `Bearer ${credential}` } : {}),
        ...(body ? { "content-type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    let response = await send();
    // a secondary rate limit is waited out as GitHub prescribes, never reported as an unread
    for (let attempt = 0; attempt < secondaryRetries && [403, 429].includes(response.status); attempt += 1) {
      const said = typeof response.clone === "function" ? await response.clone().text().catch(() => "") : "";
      const wait = secondaryLimitWait({ status: response.status, headers: response.headers, message: said, attempt });
      if (wait === null) break;
      await sleep(wait);
      response = await send();
    }
    if (response.headers.has("x-ratelimit-remaining")) {
      const kind = keyOf(response.headers.get("x-ratelimit-resource") ?? resource, account);
      remaining.set(kind, Number(response.headers.get("x-ratelimit-remaining")));
      if (response.headers.has("x-ratelimit-reset")) resets.set(kind, Number(response.headers.get("x-ratelimit-reset")));
    }
    if (response.status === 204) return { data: null, response };
    const text = await response.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); }
      catch {
        // An HTML/text error body must not erase the observed HTTP failure.
        // A malformed success is still refused, never read as empty data.
        if (response.ok) throw Object.assign(
          new Error(`GitHub provider BAD_PROVIDER_JSON: HTTP ${response.status}`),
          { code: "BAD_PROVIDER_JSON", status: response.status });
      }
    }
    if (!response.ok) {
      const error = new Error(`${method} ${path}: ${response.status} ${data?.message ?? ""}`.trim());
      error.status = response.status;
      throw error;
    }
    return { data, response };
  }
  return {
    belowFloor,
    /**
     * Whether requests are made as a GitHub App's installations: an installation is no collaborator, so a
     * repository's viewerPermission and permissions say nothing of it (REST reports push false where its
     * installation has contents: write); its installation's permissions decide, and the write itself is the check.
     */
    app: perAccount,
    request: async (method, path, body) => (await raw(method, path, body)).data,
    /**
     * All items of a list endpoint. GitHub returns either an array or an object wrapping the array
     * (`{ total_count, check_runs: [...] }`, `{ items }`); both are read. A page limit reached with a
     * `rel="next"` still pending throws: a truncated list is missing evidence, never an empty one.
     */
    async paginate(path, { maxPages = 10 } = {}) {
      const items = [];
      // Link URLs may replace /repos/owner/name with /repositories/id.
      // Keep the installation and its budget from the initiating request.
      const start = new URL(path, base);
      const paginationAccount = perAccount ? accountOf(start.pathname + start.search) : undefined;
      let next = path + (path.includes("?") ? "&" : "?") + "per_page=100";
      for (let page = 0; next; page += 1) {
        if (page >= maxPages) throw new Error(`${path}: more than ${maxPages} pages; list truncated`);
        const { data, response } = await raw("GET", next, undefined, paginationAccount);
        items.push(...listOf(data, path));
        next = /<([^>]+)>;\s*rel="next"/u.exec(response.headers.get("link") ?? "")?.[1] ?? null;
      }
      return items;
    },
  };
}
