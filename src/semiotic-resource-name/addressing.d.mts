/** Canonical Code-owned type contract for addressed SEN path claims.
 * RFC 6920 NI commits to a canonical SEN envelope; it is not claim truth,
 * actor authorization, nor a decoded semantic term. */
export interface SemioticResourceNameClaim<Type = readonly unknown[], Term = readonly unknown[]> {
  readonly semanticType: Type;
  readonly term: Term;
}
export interface SemioticResourceNameAddress<Type = readonly unknown[], Term = readonly unknown[]> {
  readonly surface: string;
  readonly token: `ni:///sha-256;${string}`;
  readonly claim: SemioticResourceNameClaim<Type, Term>;
}
export interface SemioticResourceNameAddressCarrier {
  readonly surface: string;
  readonly bytes: Uint8Array;
  readonly token: `ni:///sha-256;${string}`;
}
/** Derive one source path surface as a typed SEN term and NI commitment. */
export declare function addressSemioticResourceName(surface: string): SemioticResourceNameAddress;
/** Check all transported coordinates against that source-derived address. */
export declare function assertSemioticResourceNameAddress(address: unknown): SemioticResourceNameAddress;
/** Nonthrowing source-address admission. */
export declare function verifySemioticResourceNameAddress(address: unknown): boolean;
/** Admit normalized SEN envelope bytes without decoding a token to meaning. */
export declare function admitSemioticResourceNameAddress(
  carrier: SemioticResourceNameAddressCarrier,
): SemioticResourceNameAddress;
