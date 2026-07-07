from backend.app.customer_support_agent import choose_route


def test_route_docs_for_policy_question() -> None:
    assert choose_route("What is your return policy?") == "docs"


def test_route_tools_for_order_question() -> None:
    assert choose_route("Can you track my order 1002?") == "tools"


def test_route_escalate_for_legal_issue() -> None:
    assert choose_route("I am considering legal action.") == "escalate"
