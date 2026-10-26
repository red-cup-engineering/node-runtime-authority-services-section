// The house RFC 6920 ("Naming Things with Hashes") module: builds and
// validates the narrow `ni:///sha-256;<base64url-digest>` content-identity URI
// that every house content address is written in.
import { sha256Bytes } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/portable-sha256";
import { decodeJsonByteCarrier } from "@red-cup-engineering/json-services-section/json-byte-carrier";

function base64url(bytes) {
  let text = "";
  for (const byte of bytes) text += String.fromCharCode(byte);
  return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64url(value) {
  const text = atob(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4));
  return Uint8Array.from(text, (character) => character.charCodeAt(0));
}

function sha256(bytes) {
  const hex = sha256Bytes(bytes);
  return Uint8Array.from(hex.match(/../g), (pair) => Number.parseInt(pair, 16));
}

const NI_PREFIX = "ni:///sha-256;";

// RFC 6920 base64url digests of a 32-byte SHA-256 hash are exactly 43
// characters without padding. The last character contains four digest bits
// and two zero pad bits, so only every fourth base64url character is canonical.
// Enforcing that final sextet prevents four different URI strings from naming
// the same digest bytes.
export const NI_URI_PATTERN = /^ni:\/\/\/sha-256;[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$/u;

function fail(message) {
  const error = new Error(message);
  error.code = "invalid-ni-uri";
  throw error;
}

function byteString(value) {
  if (!(value instanceof Uint8Array)) {
    throw new TypeError("ni URI input must be a Uint8Array");
  }
  return value;
}

function digestBytes(value) {
  if (typeof value !== "string" || !NI_URI_PATTERN.test(value)) return null;
  const encoded = value.slice(NI_PREFIX.length);
  const digest = fromBase64url(encoded);
  return digest.length === 32 && base64url(digest) === encoded
    ? digest
    : null;
}

// Build the `ni:` URI for the given bytes, digesting them with SHA-256 and
// base64url-encoding the result per RFC 6920.
export function makeNiUri(bytes) {
  const digest = base64url(sha256(byteString(bytes)));
  return `${NI_PREFIX}${digest}`;
}

// Report whether a value is a well-formed sha-256 `ni:` URI. The pattern alone decides it: 42
// base64url characters and a canonical final one are exactly 256 bits, so they always decode to 32
// bytes that encode back to the same text; decoding to check again was most of a store walk's time.
export function isNiUri(value) {
  return typeof value === "string" && NI_URI_PATTERN.test(value);
}

// Extract the base64url digest from a validated sha-256 `ni:` URI, throwing
// on anything that does not match the RFC 6920 sha-256 form.
export function niUriDigest(value) {
  if (!isNiUri(value)) fail(`invalid sha-256 ni URI ${JSON.stringify(value)}`);
  return value.slice(NI_PREFIX.length);
}

// Recover the named 32-byte SHA-256 digest from a canonical URI.
export function niUriDigestBytes(value) {
  const digest = digestBytes(value);
  if (digest === null) fail(`invalid sha-256 ni URI ${JSON.stringify(value)}`);
  return digest.slice();
}

// Verify the complete receiver-facing relation: these exact bytes must hash
// to this exact canonical RFC 6920 name.
export function verifyNiUri(bytes, value) {
  if (!isNiUri(value)) return false;
  return makeNiUri(bytes) === value;
}

/** {bytesBase64 | text, algorithm?} -> {uri}: the ni: name of bytes or UTF-8 text. */
export function makeNiUriService(request) {
  const hasBytes = typeof request?.bytesBase64 === "string";
  const hasText = typeof request?.text === "string";
  if (hasBytes === hasText) throw new TypeError("exactly one of bytesBase64 or text is required");
  if (request.algorithm !== undefined && request.algorithm !== "sha-256") {
    throw new TypeError(`unsupported ni URI algorithm ${JSON.stringify(request.algorithm)}; only sha-256 is available`);
  }
  if (hasText && !request.text.isWellFormed()) throw new TypeError("text must be well-formed Unicode");
  const bytes = hasBytes
    ? Uint8Array.from(decodeJsonByteCarrier({carrier:{mediaType:"application/octet-stream",contentBase64:request.bytesBase64}}).bytes)
    : new TextEncoder().encode(request.text);
  return { uri: makeNiUri(bytes) };
}

/** {uri} -> {algorithm, digest}: a validated sha-256 ni: URI taken apart. */
export function parseNiUri(request) {
  if (typeof request?.uri !== "string") throw new TypeError("uri must be a string");
  if (!isNiUri(request.uri)) throw new TypeError(`invalid sha-256 ni URI ${JSON.stringify(request.uri)}`);
  return { algorithm: "sha-256", digest: niUriDigest(request.uri) };
}

// RFC 6920 sections 3-4: the canonical digest names bytes. Metadata
// in the optional query is a distinct coordinate and survives HTTP mapping.
const NI_QUERY_PATTERN = /^(?:[A-Za-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9A-Fa-f]{2})*$/u;

function niReference(value) {
  if (typeof value !== "string") return null;
  const split = value.indexOf("?");
  const name = split < 0 ? value : value.slice(0, split);
  const query = split < 0 ? null : value.slice(split + 1);
  if (!isNiUri(name) || (query !== null && !NI_QUERY_PATTERN.test(query))) return null;
  try {
    if (query !== null) decodeURIComponent(query);
  } catch {
    return null;
  }
  return { name, query };
}

function niQueryParameters(query) {
  // RFC 3986 query "+" is literal; URLSearchParams otherwise decodes it as space.
  return new URLSearchParams((query ?? "").replaceAll("+", "%2B"));
}

export function niUriName(value) {
  return niReference(value)?.name ?? null;
}

export function niUriContentType(value) {
  const reference = niReference(value);
  if (!reference || reference.query === null) return null;
  const values = niQueryParameters(reference.query).getAll("ct");
  return values.length === 1 ? values[0] : null;
}

export function niUriWithContentType(value, contentType) {
  const reference = niReference(value);
  if (!reference) fail(`invalid sha-256 ni URI ${JSON.stringify(value)}`);
  if (typeof contentType !== "string" || !contentType.isWellFormed()) {
    throw new TypeError("contentType must be a well-formed MIME media type");
  }
  const mediaType = contentType.trim();
  if (!/^[^\s/;]+\/[^\s/;]+(?:[ \t]*;[^\r\n]*)?$/u.test(mediaType) ||
      /[\u0000-\u001f\u007f]/u.test(mediaType)) {
    throw new TypeError("contentType must be a MIME media type without control characters");
  }
  const query = niQueryParameters(reference.query);
  query.set("ct", mediaType);
  // URLSearchParams writes form spaces as "+", but in an RFC 3986 URI
  // query "+" is a literal plus. Emit URI-safe %20 instead.
  return `${reference.name}?${query.toString().replaceAll("+", "%20")}`;
}

// RFC 6920 section 4 maps the complete query to /.well-known/ni/.
export const NI_WELL_KNOWN_PREFIX = "/.well-known/ni/sha-256/";
export function niWellKnownPath(value) {
  const reference = niReference(value);
  if (!reference) fail(`invalid sha-256 ni URI ${JSON.stringify(value)}`);
  return `${NI_WELL_KNOWN_PREFIX}${niUriDigest(reference.name)}${reference.query === null ? "" : `?${reference.query}`}`;
}
export function niUriOfWellKnownPath(path) {
  if (typeof path !== "string" || !path.startsWith(NI_WELL_KNOWN_PREFIX)) return null;
  const reference = `${NI_PREFIX}${path.slice(NI_WELL_KNOWN_PREFIX.length)}`;
  return niReference(reference) ? reference : null;
}
