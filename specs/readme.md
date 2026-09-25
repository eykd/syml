# Specs Index (The Pin)

Read this before implementing any feature. When you search for a term and find it
here, follow the Spec path to the full specification. Keywords are intentionally
broad — synonyms, related terms, tech names, problem descriptions.

---

## syml 1.0 Spec Conformance

Keywords: syml 1.0, spec conformance, SYML-SPECIFICATION, parser conformance, literal values, no quoted strings (D18), case-restricted keys (D19), duplicate keys, DuplicateKeyError, tab indentation, TabIndentationError, BOM, CRLF normalization, pre-processing, multiline baseline, continuation lines, OutOfContextNodeError, sibling indentation, empty value returns empty string not None, error taxonomy, EncodingError, dumps, dump, serializer, round-trip, source tracking, Source, Pos, migration from 0.6.2, breaking changes, todo.txt retirement, release 1.0.0
Spec: specs/001-syml-1-0-conformance/spec.md

---

## SYML Language Revision — Values Are Just Text

Keywords: syml language revision, values are just text, text context, open text value, paragraph break, blank line in value, no comments, remove comments, # and // are text, key pattern, [a-z][a-z0-9_-]*, ASCII keys, uppercase keys are text, would-be key, strict indentation, indentless sequence rejected, list at key column, tab after colon, tab after dash, separator whitespace, NBSP indentation, Unicode whitespace, only U+0020 is indentation, root scalar leading spaces, ParseError str format, file:line:col, error hint, open columns, filename prefix, TabIndentationError position, dumps Source, as_source round-trip, dumps empty string, DocumentLimitError, EncodingError, os.PathLike filename, Coming from YAML, README YAML migration, D20–D25, break-test findings, syml-xreq, release 1.0.0 tag, human-friendly SYML, interactive fiction prose
Spec: specs/002-syml-language-revision/spec.md

---

## How to Update This File

When adding a new spec via `/sp:02-specify`, the workflow updates this file
automatically. To update manually, append an entry using this format:

    ## Feature Name
    Keywords: kw1, kw2, kw3, ...  (10-20 terms: synonyms, related, tech, problems solved)
    Spec: specs/NNN-name/spec.md
