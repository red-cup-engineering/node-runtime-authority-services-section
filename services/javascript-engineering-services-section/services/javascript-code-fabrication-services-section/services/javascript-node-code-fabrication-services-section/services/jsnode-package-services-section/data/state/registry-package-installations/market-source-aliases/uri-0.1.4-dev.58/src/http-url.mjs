/** Admit a string as an absolute http(s) URL and return it, or throw a TypeError naming `field`. */
export function assertHttpUrl(value, field = "url") {
  if (typeof value !== "string" || !value.isWellFormed()) throw new TypeError(`${field} must be a well-formed Unicode absolute http(s) URL`);
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new TypeError(`${field} must be an absolute http(s) URL`);
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") throw new TypeError(`${field} must be an absolute http(s) URL`);
  return value;
}


/** Whether a declared browsing link has an absolute HTTPS address without
 * URI-template holes or embedded userinfo. This is a presentation predicate,
 * NOT SSRF admission, endpoint authority, availability or safe-browsing.
 * Consumers separately decide whether to render an actual link.
 */
export function isDirectHttpsHref(value) {
  if (typeof value !== "string" || !value.isWellFormed() ||
      value.includes("{") || value.includes("}") ||
      // WHATWG accepts and repairs "https:///other-host" or backslashes;
      // those source strings do not explicitly declare their actual authority.
      !/^https:\/\/[^/?#\s\\@]+(?:[/?#][^\s\\]*)?$/iu.test(value) ||
      // The browser parser can retain invalid percent escapes. A direct,
      // source-declared HTTP resource cannot silently reinterpret them.
      /%(?![0-9a-f]{2})/iu.test(value)) return false;
  try {
    const url = new URL(assertHttpUrl(value));
    return url.protocol === "https:" && url.username === "" && url.password === "";
  } catch {
    return false;
  }
}
