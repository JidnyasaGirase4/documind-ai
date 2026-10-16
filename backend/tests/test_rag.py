"""RAG behaviour: valid citations, honest insufficient-evidence answers and LLM failure handling.

The LLM is replaced by a test double in most tests, and by mocked HTTP in the provider tests. These
doubles verify our logic; they are not live AI."""

import httpx

from app.core.config import settings
from app.services import rag_service, vector_service
from app.services.llm_service import MOCK_PREFIX
from tests.conftest import API, PARENTAL, WARRANTY, ask, new_conversation, new_user, ready_document, upload


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def generate(self, system, messages):
        self.calls.append((system, messages))
        return self.reply(messages) if callable(self.reply) else self.reply


def use_llm(monkeypatch, reply) -> FakeLLM:
    fake = FakeLLM(reply)
    monkeypatch.setattr(rag_service, "get_llm", lambda: fake)
    return fake


def setup_user_with_doc(client, pages=(PARENTAL, WARRANTY), email="a@example.com"):
    h = new_user(client, email)
    doc = ready_document(client, h, list(pages), "handbook.pdf")
    return h, doc, new_conversation(client, h)


def test_answer_has_citations_that_match_the_retrieved_chunk(client, monkeypatch):
    h, doc, conv = setup_user_with_doc(client)
    fake = use_llm(monkeypatch, "Primary caregivers get sixteen weeks of paid leave [S1].")

    r = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?")
    assert r.status_code == 201, r.text
    answer = r.json()["assistant_message"]
    assert "[S1]" in answer["content"]
    assert len(answer["citations"]) == 1
    c = answer["citations"][0]
    assert c["document_id"] == doc["id"] and c["document_name"] == "handbook.pdf"
    assert c["page_number"] == 1  # the parental-leave text is on page 1, not page 2
    assert "sixteen weeks" in c["excerpt"]
    # The citation points at a vector that really exists in the index.
    assert vector_service._collection().get(ids=[c["chunk_id"]])["ids"] == [c["chunk_id"]]

    system, messages = fake.calls[0]
    assert "ONLY" in system and "untrusted" in system  # grounded, injection-aware instructions
    last = messages[-1]["content"]
    assert "handbook.pdf" in last and "sixteen weeks" in last and "Question:" in last


def test_invalid_citation_markers_are_dropped_and_valid_ones_renumbered(client, monkeypatch):
    pages = ["paid parental leave policy for primary caregivers", "paid parental leave policy for secondary caregivers"]
    h, doc, conv = setup_user_with_doc(client, pages)
    use_llm(monkeypatch, "First [S2] then invented [S9] then [S1].")
    r = ask(client, h, conv["id"], "paid parental leave policy caregivers")
    answer = r.json()["assistant_message"]
    assert "[S9]" not in answer["content"]
    assert "[S1]" in answer["content"] and "[S2]" in answer["content"]
    assert sorted(c["page_number"] for c in answer["citations"]) == [1, 2]


def test_answer_without_any_valid_citation_becomes_insufficient_evidence(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    use_llm(monkeypatch, "Sixteen weeks, trust me. [S7]")
    answer = ask(client, h, conv["id"], "paid parental leave weeks").json()["assistant_message"]
    assert answer["content"] == rag_service.INSUFFICIENT_MESSAGE
    assert answer["citations"] == []


def test_model_can_report_insufficient_evidence(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    use_llm(monkeypatch, "INSUFFICIENT_EVIDENCE")
    answer = ask(client, h, conv["id"], "paid parental leave weeks").json()["assistant_message"]
    assert answer["content"] == rag_service.INSUFFICIENT_MESSAGE and answer["citations"] == []


def test_no_relevant_passages_means_no_llm_call_and_no_citations(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    fake = use_llm(monkeypatch, "should never be used [S1]")
    answer = ask(client, h, conv["id"], "volcano magma basalt eruption lava").json()["assistant_message"]
    assert answer["content"] == rag_service.INSUFFICIENT_MESSAGE
    assert answer["citations"] == []
    assert fake.calls == []


def test_other_users_documents_cannot_be_used_or_leak(client, monkeypatch):
    a = new_user(client, "a@example.com")
    doc_a = ready_document(client, a, [PARENTAL])
    b = new_user(client, "b@example.com")
    conv_b = new_conversation(client, b)
    fake = use_llm(monkeypatch, "leak [S1]")

    # Selecting someone else's document is refused.
    r = ask(client, b, conv_b["id"], "paid parental leave weeks", [doc_a["id"]])
    assert r.status_code == 404 and r.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    # With no documents of their own, there is nothing to search.
    r = ask(client, b, conv_b["id"], "paid parental leave weeks")
    assert r.status_code == 400 and r.json()["error"]["code"] == "NO_READY_DOCUMENTS"
    # With a different document of their own, A's text is never retrieved.
    ready_document(client, b, [WARRANTY])
    answer = ask(client, b, conv_b["id"], "paid parental leave weeks sixteen caregivers").json()["assistant_message"]
    assert answer["content"] == rag_service.INSUFFICIENT_MESSAGE
    assert fake.calls == []


def test_documents_that_are_not_ready_cannot_be_queried(client):
    h = new_user(client, "a@example.com")
    failed = upload(client, h, ["", ""], "scan.pdf").json()
    conv = new_conversation(client, h)
    r = ask(client, h, conv["id"], "anything", [failed["id"]])
    assert r.status_code == 409 and r.json()["error"]["code"] == "DOCUMENT_NOT_READY"


def test_follow_up_questions_send_prior_turns_without_citation_markers(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    fake = use_llm(monkeypatch, "Sixteen weeks [S1].")
    ask(client, h, conv["id"], "paid parental leave primary caregivers weeks")
    ask(client, h, conv["id"], "and for secondary caregivers paid leave weeks")
    _, messages = fake.calls[1]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert "[S" not in messages[1]["content"]


def test_dev_mock_provider_is_clearly_labelled_and_still_cites(client):
    h, doc, conv = setup_user_with_doc(client)
    answer = ask(client, h, conv["id"], "paid parental leave primary caregivers weeks").json()["assistant_message"]
    assert answer["content"].startswith(MOCK_PREFIX)
    assert answer["citations"] and answer["citations"][0]["document_id"] == doc["id"]


# ------------------------------------------------------- LLM failure handling
def _anthropic(monkeypatch, post):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr("app.services.llm_service.httpx.post", post)


def _status_error(status):
    def post(*_, **__):
        return httpx.Response(status, request=httpx.Request("POST", "https://api.example.test"), json={"error": "x"})

    return post


def _messages_of(client, h, conv_id):
    return client.get(f"{API}/conversations/{conv_id}", headers=h).json()["messages"]


def test_llm_timeout_rate_limit_and_auth_errors_are_clean_and_leave_no_messages(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    q = "paid parental leave primary caregivers weeks"

    def timeout(*_, **__):
        raise httpx.ReadTimeout("slow")

    _anthropic(monkeypatch, timeout)
    r = ask(client, h, conv["id"], q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "LLM_TIMEOUT"

    _anthropic(monkeypatch, _status_error(429))
    r = ask(client, h, conv["id"], q)
    assert r.status_code == 429 and r.json()["error"]["code"] == "LLM_RATE_LIMITED"

    _anthropic(monkeypatch, _status_error(401))
    r = ask(client, h, conv["id"], q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "LLM_AUTH_ERROR"
    assert "test-key" not in r.text  # credentials are never echoed

    _anthropic(monkeypatch, _status_error(500))
    assert ask(client, h, conv["id"], q).json()["error"]["code"] == "LLM_PROVIDER_ERROR"

    assert _messages_of(client, h, conv["id"]) == [], "a failed answer must not leave a dangling question"


def test_missing_api_key_is_reported_not_faked(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "")
    r = ask(client, h, conv["id"], "paid parental leave primary caregivers weeks")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LLM_NOT_CONFIGURED"


def test_real_provider_response_is_parsed_and_cited(client, monkeypatch):
    h, doc, conv = setup_user_with_doc(client)

    def post(*_, **__):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.example.test"),
            json={"content": [{"type": "text", "text": "Sixteen weeks [S1]."}]},
        )

    _anthropic(monkeypatch, post)
    answer = ask(client, h, conv["id"], "paid parental leave primary caregivers weeks").json()["assistant_message"]
    assert answer["content"] == "Sixteen weeks [S1]."
    assert answer["citations"][0]["document_id"] == doc["id"]


def test_ollama_needs_no_api_key_and_uses_the_local_endpoint(client, monkeypatch):
    h, doc, conv = setup_user_with_doc(client)
    seen = {}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, model=json["model"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={"choices": [{"message": {"content": "Sixteen weeks [S1]."}}]})

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_model", "llama3.2:3b")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr("app.services.llm_service.httpx.post", post)

    answer = ask(client, h, conv["id"], "paid parental leave primary caregivers weeks").json()["assistant_message"]
    assert seen["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert seen["model"] == "llama3.2:3b"
    assert "Authorization" not in seen["headers"]
    assert answer["content"] == "Sixteen weeks [S1]." and answer["citations"][0]["document_id"] == doc["id"]


def test_ollama_without_a_model_or_server_gives_clear_errors(client, monkeypatch):
    h, _, conv = setup_user_with_doc(client)
    q = "paid parental leave primary caregivers weeks"
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", "")
    r = ask(client, h, conv["id"], q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "LLM_NOT_CONFIGURED"

    monkeypatch.setattr(settings, "llm_model", "llama3.2:3b")

    def refused(*_, **__):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("app.services.llm_service.httpx.post", refused)
    r = ask(client, h, conv["id"], q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "LLM_UNAVAILABLE"


# ------------------------------------------------ messy output from small local models
def _sources_for_validation():
    return [rag_service.Source(number=1, chunk_id=1, document_id=1, document_name="cv.pdf", page_number=1, text="Skills: Python, SQL.", vector_id="chunk-1")]


def test_runaway_repeated_markers_are_collapsed():
    raw = "She knows Python and SQL. [S1] " + "[S1] " * 300
    answer = rag_service.validate_and_format(raw, _sources_for_validation())
    assert answer.content == "She knows Python and SQL. [S1]"
    assert len(answer.citations) == 1 and answer.citations[0]["page_number"] == 1


def test_a_marker_cut_off_by_the_length_limit_is_removed():
    answer = rag_service.validate_and_format("She knows Python [S1] and also [S", _sources_for_validation())
    assert answer.content == "She knows Python [S1] and also"
    assert [c["document_name"] for c in answer.citations] == ["cv.pdf"]


def _cv_sources():
    text = (
        "Technical Skills Languages JavaScript Python SQL Frontend React.js Redux Toolkit Backend Laravel Node.js FastAPI Django "
        "Tools Git GitHub Docker Education SNJB College of Engineering Nashik Bachelor of Engineering in Computer Science"
    )
    return [rag_service.Source(number=1, chunk_id=1, document_id=7, document_name="Jidnyasa Girase_CV.pdf", page_number=1, text=text, vector_id="chunk-1")]


def test_citation_by_file_name_and_page_is_accepted_when_it_matches_a_retrieved_source():
    raw = "[Jidnyasa Girase_CV.pdf, page 1]\nShe knows JavaScript, Python and SQL."
    answer = rag_service.validate_and_format(raw, _cv_sources())
    assert answer.content.startswith("[S1]") and "JavaScript" in answer.content
    assert [(c["document_id"], c["page_number"]) for c in answer.citations] == [(7, 1)]


def test_citation_to_a_file_or_page_that_was_not_retrieved_is_dropped_and_not_trusted():
    raw = "Totally invented. [other.pdf, page 9] [Jidnyasa Girase_CV.pdf, page 4]"
    answer = rag_service.validate_and_format(raw, _cv_sources())
    assert answer.content == rag_service.INSUFFICIENT_MESSAGE and answer.citations == []


def test_uncited_answer_that_is_supported_by_the_sources_gets_verified_citations():
    raw = "She works with JavaScript, Python and SQL, using React.js, Laravel, FastAPI and Django, and tools like Docker and GitHub."
    answer = rag_service.validate_and_format(raw, _cv_sources())
    assert answer.content.endswith("[S1]")
    assert [(c["document_name"], c["page_number"]) for c in answer.citations] == [("Jidnyasa Girase_CV.pdf", 1)]


def test_uncited_answer_that_is_not_supported_by_the_sources_is_rejected():
    raw = "She won an international chess championship in Reykjavik and later founded a successful aerospace company."
    answer = rag_service.validate_and_format(raw, _cv_sources())
    assert answer.content == rag_service.INSUFFICIENT_MESSAGE and answer.citations == []


def test_malformed_markers_and_a_stray_insufficient_token_are_cleaned():
    answer = rag_service.validate_and_format("She knows Python and SQL. [SS1] INSUFFICIENT_Evidence", _cv_sources())
    assert answer.content == "She knows Python and SQL. [S1]"
    assert len(answer.citations) == 1


def test_summary_requests_start_from_the_beginning_of_the_document(client, monkeypatch):
    pages = ["Chapter one introduces the company and explains its mission for new readers", "Appendix with unrelated pricing tables and long lists of numbers"]
    h, doc, conv = setup_user_with_doc(client, pages)
    fake = use_llm(monkeypatch, "It introduces the company [S1].")

    # A similarity search for this wording finds nothing (the question names no topic), yet a summary is a valid request.
    r = ask(client, h, conv["id"], "Please summarize this document")
    assert r.status_code == 201
    assert len(fake.calls) == 1
    prompt = fake.calls[0][1][-1]["content"]
    assert prompt.index("Chapter one") < prompt.index("Appendix"), "sources must be in reading order"
    answer = r.json()["assistant_message"]
    assert answer["citations"][0]["document_id"] == doc["id"] and answer["citations"][0]["page_number"] == 1


def test_broad_questions_are_answered_from_the_start_of_the_document(client, monkeypatch):
    pages = ["Chapter one introduces the company and explains its mission for new readers", "Appendix with unrelated pricing tables and long lists of numbers"]
    h, doc, conv = setup_user_with_doc(client, pages)
    fake = use_llm(monkeypatch, "It introduces the company [S1].")
    for question in ["What are the key points?", "What is this document about?", "Summarize this document in a few sentences."]:
        r = ask(client, h, conv["id"], question)
        assert r.status_code == 201, question
        assert r.json()["assistant_message"]["citations"], question
    assert len(fake.calls) == 3, "every broad question must reach the model instead of failing the similarity floor"


def test_marker_only_reply_is_retried_once_and_then_answers(client, monkeypatch):
    """A small model once replied with just "[ S1 ]". That is now tolerated (spacing) and retried once for a real sentence."""
    h, doc, conv = setup_user_with_doc(client)
    replies = iter(["[ S1 ]", "Primary caregivers get sixteen weeks of paid leave [S1]."])
    fake = use_llm(monkeypatch, lambda messages: next(replies))
    r = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?")
    assert r.status_code == 201, r.text
    answer = r.json()["assistant_message"]
    assert "sixteen weeks" in answer["content"] and len(answer["citations"]) == 1
    assert len(fake.calls) == 2 and "only a source marker" in fake.calls[1][1][-1]["content"]


def test_marker_only_twice_is_still_insufficient_evidence_and_never_loops(client, monkeypatch):
    h, doc, conv = setup_user_with_doc(client)
    fake = use_llm(monkeypatch, "[ S1 ]")
    r = ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?")
    assert r.status_code == 201
    assert r.json()["assistant_message"]["citations"] == [] and "couldn't find enough evidence" in r.json()["assistant_message"]["content"]
    assert len(fake.calls) == 2  # one retry, never more


def test_explicit_refusal_is_not_retried(client, monkeypatch):
    h, doc, conv = setup_user_with_doc(client)
    fake = use_llm(monkeypatch, "INSUFFICIENT_EVIDENCE")
    ask(client, h, conv["id"], "How many weeks of paid parental leave do primary caregivers get?")
    assert len(fake.calls) == 1


def test_spaced_markers_are_normalised():
    from app.services.rag_service import Source, validate_and_format

    src = [Source(number=1, chunk_id=1, document_id=1, document_name="a.pdf", page_number=1, text="Staff get twenty days of paid leave.", vector_id="chunk-1")]
    out = validate_and_format("Staff get twenty days of paid leave [ S1 ].", src)
    assert out.citations and out.citations[0]["page_number"] == 1 and "[S1]" in out.content
