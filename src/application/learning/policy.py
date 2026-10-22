"""Validated, immutable per-request learning scope (never mutate the shared agent)."""

import json
import re
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

CORE_TOOLS = frozenset(
    {
        "budget_template",
        "calculate_future_value",
        "calculate_loan_schedule",
        "calculate_pit",
        "get_rates",
        "search_knowledge",
        "generate_learning_chart",
    }
)
MARKET_TOOLS = frozenset(
    {
        "get_stock_price",
        "generate_chart_spec",
        "get_company_info",
        "get_financial_ratios",
        "search_knowledge",
    }
)


def has_requested_symbols(
    tool_name: str, args: dict, query: str, chart_summary: str | None
) -> bool:
    """Lesson examples must not silently supply a missing ticker."""
    if tool_name not in MARKET_TOOLS - {"search_knowledge"}:
        return True
    symbols = args.get("symbols") if tool_name == "generate_chart_spec" else args.get("tickers")
    if not isinstance(symbols, list) or not symbols:
        return False
    context = query + " " + (chart_summary or "")
    return all(
        isinstance(symbol, str)
        and re.search(rf"(?<!\w){re.escape(symbol)}(?!\w)", context, re.IGNORECASE)
        for symbol in symbols
    )


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(
        files("application.learning").joinpath("catalog.json").read_text(encoding="utf-8")
    )


class LearningContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    track: Literal["personal_finance", "market_literacy"] = "personal_finance"
    lesson_id: str | None = None

    @model_validator(mode="after")
    def validate_lesson(self):
        if self.lesson_id and self.lesson is None:
            raise ValueError("Bài học không thuộc lộ trình đã chọn.")
        return self

    @property
    def lesson(self) -> dict | None:
        return next(
            (
                lesson
                for track in catalog()["tracks"]
                if track["id"] == self.track
                for module in track["modules"]
                for lesson in module["lessons"]
                if lesson["id"] == self.lesson_id
            ),
            None,
        )

    @property
    def tools(self) -> frozenset[str]:
        allowed = CORE_TOOLS if self.track == "personal_finance" else MARKET_TOOLS
        if self.lesson and "tools" in self.lesson:
            return allowed.intersection(self.lesson["tools"])
        return allowed

    def memory_user(self, user_id: str | None) -> str | None:
        return f"{user_id}:learning:{self.track}:{self.lesson_id or 'general'}" if user_id else None

    def prompt(self, query: str = "") -> str:
        text = (
            "Bạn là trợ giảng giáo dục tài chính. Dạy khái niệm, ví dụ, cách kiểm chứng và "
            "câu hỏi tự đánh giá; không đưa lệnh mua/bán, phân bổ cá nhân hay cam kết lợi nhuận. "
            "Cho phép học kiến thức đầu tư; không từ chối một câu hỏi khái niệm chỉ vì có cổ phiếu. "
            "Ví dụ giả định phải ghi rõ, dữ liệu thật phải có nguồn/ngày/đơn vị; thiếu thì nói chưa rõ. "
            "Không tự gắn VND hay nghìn VND cho giá khi tool chưa xác nhận đơn vị; "
            "giữ nguyên giá trị và nói rõ đơn vị chưa xác minh. "
            "Không suy ra dự báo từ giá quá khứ. Khi tool thiếu dữ liệu, giải thích và đề nghị thử lại, "
            "không tự tạo dữ liệu. "
            "Bài học là bối cảnh, không phải yêu cầu đang thực hiện. Không tự chạy câu hỏi ví dụ "
            "hay lấy mã/số liệu trong ví dụ thay cho đầu vào người học chưa cung cấp. "
            "Câu hỏi thuần khái niệm không cần tra cứu một doanh nghiệp cụ thể. Trả lời mặc định "
            "ngắn gọn: ý chính, một ví dụ/bước thực hành, giới hạn và một câu tự kiểm tra. "
            "Kiểm tra số và lời giải khớp nhau trước khi trả lời: các tỷ lệ ngân sách cộng đủ 100%; "
            "nếu nói giảm tiết kiệm từ 20% thì tỷ lệ tiết kiệm mới phải nhỏ hơn 20%. "
            "50/30/20 là tham khảo; không áp tỷ lệ tiết kiệm tối thiểu bắt buộc cho mọi hoàn cảnh. "
            "Nếu yêu cầu vượt nhóm công cụ hiện tại, giải thích khái niệm và hướng dẫn chọn "
            "lộ trình/bài thích hợp trên giao diện; không tự đổi lộ trình. "
            f"Lộ trình đang chọn: {self.track}. Công cụ cho phép: {', '.join(sorted(self.tools))}. "
        )
        if self.track == "personal_finance":
            text += "Tra cứu/vẽ cổ phiếu nằm ở lộ trình tự chọn Hiểu thị trường tài chính (/learn?track=market_literacy). "
        if self.lesson:
            text += "\nBài học hiện tại (nội dung biên soạn): " + json.dumps(
                self.lesson, ensure_ascii=False
            )
        from application.learning.guidance import content_guidance

        text += "\n" + content_guidance(query, self.lesson_id)
        return text
