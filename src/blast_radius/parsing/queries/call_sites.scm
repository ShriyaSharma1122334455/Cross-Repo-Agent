; Direct call: charge(...) — callee resolved against local names bound
; directly to the symbol (named/destructured import or alias).
(call_expression
  function: (identifier) @call.callee
  arguments: (arguments) @call.args) @call.expr

; Member call: lib.charge(...) — callee resolved against local names bound
; to the whole module (default/namespace import, or `const lib = require(...)`).
(call_expression
  function: (member_expression
    object: (identifier) @call.object
    property: (property_identifier) @call.property)
  arguments: (arguments) @call.args) @call.expr
