# Specs Index (The Pin)

Read this before implementing any feature. When you search for a term and find it
here, follow the Spec path to the full specification. Keywords are intentionally
broad — synonyms, related terms, tech names, problem descriptions.

---

## syml 1.0 Spec Conformance

Keywords: syml 1.0, spec conformance, SYML-SPECIFICATION, parser conformance, literal values, no quoted strings (D18), case-restricted keys (D19), duplicate keys, DuplicateKeyError, tab indentation, TabIndentationError, BOM, CRLF normalization, pre-processing, multiline baseline, continuation lines, OutOfContextNodeError, sibling indentation, empty value returns empty string not None, error taxonomy, EncodingError, dumps, dump, serializer, round-trip, source tracking, Source, Pos, migration from 0.6.2, breaking changes, todo.txt retirement, release 1.0.0
Spec: specs/001-syml-1-0-conformance/spec.md

---

## How to Update This File

When adding a new spec via `/sp:02-specify`, the workflow updates this file
automatically. To update manually, append an entry using this format:

    ## Feature Name
    Keywords: kw1, kw2, kw3, ...  (10-20 terms: synonyms, related, tech, problems solved)
    Spec: specs/NNN-name/spec.md
