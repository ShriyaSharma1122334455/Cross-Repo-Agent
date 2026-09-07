; ES module named import, optionally aliased: import { x as y } from "pkg"
(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @import.name
        alias: (identifier)? @import.alias)))
  source: (string (string_fragment) @import.source))

; ES module default import: import x from "pkg" — binds the whole module.
(import_statement
  (import_clause
    (identifier) @import.default)
  source: (string (string_fragment) @import.source))

; ES module namespace import: import * as x from "pkg" — binds the whole module.
(import_statement
  (import_clause
    (namespace_import
      (identifier) @import.namespace))
  source: (string (string_fragment) @import.source))

; CommonJS require("pkg") — the enclosing variable_declarator's binding
; pattern (identifier / object_pattern) is inspected in Python, since
; that structural walk isn't expressible as a single query pattern.
((call_expression
  function: (identifier) @import.require_fn
  arguments: (arguments (string (string_fragment) @import.source))) @import.require_call
 (#eq? @import.require_fn "require"))
