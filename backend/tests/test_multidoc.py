"""Multi-document questions: every selected document is searched, conflicts are surfaced to the model, evidence gaps
are stated, and the selection is limited to documents the user owns. The LLM is a test double; these tests verify the
retrieval, prompt and citation logic around it."""

from tests.conftest import API, ask, new_conversation, new_user, ready_document
from tests.test_rag import use_llm

POLICY_2023 = "Employees accrue twenty days of annual leave under the 2023 leave policy."
POLICY_2024 = "Employees accrue twenty five days of annual leave under the 2024 leave policy."
Q = "How many days of annual leave do employees accrue under the leave policy?"


def _two_docs(client, h):
    a = ready_document(client, h, [POLICY_2023], "policy-2023.pdf")
    b = ready_document(client, h, [POLICY_2024], "policy-2024.pdf")
    return a, b, new_conversation(client, h)


def test_all_selected_documents_reach_the_model_and_are_cited_separately(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a, b, conv = _two_docs(client, h)
    fake = use_llm(monkeypatch, "policy-2023 says twenty days [S1] while policy-2024 says twenty five days [S2].")
    r = ask(client, h, conv["id"], Q, [a["id"], b["id"]])
    assert r.status_code == 201, r.text
    system, messages = fake.calls[0]
    prompt = messages[-1]["content"]
    assert "policy-2023.pdf" in prompt and "policy-2024.pdf" in prompt
    assert "conflict" in system.lower() and "do NOT merge" in system  # multi-document rules were added
    cites = r.json()["assistant_message"]["citations"]
    assert {c["document_name"] for c in cites} == {"policy-2023.pdf", "policy-2024.pdf"}
    assert {c["document_id"] for c in cites} == {a["id"], b["id"]}
    assert all(c["page_number"] == 1 and c["excerpt"] for c in cites)


def test_single_document_questions_do_not_get_the_multi_document_rules(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a, _, conv = _two_docs(client, h)
    fake = use_llm(monkeypatch, "Twenty days [S1].")
    assert ask(client, h, conv["id"], Q, [a["id"]]).status_code == 201
    assert "Several documents are involved" not in fake.calls[0][0]


def test_a_large_document_cannot_crowd_out_a_small_one(client, monkeypatch):
    h = new_user(client, "a@example.com")
    big = ready_document(client, h, [f"Annual leave policy section {i}: employees accrue annual leave days under the leave policy." for i in range(8)], "big.pdf")
    small = ready_document(client, h, ["The contractor leave policy: contractors accrue annual leave days only after one year."], "small.pdf")
    conv = new_conversation(client, h)
    fake = use_llm(monkeypatch, "Employees accrue leave [S1].")
    ask(client, h, conv["id"], "annual leave policy days accrue", [big["id"], small["id"]])
    prompt = fake.calls[0][1][-1]["content"]
    assert "small.pdf" in prompt and "big.pdf" in prompt


def test_missing_evidence_in_the_selection_is_stated_with_the_documents_searched(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a, b, conv = _two_docs(client, h)
    use_llm(monkeypatch, "INSUFFICIENT_EVIDENCE")
    r = ask(client, h, conv["id"], Q, [a["id"], b["id"]])
    msg = r.json()["assistant_message"]
    assert msg["citations"] == []
    assert "couldn't find enough evidence" in msg["content"]
    assert "policy-2023.pdf" in msg["content"] and "policy-2024.pdf" in msg["content"]


def test_answer_with_only_invented_citations_is_not_accepted(client, monkeypatch):
    h = new_user(client, "a@example.com")
    a, b, conv = _two_docs(client, h)
    use_llm(monkeypatch, "The moon is made of cheese [S7].")
    msg = ask(client, h, conv["id"], Q, [a["id"], b["id"]]).json()["assistant_message"]
    assert msg["citations"] == [] and "cheese" not in msg["content"]


def test_selection_cannot_include_another_users_or_unknown_documents(client, monkeypatch):
    a_h, b_h = new_user(client, "a@example.com"), new_user(client, "b@example.com")
    mine = ready_document(client, a_h, [POLICY_2023], "mine.pdf")
    theirs = ready_document(client, b_h, [POLICY_2024], "theirs.pdf")
    conv = new_conversation(client, a_h)
    fake = use_llm(monkeypatch, "x [S1]")
    r = ask(client, a_h, conv["id"], Q, [mine["id"], theirs["id"]])
    assert r.status_code == 404 and r.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert ask(client, a_h, conv["id"], Q, [mine["id"], 987654]).status_code == 404
    assert not fake.calls  # nothing was retrieved or sent to the model
    # Without a selection the search covers only the caller's own documents.
    use_llm(monkeypatch, "Twenty days [S1].")
    ok = ask(client, a_h, conv["id"], Q).json()["assistant_message"]
    assert {c["document_name"] for c in ok["citations"]} == {"mine.pdf"}


def test_selection_size_is_limited(client):
    h = new_user(client, "a@example.com")
    conv = new_conversation(client, h)
    assert ask(client, h, conv["id"], Q, list(range(1, 60))).status_code == 422
    r = ask(client, h, conv["id"], Q, list(range(1, 30)))
    assert r.status_code in (400, 404) and "error" in r.json()
