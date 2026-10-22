"""Reviewed explanations for recurring safety and contract concepts.

These are topic references, independent of lesson IDs and evaluation wording.
Individual tax computations and numerical loan requests still use the agent tools.
"""

import re

from application.learning.references import normalize, reviewed_payload


def reviewed_concept(query: str) -> str | None:
    text = normalize(query)
    supported_tax_period = all(year == "2026" for year in re.findall(r"\b20\d{2}\b", text))
    source_id = None
    answer = None
    if any(word in text for word in ("mau", "template")) and any(
        word in text for word in ("ghi chu", "phan tich doanh nghiep", "nghien cuu doanh nghiep")
    ):
        return (
            "Mẫu ghi chú học tập — chỉ điền khi có chứng cứ:\n\n"
            "| Phần | Nội dung cần điền |\n|---|---|\n"
            "| Câu hỏi nghiên cứu | [Câu hỏi có thể kiểm chứng, kỳ và phạm vi] |\n"
            "| Dữ kiện | Chưa có dữ liệu: [chỉ tiêu, giá trị, đơn vị, kỳ báo cáo] |\n"
            "| Nguồn của từng dữ kiện | Chưa có nguồn: [tài liệu, ngày công bố, trang/đoạn, URL] |\n"
            "| Giả định và diễn giải | [Ghi rõ giả định, liên hệ với dữ kiện nào, điều kiện có thể sai] |\n"
            "| Ba giới hạn | [Dữ liệu thiếu]; [giới hạn phương pháp]; [rủi ro chưa xét] |\n"
            "| Câu hỏi tiếp theo | [Tài liệu/công bố cần kiểm tra và thông tin cần tìm] |\n\n"
            "Chưa có tài liệu thì để trống; không bịa số, trang báo cáo, thời điểm hay phát ngôn "
            "cho doanh nghiệp thật. Nếu cần ví dụ, dùng Doanh nghiệp X và ghi rõ giả định tại "
            "từng số. URL có thật không chứng minh một con số; đoạn nguồn phải hỗ trợ kết luận. "
            "Phát biểu có thể kiểm chứng chưa phải dữ kiện đã được xác minh."
        )
    if "otp" in text and any(
        word in text for word in ("doc", "gui", "cung cap", "tong dai", "chia se")
    ):
        source_id = "digital_safety"
        answer = (
            "Không đọc/gửi OTP, PIN, mật khẩu hoặc CVV cho bất kỳ ai, kể cả nhân viên và khi "
            "chính bạn gọi tổng đài. Chỉ nhập OTP trong ứng dụng/trang chính thức cho giao dịch "
            "mình chủ động và đã kiểm tra số tiền, người nhận, mục đích.\n\n"
            "Tự lấy hotline từ app/thẻ/website chính thức; số gọi đến không chứng minh danh tính. "
            "Nếu đã lộ mã hoặc có giao dịch lạ, khóa trên kênh chính thức, báo ngân hàng ngay, "
            "giữ chứng cứ và trình báo cơ quan phù hợp. Không có bảo đảm thu hồi tiền hay hủy "
            "giao dịch đã hoàn tất trong vài giờ."
        )
    elif "toi thieu" in text and any(word in text for word in ("the", "tin dung")):
        source_id = "cic_debt_groups"
        answer = (
            "Trả đủ mức tối thiểu đúng hạn không tự động là quá hạn hay nợ xấu. Tuy nhiên, "
            "dư nợ còn lại có thể phát sinh lãi và kéo dài thời gian trả nợ. Việc còn được miễn "
            "lãi, tính lãi từ ngày nào và khoản phí nào áp dụng phải đọc đúng hợp đồng/sao kê.\n\n"
            "Để tính thời gian tất toán và tổng lãi, cần dư nợ, lịch giao dịch, cách tính lãi, "
            "tỷ lệ tối thiểu, sàn thanh toán bằng tiền và phí. Chỉ biết một tỷ lệ trên dư nợ thì "
            "không đủ để đưa số năm trả hết. Phân loại nợ dựa trên các tiêu chí áp dụng, không "
            "chỉ từ việc còn dư nợ. Hãy kiểm tra ngày đến hạn, toàn bộ dư nợ và điều kiện miễn "
            "lãi trên sao kê trước khi chọn số tiền trả."
        )
    elif "cic" in text and any(
        word in text for word in ("dong", "huy the", "anh huong", "tinh diem", "diem tin dung")
    ):
        source_id = "cic_debt_groups"
        answer = (
            "CIC không công bố một công thức điểm cá nhân đầy đủ để suy ra điểm từ một hành động "
            "riêng lẻ. Đóng hoặc hủy thẻ không có nghĩa chắc chắn điểm tăng hay giảm; tác động "
            "phụ thuộc hồ sơ tín dụng, dư nợ, lịch sử trả nợ và dữ liệu được tổ chức tín dụng "
            "báo cáo. Không áp quy tắc FICO hoặc một ngưỡng điểm nước ngoài vào CIC nếu chưa có "
            "nguồn xác nhận tương ứng. Hãy kiểm tra báo cáo tín dụng và hỏi ngân hàng/CIC khi "
            "cần xác minh một trường hợp cụ thể."
        )
    elif (
        supported_tax_period
        and "phu thuoc" in text
        and any(word in text for word in ("giam tru", "thue", "tinh vo", "khi nao"))
    ):
        source_id = "pit_dependents_2026"
        answer = (
            "Người phụ thuộc phải đáp ứng điều kiện của đúng nhóm quan hệ; không phải cứ "
            "không đi làm hoặc không có thu nhập là được tính. Phân biệt con chưa thành niên, "
            "con trưởng thành thuộc diện khuyết tật/mất năng lực, con đang học thuộc diện luật "
            "quy định, vợ/chồng, cha mẹ và người khác phải trực tiếp nuôi dưỡng. Điều kiện tuổi, "
            "khả năng lao động và thu nhập khác nhau theo nhóm. Vợ/chồng còn trong tuổi lao động, "
            "khỏe mạnh mà chỉ thất nghiệp không tự động đủ điều kiện.\n\n"
            "Với các nhóm phải xét thu nhập theo TT87/2026, mức bình quân tháng trong năm từ "
            "mọi nguồn không vượt 3 triệu đồng; ngưỡng này không thay thế các điều kiện khác. "
            "Cần đăng ký và hồ sơ phù hợp, không tính trùng cho hai người nộp thuế. Đừng áp "
            "chung điều kiện dưới 18 tuổi hoặc mất khả năng lao động cho mọi người phụ thuộc. "
            "Để xét trường hợp cụ thể, hãy cho biết kỳ tính thuế, quan hệ, tuổi, tình trạng "
            "học tập/khả năng lao động, thu nhập và ai đang đăng ký giảm trừ."
        )
    elif supported_tax_period and "quyet toan" in text and "thue" in text:
        source_id = "pit_dependents_2026"
        answer = (
            "Có hai nơi trả thu nhập không tự động có nghĩa phải tự quyết toán. Cần phân biệt "
            "được ủy quyền, phải tự quyết toán và không phải quyết toán; xét loại thu nhập, "
            "hợp đồng, nơi đang làm và thuế đã khấu trừ. NĐ253/2026 có ngoại lệ cho thu nhập "
            "nơi khác bình quân tháng trong năm không quá 15 triệu đã khấu trừ 10%, khi đủ "
            "điều kiện và không yêu cầu quyết toán phần đó. Không dùng ngưỡng tổng thu nhập "
            "100 triệu để tự kết luận, không cộng máy móc cổ tức/chuyển nhượng vào lương.\n\n"
            "Hãy cho biết năm quyết toán, tình trạng cư trú, các nơi trả lương, loại hợp đồng, "
            "thu nhập và số thuế đã khấu trừ. Cá nhân trực tiếp quyết toán thường có hạn cuối "
            "tháng thứ tư sau năm dương lịch, khác hạn tổ chức cuối tháng thứ ba; cần kiểm "
            "ngày nghỉ và trường hợp cụ thể trước khi chốt hạn."
        )
    elif (
        supported_tax_period
        and any(word in text for word in ("thue tncn", "thue thu nhap ca nhan", "tinh thue"))
        and not re.search(r"\d[\d.,\s]*\s*(?:trieu|nghin|tr\b|vnd|dong\b)", text)
    ):
        source_id = "pit_law_109"
        answer = (
            "Với tiền lương của cá nhân cư trú kỳ 2026: thu nhập tính thuế = max(0, tiền "
            "lương thuộc diện chịu thuế - bảo hiểm được trừ - giảm trừ gia cảnh - khoản giảm "
            "trừ hợp lệ khác). Trước đó cần loại khoản được miễn theo đúng điều kiện.\n\n"
            "Giảm trừ bản thân 15,5 triệu đồng/tháng, mỗi người phụ thuộc đủ điều kiện 6,2 "
            "triệu. Biểu lũy tiến tháng tính theo từng PHẦN thu nhập tính thuế: đến 10 triệu "
            "5%; trên 10-30 triệu 10%; trên 30-60 triệu 20%; trên 60-100 triệu 30%; trên 100 "
            "triệu 35%. Không áp một thuế suất cao nhất lên toàn bộ lương.\n\n"
            "Để tính số tiền, cần kỳ tính thuế, tình trạng cư trú, lương chịu thuế, số bảo "
            "hiểm thực được trừ, người phụ thuộc hợp lệ và giảm trừ khác; dùng công cụ PIT "
            "sau khi đủ đầu vào. Không tự lấy lương mẫu của bài học hoặc coi mọi phí bảo "
            "hiểm nhân thọ là khoản được giảm trừ. Mô hình này không thay thế quyết toán hay "
            "xử lý thu nhập ngoài lương; kỳ khác phải kiểm lại văn bản."
        )
    elif "bhyt" in text and any(word in text for word in ("khac", "thuong mai", "suc khoe")):
        source_id = "kdbh_law_08"
        answer = (
            "BHYT và bảo hiểm sức khỏe thương mại khác nhau về cơ sở tham gia, phạm vi và cách "
            "chi trả. BHYT chi theo quy định, danh mục và điều kiện áp dụng; có thể khám tại "
            "cơ sở tư nhân có hợp đồng BHYT, không chỉ bệnh viện công.\n\n"
            "Bảo hiểm thương mại chi theo hợp đồng: kiểm hạn mức, đồng chi trả, cơ sở liên kết, "
            "thời gian chờ, bệnh có sẵn và loại trừ. Có gói ngoại trú hoặc nha khoa không đồng "
            "nghĩa mọi điều trị răng, implant, chỉnh nha hay thẩm mỹ đều được chi. Đừng suy quyền "
            "lợi từ tên gói hoặc lời giới thiệu.\n\n"
            "Bước thực hành: lấy một dịch vụ cụ thể, đối chiếu điều kiện BHYT và điều khoản "
            "hợp đồng thương mại; đánh dấu phần được chi, tự trả và chưa xác nhận. Hai hình "
            "thức có thể bổ sung cho nhau nhưng không mặc nhiên hoàn toàn bộ mọi chi phí."
        )
    elif "bao hiem" in text and any(
        word in text for word in ("loai tru", "benh co san", "can nhac")
    ):
        source_id = "kdbh_law_08"
        answer = (
            "Điều khoản loại trừ xác định rủi ro/trường hợp không được chi trả theo hợp đồng. "
            "Thời gian chờ là khoảng thời gian trước khi một quyền lợi có thể bắt đầu được "
            "xét; hết chờ không tự xóa một loại trừ riêng. Bệnh có sẵn không mặc nhiên được "
            "chi sau hai năm. Cần khai báo trung thực và yêu cầu giải thích điều khoản bằng văn bản.\n\n"
            "Trước khi ký, kiểm quyền lợi, hạn mức, đồng chi trả, bệnh có sẵn, loại trừ, chờ "
            "và thủ tục yêu cầu chi trả. Với hợp đồng thời hạn trên một năm, Điều35 Luật KDBH "
            "quy định 21 ngày cân nhắc từ ngày nhận hợp đồng; khi từ chối tiếp tục, hoàn phí "
            "sau trừ chi phí hợp lý theo thỏa thuận. Không áp thời hạn này cho mọi hợp đồng. "
            "Một ca cụ thể cần đọc đúng bản hợp đồng và hồ sơ, chưa thể hứa được bồi thường."
        )
    elif "bao hiem" in text and any(
        word in text
        for word in ("can thiet", "that su can", "ban kem", "mua kem", "co can", "can mua")
    ):
        source_id = "kdbh_law_08"
        answer = (
            "Bắt đầu từ rủi ro gây tổn thất vượt khả năng tự chịu, rồi xét quyền lợi hợp đồng "
            "và khả năng duy trì phí. Nhu cầu bảo hiểm sức khỏe của bản thân khác nhu cầu bảo "
            "vệ người phụ thuộc bằng bảo hiểm nhân thọ; độc thân vẫn có thể cần bảo hiểm y tế/sức khỏe.\n\n"
            "Không dùng quy tắc phải có người phụ thuộc mới cần mua, hay phải đồng thời trả "
            "lời có cho ba câu hỏi. Nếu quỹ đã đủ tự chịu một rủi ro, đó là yếu tố cân nhắc "
            "tự bảo hiểm, không phải lý do tự động phải mua thêm. Không thể chốt số tiền bảo "
            "hiểm hoặc mức phí chỉ từ số con hay dư nợ.\n\n"
            "So sánh rủi ro chưa được BHYT/hợp đồng hiện có bảo vệ, giới hạn chi trả, loại trừ, "
            "thời gian chờ, tổng phí và điều kiện hủy. Bán kèm không tự chứng minh lừa đảo hay "
            "nhu cầu; cần kiểm sự tự nguyện và điều kiện sản phẩm. Hợp đồng trên một năm có "
            "21 ngày cân nhắc từ ngày nhận theo Điều35 Luật KDBH, hoàn phí sau trừ chi phí hợp "
            "lý theo thỏa thuận."
        )
    if answer is None:
        return None
    reference = reviewed_payload(source_id)
    return (
        answer
        + "\n\nNguồn đối chiếu (tóm tắt biên tập 22/10/2026): "
        + " · ".join(f"[Nguồn {i}]({url})" for i, url in enumerate(reference["source_urls"], 1))
    )
