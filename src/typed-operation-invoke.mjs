import { admit } from "@red-cup-engineering/signcell/type-system";
import { parseJsonValue, requireJsonValue, canonicalJson } from "@red-cup-engineering/json-services-section";
import {
  TYPED_OPERATION_MESSAGE_VERSION,
  TYPED_OPERATION_REFUSAL_KIND,
  TYPED_OPERATION_RESULT_KIND,
  typedOperationRequestType,
} from "./typed-operation-message.mjs";

// RFC 8259 remains the original v1 message mode. RFC 8785 is a distinct
// requested codec rather than a silent re-encoding of historical JSON bodies.
// Both use Computer Data's original JSON admission/canonicalizer.
const CODECS = Object.freeze({
  json: Object.freeze({
    decode: parseJsonValue,
    encode: (value) => JSON.stringify(requireJsonValue(value)),
  }),
  jcs: Object.freeze({
    decode: (text) => {
      const value = parseJsonValue(text);
      if (canonicalJson(value) !== text) {
        throw new TypeError("RFC 8785 JCS input must already be canonical");
      }
      return value;
    },
    encode: canonicalJson,
  }),
});

function refusalMessage(requestId, code, message) {
  return Object.freeze({
    version: TYPED_OPERATION_MESSAGE_VERSION,
    kind: TYPED_OPERATION_REFUSAL_KIND,
    requestId: typeof requestId === "string" && requestId !== "" ? requestId : "unknown",
    code,
    message,
  });
}

function resultMessage(requestId, outputCodec, output) {
  return Object.freeze({ version: TYPED_OPERATION_MESSAGE_VERSION, kind: TYPED_OPERATION_RESULT_KIND, requestId, outputCodec, output });
}

/**
 * Invoke one operation registered under `operations` against a
 * typed-operation-request message. This is the Computer Code
 * composition boundary every content-typed engine (text, markdown, and so
 * on) dispatches through rather than reimplementing its own admission,
 * codec, and refusal handling: it admits the request against
 * Computer Code's own typed-operation-message contract, decodes and
 * encodes by the request's declared codec, invokes the registered handler,
 * and reports every failure as a typed-operation-refusal instead of
 * throwing.
 *
 * @param {{operations: Record<string, (input: unknown) => unknown>, request: unknown}} invocation
 * @returns {Promise<Readonly<Record<string, unknown>>>} A typed-operation-result or typed-operation-refusal message.
 */
export async function invokeTypedOperation({ operations, request } = {}) {
  if (operations === null || typeof operations !== "object" || Array.isArray(operations)) throw new TypeError("operations must be a registered operation table");
  const admission = admit(typedOperationRequestType, request);
  if (!admission.ok) {
    const detail = admission.refusal.issues.map((issue) => issue.message).join("; ") || "request does not satisfy typed-operation-request";
    return refusalMessage(request?.requestId, "malformed-request", detail);
  }
  const { requestId, operationId, inputCodec, input, outputCodec } = admission.value;
  const inCodec = Object.hasOwn(CODECS, inputCodec) ? CODECS[inputCodec] : undefined;
  const outCodec = Object.hasOwn(CODECS, outputCodec) ? CODECS[outputCodec] : undefined;
  if (!inCodec || !outCodec) return refusalMessage(requestId, "unsupported-codec", `unsupported codec ${inputCodec}/${outputCodec}`);
  const handler = Object.hasOwn(operations, operationId) ? operations[operationId] : undefined;
  if (typeof handler !== "function") return refusalMessage(requestId, "unknown-operation", `unknown operation ${operationId}`);
  let decoded;
  try {
    decoded = inCodec.decode(input);
  } catch (error) {
    return refusalMessage(requestId, "malformed-input", "input is not valid for the declared codec");
  }
  let output;
  try {
    output = await handler(decoded);
  } catch (error) {
    return refusalMessage(requestId, "operation-failed", "the declared operation failed");
  }
  try {
    const encoded = outCodec.encode(output);
    if (typeof encoded !== "string") throw new TypeError("output codec yielded no encoded value");
    return resultMessage(requestId, outputCodec, encoded);
  } catch {
    return refusalMessage(requestId, "malformed-output", "operation result is not encodable by the declared codec");
  }
}
