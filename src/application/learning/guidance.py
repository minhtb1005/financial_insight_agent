"""Teaching rules and topic guidance, shared across authored and unseen questions."""

from application.learning.references import references_for

CONTENT_RULES = """
Quy tắc chất lượng nội dung:
- Trả lời đúng câu hỏi đang hỏi. Chỉ dùng sự kiện pháp lý/lãi suất/phí từ nguồn có nội dung
  hỗ trợ và đúng kỳ; không nhớ số cũ rồi gắn tên văn bản mới. Các tóm tắt biên tập bên dưới
  có ngày đối chiếu, không phải trích nguyên văn. Nếu nguồn RAG cũ mâu thuẫn, chỉ rõ giới hạn,
  ưu tiên văn bản đúng kỳ; chưa kiểm được thì không khẳng định. Không bịa điều/khoản hay URL.
- Tuyệt đối không đọc/gửi OTP, PIN, mật khẩu cho người khác, kể cả tự gọi tổng đài.
  Chỉ nhập trong kênh chính thức để xác nhận giao dịch mình chủ động và đã kiểm tra.
- Mẫu phân tích chưa có dữ kiện: để ô trống 'chưa có dữ liệu', hoặc dùng Doanh nghiệp X
  với số ghi rõ giả định. Không bịa số VNM/FPT, trang báo cáo, ngày, phát ngôn CEO hay nguồn.
  Một URL có thật không chứng minh số liệu. Chỉ trích đoạn thực sự hỗ trợ kết luận.
- Số học: viết giả định và công thức trước; ví dụ và câu tự kiểm tra phải đủ đầu vào.
  Vay/trả nợ và tính ngược số tiền vay: bắt buộc calculate_loan_schedule, kể cả lãi 0%.
  Thuế có đủ dữ kiện: calculate_pit; thiếu lương/cư trú/kỳ/giảm trừ thì hỏi, không mặc định lương.
  Lãi kép/lạm phát/hưu trí: calculate_future_value. Không tự ước lượng khi công cụ có thể tính.
  Tổng phân bổ không vượt tiền thực có; quỹ cuối=quỹ đầu+tiền nạp-tiền dùng. Chỉ nạp lại quỹ
  từ thặng dư SAU chi thiết yếu/nợ tối thiểu, không từ toàn bộ lương. Thu nhập vượt nền thì
  gửi phần dư, chỉ rút bù khi thu nhập thấp hơn nền. Tiền có thể chịu rủi ro=max(0,tiền thanh
  khoản-mục tiêu quỹ-nghĩa vụ đã cam kết), không chi vào phần quỹ cần giữ.
- Không tự đưa tỷ lệ bắt buộc, lãi/phí hiện hành, trần bảo hiểm, mức khấu hao hoặc mức sinh
  lời không có nguồn. Nếu chỉ cần minh họa, ghi giả định; không biến giả định thành thông lệ.
- Tự kiểm tra phải có dữ kiện đủ để giải và không tự thêm kiến thức sai. Mỗi câu trả lời
  nhất quán từ ví dụ tới giới hạn; không thêm số/luật ngoài nhu cầu chỉ để làm dài bài.
"""

_TOPICS = {
    "M1L7": "Chia điện: dùng kWh cuối kỳ trừ đầu kỳ, không dùng chỉ số tích lũy. "
    "Tách kWh chung và riêng; đơn giá phân bổ bình quân=hóa đơn/tổng kWh. Tiền mỗi phòng="
    "kWh riêng*đơn giá + phần tiền chung theo thỏa thuận. Kiểm tổng các phần=hóa đơn, "
    "không cộng phần chung hai lần. Ví dụ phải cho đủ kWh chung/riêng và số người. "
    "Không làm tròn kWh trung gian; làm tròn tiền cuối và phân bổ phần dư để tổng đúng hóa đơn.",
    "M2L3": "Pay yourself first là dành trước một khoản phù hợp sau khi bảo đảm chi thiết yếu "
    "và trả nợ tối thiểu đúng hạn; không đầu tư trước nghĩa vụ bắt buộc/nợ lãi cao.",
    "M3L2": "Snowball/avalanche đều trả tối thiểu mọi khoản trước khi dồn phần dư; ví dụ so sánh "
    "cần khoản nhỏ lãi thấp và khoản lớn lãi cao để thấy thứ tự khác. Không bịa chênh lệch lãi.",
    "M3L3": "Phân biệt flat, gốc đều và trả tổng đều (annuity). Nói rõ cách trả trước khi so tổng "
    "lãi, cùng số tiền/kỳ/rate. APR không mặc nhiên giống lãi hiệu dụng; không nói luôn gấp đôi.",
    "M3L4": "Không bịa thời gian tất toán/tổng lãi khi chỉ trả % dư nợ: cần sàn trả bằng tiền, "
    "cách tính lãi và ngày giao dịch. Chỉ trả tỷ lệ không có sàn không cho ngày hết nợ hữu hạn. "
    "Không đưa khoảng 5-7 năm hay lãi gấp đôi khi chưa có lịch tính. Chỉ giải thích cơ chế, "
    "hỏi sao kê/điều khoản để mô phỏng, không tự tạo ví dụ thời gian trả hết.",
    "M3L6": "Sửa laptop làm việc khác nâng cấp giải trí. Tính số tháng quỹ còn lại và kế hoạch "
    "bù từ thặng dư. Hỏi GIÁ SỬA, số dư quỹ, chi thiết yếu, thặng dư và điều kiện vay. "
    "12 triệu/6 tháng trong activity là bài tập riêng, KHÔNG phải dữ kiện người hỏi. "
    "Dùng biến giá sửa khi thiếu báo giá. Không kết luận vay luôn an toàn hơn chỉ vì thu nhập "
    "ổn định hoặc cấm dùng quỹ đúng mục đích khẩn cấp chỉ vì quỹ sẽ giảm.",
    "M3L7": "So sánh cùng kỳ: thực nhận=gốc-phí trừ trước; chi phí=tổng trả-thực nhận; "
    "tỷ lệ chi phí kỳ=chi phí/thực nhận. Ví dụ ghi rõ giả định và tránh quy đổi tháng/năm "
    "nếu chưa có quy ước ngày và dòng tiền. Không vừa nói nhận đủ gốc vừa trừ phí trước. "
    "Trần dân sự thuộc BLDS, tội cho vay lãi nặng thuộc BLHS; không nhầm hai bộ luật.",
    "M4L5": "Không biết công thức điểm CIC thì không giải thích tác động bằng tuổi tài khoản "
    "hay utilization như dữ kiện Việt Nam. Không đưa số lượt miễn phí tra cứu khi chưa có "
    "nguồn biểu phí hiện hành. Tập trung nghĩa vụ phí, tất toán, xác nhận đóng và cập nhật.",
    "M8L2": "Hưu trí: tính chi phí hiện tại điều chỉnh riêng đi làm/con cái/y tế rồi lũy kế lạm "
    "phát. Nếu giả định dùng70-80% phải nhân tỷ lệ đó cả trong ví dụ. Không áp70-80% mặc định. "
    "Không lấy tuổi thọ lúc sinh trừ tuổi hưu; dùng các kịch bản sống thêm/tuổi đích được ghi "
    "rõ là giả định. Tỷ trọng y tế tương lai cần tỷ trọng ban đầu và tốc độ cả hai nhóm.",
    "M8L4": "Giá niêm yết đồ cũ chỉ tham khảo, không phải tiền bán thực nhận; xét tình trạng, "
    "thương lượng/phí. Ghi tài sản và dư nợ riêng, không tự áp khấu hao30-60%.",
    "M8L7": "TCO=giá mua+chi dùng-giá bán lại. Chi phí cơ hội phải theo thời điểm dòng tiền "
    "(giá mua đầu kỳ, chi rải kỳ, bán cuối kỳ), không lấy toàn bộ TCO như tiền đầu tư từ ngày0.",
    "M8L8": "DTI tính TẤT CẢ nghĩa vụ trả nợ tháng/thu nhập ròng, không riêng khoản nhà; ngưỡng "
    "là giả định để thử ngân sách, không quy định NHNN chung. Dùng chế độ payment_budget "
    "của calculate_loan_schedule để tính ngược gốc; stress lãi, quỹ sau trả trước, phí bảo trì.",
    "MK3L2": "Drawdown tối đa khác lỗ cuối kỳ; đa dạng hóa không bỏ rủi ro hệ thống. Không dẫn "
    "luật bảo hiểm như nguồn công thức danh mục nếu đoạn nguồn không hỗ trợ.",
    "MK4L1": "Ba báo cáo chính: bảng cân đối kế toán, kết quả kinh doanh, lưu chuyển tiền tệ; "
    "đọc kèm thuyết minh. Xuất hóa đơn đơn lẻ chưa đủ điều kiện ghi doanh thu.",
    "MK4L2": "Phân biệt ngày snapshot với kỳ báo cáo; chưa xác nhận ROE quý/năm, % hay tỷ lệ "
    "thì nói chưa xác nhận, không tự quy đổi. Không tự xếp ngành nào ROE cao hơn ngành khác.",
    "MK2L1": "Mô tả đường close chỉ dùng min/max của close, không lấy high/low của nến. "
    "Phân biệt phiên mới nhất đang giao dịch với phiên đã chốt; không gọi giá tạm là đóng cửa cuối ngày.",
    "MK2L2": "So sánh cùng field/định nghĩa và trạng thái điều chỉnh; khung thời gian khác làm "
    "đổi cảm giác, không đổi dữ kiện hoặc chứng minh nguyên nhân/dự báo.",
}


def content_guidance(query: str = "", lesson_id: str | None = None) -> str:
    parts = [CONTENT_RULES]
    if lesson_id in _TOPICS:
        parts.append(_TOPICS[lesson_id])
    parts.extend(ref.context() for ref in references_for(query, lesson_id))
    return "\n\n".join(parts)
