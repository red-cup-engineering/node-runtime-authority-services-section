// reading-file: file path → file-content
// Variance: restriction of articulating-class to filesystem-reading enactor.

import { readFile, stat } from "node:fs/promises";

/**
 * @param {string} filePath
 * @param {{encoding?: string}} [options]
 * @returns {Promise<{path: string, encoding: string, content: string, readAt: string, bytes: number}>}
 */
export default async function readingFile(filePath, options = {}) {
  if (typeof filePath !== "string" || filePath.length === 0) {
    throw new Error("reading-file: path must be a non-empty string");
  }
  const encoding = options.encoding ?? "utf8";
  const content = await readFile(filePath, encoding);
  const stats = await stat(filePath);
  return {
    path: filePath,
    encoding,
    content,
    readAt: new Date().toISOString(),
    bytes: stats.size
  };
}
