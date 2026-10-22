import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from application.agents.agent import AgentStreamEvent, StockAgent
from application.learning.review import review_messages


def test_review_receives_actual_evidence_and_query_without_catalog_example_inputs():
    evidence = ToolMessage(content='{"tax": 0}', tool_call_id="tax", name="calculate_pit")
    messages = review_messages("Lương thấp có phải nộp thuế?", "M6L1", "thuế âm", [evidence])
    payload = json.loads(messages[-1].content)
    assert payload["tool_evidence"] == [{"tool": "calculate_pit", "result": '{"tax": 0}'}]
    assert payload["question"] == "Lương thấp có phải nộp thuế?"
    assert payload["draft"] == "thuế âm"


def agent_with_review(result=None, error=None):
    agent = object.__new__(StockAgent)
    invoke = MagicMock(return_value=result, side_effect=error)
    agent.llm_provider = SimpleNamespace(
        get_tool_calling_llm=MagicMock(return_value=SimpleNamespace(invoke=invoke))
    )
    agent._output_guardrails = None
    return agent, invoke


def test_final_review_replaces_unsafe_draft_before_response():
    agent, invoke = agent_with_review(AIMessage(content="Không cung cấp OTP cho người khác."))
    result = agent._final_answer_node(
        {
            "messages": [AIMessage(content="Có thể đọc OTP khi gọi tổng đài")],
            "original_query": "Tự gọi tổng đài được đọc OTP không?",
            "learning_context": {"track": "personal_finance", "lesson_id": "M4L4"},
        }
    )
    assert result["messages"][0].content == "Không cung cấp OTP cho người khác."
    invoke.assert_called_once()
    assert invoke.call_args.kwargs["timeout"] == 45
    agent.llm_provider.get_tool_calling_llm.assert_called_once_with([])


@pytest.mark.parametrize(
    "result,error",
    [
        (AIMessage(content=""), None),
        (None, TimeoutError("offline")),
    ],
)
def test_failed_review_does_not_fall_back_to_unchecked_financial_claim(result, error):
    agent, _ = agent_with_review(result, error)
    answer = agent._final_answer_node(
        {
            "messages": [AIMessage(content="Có thể đọc OTP")],
            "learning_context": {"track": "personal_finance"},
        }
    )["messages"][0]
    assert answer.additional_kwargs["agent_error"]
    assert "Có thể đọc OTP" not in answer.content


def test_learning_stream_never_emits_draft_or_review_tokens():
    agent = object.__new__(StockAgent)
    agent.app = SimpleNamespace(
        stream=lambda *args, **kwargs: iter(
            [
                (AIMessageChunk(content="unsafe draft"), {"langgraph_node": "reason"}),
                (AIMessageChunk(content="intermediate edit"), {"langgraph_node": "final_answer"}),
                (AIMessage(content="unmarked model output"), {"langgraph_node": "final_answer"}),
                (
                    AIMessage(
                        content="checked answer", additional_kwargs={"content_reviewed": True}
                    ),
                    {"langgraph_node": "final_answer"},
                ),
            ]
        )
    )
    events = list(
        agent._run_single_stream(
            "question",
            "review-test",
            learning_context={"track": "personal_finance"},
        )
    )
    assert events == ["checked answer"]
    assert not any(isinstance(event, AgentStreamEvent) for event in events)


def test_product_disclaimer_does_not_invent_a_legal_basis():
    from infrastructure.rag.safety import check_and_sanitize

    answer, _ = check_and_sanitize("Giải thích khái niệm. " * 20)
    assert "TT 135" not in answer
    assert "giáo dục" in answer


def test_generated_loan_example_without_successful_tool_result_is_removed():
    from application.learning.review import unsupported_loan_result

    draft = "Giả định vay 8 triệu, tổng phí vay khoảng 315 nghìn, trả/tháng 1,38 triệu."
    assert unsupported_loan_result(draft, [])
    failed = ToolMessage(
        content='{"error":"offline"}', name="calculate_loan_schedule", tool_call_id="x"
    )
    assert unsupported_loan_result(draft, [failed])
    success = ToolMessage(
        content='{"monthly_payment":1380387}', name="calculate_loan_schedule", tool_call_id="x"
    )
    assert not unsupported_loan_result(draft, [success])
    assert not unsupported_loan_result(
        "Nhận 8 triệu, trả 10,5 triệu sau một tháng: phí kỳ 31,25%.", []
    )


def test_final_loan_answer_asks_missing_inputs_instead_of_inventing_repayment():
    agent, _ = agent_with_review(
        AIMessage(content="Vay 8 triệu; trả/tháng 1,38 triệu; tổng phí vay 315 nghìn.")
    )
    answer = agent._final_answer_node(
        {
            "messages": [AIMessage(content="draft")],
            "original_query": "Dùng quỹ để sửa laptop?",
            "learning_context": {"track": "personal_finance", "lesson_id": "M3L6"},
        }
    )["messages"][0]
    assert "315" not in answer.content and "1,38" not in answer.content
    assert "báo giá sửa laptop" in answer.content
    assert answer.additional_kwargs["content_reviewed"]


def test_reviewed_concepts_work_without_lesson_id_or_provider_and_do_not_capture_calculations():
    from application.learning.concepts import reviewed_concept

    insurance = reviewed_concept("Độc thân thì có cần mua bảo hiểm không?")
    assert "độc thân vẫn có thể cần" in insurance
    assert "không phải lý do tự động phải mua" in insurance
    assert reviewed_concept("Vay 120 triệu 12%/năm 24 tháng trả bao nhiêu?") is None
    assert reviewed_concept("Tính thuế lương 30 triệu năm 2026") is None
    assert reviewed_concept("Cách tính thuế TNCN năm 2025?") is None
    assert reviewed_concept("Cách tính thuế TNCN năm 2026?")
    assert "Không áp quy tắc FICO" in reviewed_concept(
        "Đóng thẻ lâu không dùng có ảnh hưởng điểm tín dụng CIC không?"
    )
    assert reviewed_concept(
        "Tôi khỏe mạnh và thất nghiệp, có phải người phụ thuộc để giảm trừ thuế?"
    )
    agent = object.__new__(StockAgent)
    agent.llm_provider = None
    result = agent._reason_node(
        {
            "learning_context": {"track": "personal_finance"},
            "original_query": "Chủ động gọi tổng đài có được đọc OTP không?",
        }
    )
    assert result["messages"][0].additional_kwargs["editorial_reference"]
    assert result["next_tool_call"] is None
