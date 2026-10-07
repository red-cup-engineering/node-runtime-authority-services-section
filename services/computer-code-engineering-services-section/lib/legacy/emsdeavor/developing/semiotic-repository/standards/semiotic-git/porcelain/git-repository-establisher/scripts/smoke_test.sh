#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="${TMPDIR:-/tmp}/establish-smoke-$$"

cleanup() {
  rm -rf "${tmp}"
}
trap cleanup EXIT

python3 "${root}/establish.py" list-templates >/dev/null

mk_repo() {
  local template="$1"
  local out="${tmp}/${template}"
  python3 "${root}/establish.py" init \
    --template "${template}" \
    --output-path "${out}" \
    --name "Smoke ${template}" \
    --description "smoke" \
    --author "Smoke" \
    --contact-email "smoke@example.com" \
    --license-id MIT \
    --github-owner smoke-org \
    --github-repo "smoke-${template}" \
    --no-git
  test -f "${out}/README.md"
  test -f "${out}/LICENSE"

  case "${template}" in
    math-paper)
      test -f "${out}/Makefile"
      test -f "${out}/CITATION.cff"
      test -f "${out}/smoke-${template}.md"
      ;;
    *)
      test -f "${out}/CHANGELOG.md"
      test -f "${out}/TODO.md"
      test -f "${out}/AGENTS.md"
      test -f "${out}/.githooks/pre-commit"
      test -f "${out}/.github/ISSUE_TEMPLATE/bug_report.yml"
      test -f "${out}/.github/CODEOWNERS"
      ;;
  esac
}

mk_repo basic
mk_repo math-paper
mk_repo python-package
mk_repo rust-crate
mk_repo research-notes
mk_repo markdown-vault
mk_repo mkdocs-site
mk_repo specs

echo "OK: ${tmp}"
