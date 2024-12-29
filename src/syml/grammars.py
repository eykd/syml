"""Parsimonious grammars for parsing SYML"""

import textwrap

syml_base_grammar = textwrap.dedent(
    """
    lines       = line*
    line        = indent (comment / blank / structure / value) &eol
    structure   = list_item / key_value / section

    indent      = ~"\\s*"

    blank       = &eol
    comment     = ~"(#|//+)+" text?

    list_item   = "-" ws value

    key_value   = section ws data
    section     = key ":"
    key         = ~"[^\\s:]+"

    eol         = "\\n" / ~"$"
    ws          = ~"[ \\t]+"
    text        = ~".+"

    value       = structure / data

    """
)


text_only_syml_grammar = syml_base_grammar + textwrap.dedent(
    """
    data        = text
    """
)

# If we want mare YAML-like booleans:
boolean_syml_grammar = syml_base_grammar + textwrap.dedent(
    """
    truthy      = "true" / "True" / "TRUE"
    falsey      = "false" / "False" / "FALSE"
    bool        = truthy / falsey

    data        = bool / text
    """
)
