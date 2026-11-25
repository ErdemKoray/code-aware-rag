from dataclasses import FrozenInstanceError

import pytest
from tree_sitter import Node

from coderag.parsing.python import ParseResult, line_range, parse


def top_level(source: bytes) -> list[Node]:
    return parse(source).tree.root_node.named_children


def find_first(node: Node, node_type: str) -> Node:
    """Depth-first search for the first node of the given type."""
    if node.type == node_type:
        return node
    for child in node.children:
        try:
            return find_first(child, node_type)
        except LookupError:
            continue
    raise LookupError(node_type)


def text(result: ParseResult, node: Node) -> str:
    return result.source[node.start_byte : node.end_byte].decode("utf-8")


# --- parse: result object --------------------------------------------------


def test_parse_returns_tree_and_original_source():
    source = b"x = 1\n"

    result = parse(source)

    assert isinstance(result, ParseResult)
    assert result.source is source
    assert result.tree.root_node.type == "module"
    assert result.has_error is False


def test_parse_result_is_frozen():
    result = parse(b"x = 1\n")

    with pytest.raises(FrozenInstanceError):
        result.source = b""  # type: ignore[misc]


def test_parse_calls_do_not_share_state():
    first = parse(b"def a(): ...\n")
    second = parse(b"class B: ...\n")

    assert [n.type for n in first.tree.root_node.named_children] == ["function_definition"]
    assert [n.type for n in second.tree.root_node.named_children] == ["class_definition"]


# --- parse: node shapes we depend on ---------------------------------------


def test_async_function_is_a_function_definition_with_an_async_token():
    (function,) = top_level(b"async def f(a, b: int = 1) -> int:\n    return a\n")

    assert function.type == "function_definition"
    assert function.children[0].type == "async"
    assert function.child_by_field_name("name").text == b"f"
    assert function.child_by_field_name("parameters").type == "parameters"
    assert function.child_by_field_name("return_type").type == "type"
    assert function.child_by_field_name("body").type == "block"


def test_plain_function_has_no_async_token():
    (function,) = top_level(b"def f():\n    pass\n")

    assert function.type == "function_definition"
    assert "async" not in [child.type for child in function.children]


def test_decorated_definition_wraps_decorators_and_definition():
    (decorated,) = top_level(b"@app.get('/x')\n@other\ndef f():\n    pass\n")

    assert decorated.type == "decorated_definition"
    assert [child.type for child in decorated.named_children] == [
        "decorator",
        "decorator",
        "function_definition",
    ]
    definition = decorated.child_by_field_name("definition")
    assert definition.type == "function_definition"
    assert definition.child_by_field_name("name").text == b"f"
    # `decorator` is a child node type, not a field name.
    assert decorated.child_by_field_name("decorator") is None


def test_decorated_class_definition():
    (decorated,) = top_level(b"@dataclass\nclass A:\n    x: int = 0\n")

    assert decorated.child_by_field_name("definition").type == "class_definition"


def test_nested_class_and_method_live_in_the_outer_body():
    (outer,) = top_level(
        b"class Outer(Base):\n    class Inner:\n        x = 1\n\n    def m(self):\n        pass\n"
    )

    assert outer.type == "class_definition"
    assert outer.child_by_field_name("name").text == b"Outer"
    assert outer.child_by_field_name("superclasses").type == "argument_list"
    body = outer.child_by_field_name("body")
    assert [child.type for child in body.named_children] == [
        "class_definition",
        "function_definition",
    ]
    inner, method = body.named_children
    assert inner.child_by_field_name("name").text == b"Inner"
    assert method.child_by_field_name("name").text == b"m"


def test_comments_are_top_level_named_nodes():
    nodes = top_level(b"# top\n\ndef f(): ...\n")

    assert [node.type for node in nodes] == ["comment", "function_definition"]


def test_non_ascii_source_uses_byte_offsets():
    source = "# caf\u00e9\nname = 'na\u00efve'\n".encode()
    result = parse(source)

    assignment = find_first(result.tree.root_node, "assignment")

    assert text(result, assignment) == "name = 'na\u00efve'"
    assert assignment.start_byte != assignment.start_point.column  # bytes, not characters


# --- parse: edge inputs ----------------------------------------------------


def test_empty_source_parses_to_an_empty_module():
    result = parse(b"")

    assert result.tree.root_node.type == "module"
    assert result.tree.root_node.named_children == []
    assert result.has_error is False


def test_source_without_trailing_newline_parses():
    result = parse(b"def f():\n    pass")

    assert result.has_error is False
    assert [n.type for n in result.tree.root_node.named_children] == ["function_definition"]


def test_crlf_line_endings_parse_like_lf():
    result = parse(b"def f():\r\n    pass\r\n")

    assert result.has_error is False
    assert [n.type for n in result.tree.root_node.named_children] == ["function_definition"]


# --- parse: broken syntax --------------------------------------------------


def test_syntax_error_does_not_raise_and_sets_has_error():
    result = parse(b"def f(:\n    pass\n")

    assert result.has_error is True


def test_parser_recovers_and_keeps_definitions_around_the_error():
    result = parse(b"def f(:\n    pass\n\nclass B:\n    x = 1\n")

    assert result.has_error is True
    assert [n.type for n in result.tree.root_node.named_children] == [
        "function_definition",
        "class_definition",
    ]


def test_unclosed_bracket_yields_an_error_node():
    result = parse(b"x = (1, 2\n")

    assert result.has_error is True
    assert result.tree.root_node.named_children[0].type == "ERROR"


@pytest.mark.parametrize(
    "source",
    [b"def (:\n", b"class\n", b"x = = 1\n", b"\xff\xfe invalid utf8 \xfa\n", b"@\n"],
)
def test_garbage_never_raises(source):
    result = parse(source)

    assert result.tree.root_node.type == "module"
    assert isinstance(result.has_error, bool)


# --- line_range ------------------------------------------------------------


def test_line_range_is_one_based_and_inclusive():
    (function,) = top_level(b"def f():\n    pass\n")

    assert line_range(function) == (1, 2)


def test_line_range_of_a_single_line_node():
    (function,) = top_level(b"def f(): ...\n")

    assert line_range(function) == (1, 1)


def test_line_range_of_decorated_definition_includes_decorators():
    (decorated,) = top_level(b"@a\n@b\ndef f():\n    pass\n")

    assert line_range(decorated) == (1, 4)
    assert line_range(decorated.child_by_field_name("definition")) == (3, 4)


def test_line_range_ignores_blank_lines_after_a_node():
    function, statement = top_level(b"def f():\n    pass\n\n\nx = 1\n")

    assert line_range(function) == (1, 2)
    assert line_range(statement) == (5, 5)


def test_line_range_module_ending_at_column_zero_does_not_add_a_line():
    # The module ends at row 2, column 0 (after the final newline): it covers lines 1-2.
    root = parse(b"def f():\n    pass\n").tree.root_node

    assert (root.end_point.row, root.end_point.column) == (2, 0)
    assert line_range(root) == (1, 2)


def test_line_range_module_without_trailing_newline():
    root = parse(b"def f():\n    pass").tree.root_node

    assert line_range(root) == (1, 2)


def test_line_range_of_empty_module():
    root = parse(b"").tree.root_node

    assert line_range(root) == (1, 1)


def test_line_range_string_content_ending_before_closing_quotes_at_column_zero():
    # The closing quotes start line 3, so the text inside the string covers lines 1-2
    # while the whole string covers lines 1-3.
    result = parse(b'x = """\nabc\n"""\n')
    string = find_first(result.tree.root_node, "string")
    content = find_first(result.tree.root_node, "string_content")

    assert (content.end_point.row, content.end_point.column) == (2, 0)
    assert line_range(content) == (1, 2)
    assert line_range(string) == (1, 3)


def test_line_range_line_continuation_does_not_add_a_line():
    result = parse(b"x = 1 \\\n")
    continuation = find_first(result.tree.root_node, "line_continuation")

    assert line_range(continuation) == (1, 1)


def test_line_range_zero_width_node_on_one_row():
    # tree-sitter inserts a zero-width MISSING ")" for "def f(:".
    result = parse(b"def f(:\n    pass\n")
    missing = find_first(result.tree.root_node, ")")

    assert missing.is_missing
    assert line_range(missing) == (1, 1)
