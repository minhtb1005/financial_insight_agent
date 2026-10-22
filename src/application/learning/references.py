"""Reviewed editorial references, not quotations or a substitute for legal advice.

Shared by lesson context and retrieval so an old embedded seed cannot override
the reviewed facts. Dates and URLs are explicit; never manufacture an article.
"""

from dataclasses import dataclass
import unicodedata


REVIEWED_AT = "2026-10-22"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


@dataclass(frozen=True)
class Reference:
    id: str
    title: str
    text: str
    urls: tuple[str, ...]
    terms: tuple[str, ...]
    lessons: tuple[str, ...] = ()

    def payload(self) -> dict:
        return {
            "source_id": self.id,
            "title": self.title,
            "text": self.text,
            "source_url": self.urls[0],
            "source_urls": list(self.urls),
            "priority": 1,
            "reviewed_at": REVIEWED_AT,
            "kind": "editorial_summary",
        }

    def context(self) -> str:
        return (
            f"Tóm tắt biên tập đã đối chiếu {REVIEWED_AT}: {self.title}\n{self.text}\n"
            + "\n".join(f"Nguồn đối chiếu: {url}" for url in self.urls)
        )


REFERENCES = (
    Reference(
        "pit_law_109",
        "Thuế lương cá nhân cư trú — kỳ tính thuế 2026",
        "Kỳ lương 2026: giảm trừ bản thân 15.500.000đ/tháng; mỗi người phụ thuộc đủ điều kiện "
        "6.200.000đ/tháng. Biểu lũy tiến gồm 5 bậc trên THU NHẬP TÍNH THUẾ tháng: "
        "đến 10 triệu:5%; phần trên 10-30 triệu:10%; trên 30-60:20%; trên 60-100:30%; "
        "trên 100 triệu:35%. Không dùng mức 11/4,4 triệu hay biểu 7 bậc cho kỳ này. "
        "Thu nhập chịu thuế là phần lương/tiền công thuộc diện chịu thuế sau loại khoản miễn; "
        "thu nhập tính thuế=max(0,thu nhập chịu thuế-bảo hiểm được trừ-giảm trừ gia cảnh-"
        "các khoản giảm trừ hợp lệ khác). Không bỏ bảo hiểm khi minh họa. Hỏi kỳ tính thuế, "
        "Không coi mọi phí bảo hiểm nhân thọ tự nguyện là khoản giảm trừ thuế; phải xét loại "
        "khoản đóng và điều kiện pháp luật, không nhầm với hưu trí tự nguyện. "
        "tình trạng cư trú, lương chịu thuế, người phụ thuộc đủ điều kiện và số bảo hiểm; "
        "thiếu đầu vào thì hỏi, không tự coi mẫu lương là lương người hỏi. "
        "Luật 109/2025 có hiệu lực 01/07/2026 nhưng quy định tiền lương cá nhân cư trú áp dụng "
        "từ kỳ tính thuế 2026. Công cụ PIT là mô hình lương đơn giản, không giải quyết mọi "
        "trường hợp miễn/giảm thuế, thu nhập khác hay quyết toán.",
        (
            "https://vanban.chinhphu.vn/?docid=216495&pageid=27160",
            "https://chinhsachonline.chinhphu.vn/thoi-diem-ap-dung-bieu-thue-thu-nhap-ca-nhan-moi-84963.htm",
        ),
        ("thue", "tncn", "luong", "giam tru"),
        ("M6L1", "M6L2", "M6L3", "M6L4"),
    ),
    Reference(
        "pit_dependents_2026",
        "Điều kiện người phụ thuộc và quyết toán 2026",
        "Người không đi làm KHÔNG tự động là người phụ thuộc. Phải xét nhóm quan hệ, "
        "tuổi/khả năng lao động, thu nhập, trách nhiệm nuôi dưỡng, hồ sơ đăng ký; một người "
        "không tính trùng cho hai người nộp thuế. Theo TT87/2026, ngưỡng thu nhập bình quân "
        "tháng từ mọi nguồn là không quá 3 triệu cho các nhóm thuộc phạm vi điều kiện đó; "
        "không áp riêng ngưỡng này thay toàn bộ điều kiện. Đặc biệt vợ/chồng còn trong tuổi "
        "lao động mà chỉ thất nghiệp chưa đủ điều kiện mất khả năng lao động. "
        "Phân biệt từng nhóm: con chưa thành niên; con trưởng thành thuộc diện khuyết tật/"
        "mất năng lực; con đang học thuộc diện luật quy định kèm điều kiện thu nhập; vợ/chồng, "
        "cha mẹ, người khác phải nuôi dưỡng xét tuổi lao động, khả năng lao động và thu nhập "
        "theo từng nhóm. Không bắt mọi người phụ thuộc đồng thời phải dưới 18 tuổi hoặc mất "
        "khả năng lao động: bỏ sót con đang học và người ngoài tuổi lao động. "
        "Quyết toán lương: phân biệt tự quyết toán, được ủy quyền và không phải quyết toán. "
        "Điều 51 NĐ253/2026 có ngoại lệ, gồm phần thu nhập nơi khác bình quân tháng trong năm "
        "không quá 15 triệu đã khấu trừ 10% đúng điều kiện; không kết luận mọi người có hai nơi "
        "thu nhập phải tự quyết toán. Không có ngưỡng tổng thu nhập 100 triệu để tự kết luận. "
        "Không cộng máy móc cổ tức/chuyển nhượng vào quyết toán lương. Hạn cá nhân trực tiếp "
        "quyết toán theo quản lý thuế thường cuối tháng thứ 4 sau năm dương lịch (xét ngày nghỉ), "
        "khác hạn tổ chức cuối tháng thứ 3. Kiểm tra kỳ và trường hợp trước khi chốt hạn. "
        "TT87/2026 hiệu lực 01/07/2026; không nói chưa có văn bản hướng dẫn.",
        (
            "https://baochinhphu.vn/quy-dinh-moi-ve-thue-thu-nhap-ca-nhan-102260707165524772.htm",
            "https://xaydungchinhsach.chinhphu.vn/quy-dinh-quyet-toan-thue-thu-nhap-ca-nhan-119260703162819669.htm",
        ),
        ("phu thuoc", "quyet toan", "giam tru"),
        ("M6L2", "M6L3"),
    ),
    Reference(
        "kdbh_law_08",
        "Bảo hiểm: nhu cầu, hợp đồng và thời gian cân nhắc",
        "Điều 35 Luật KDBH08/2022: hợp đồng thời hạn TRÊN 1 năm có 21 ngày cân nhắc từ ngày "
        "nhận hợp đồng; có thể hoàn phí sau trừ chi phí hợp lý theo thỏa thuận. Không nói 15 ngày "
        "hay 15-30 ngày cho mọi hợp đồng. Loại trừ khác thời gian chờ; bệnh có sẵn không tự hết "
        "loại trừ sau 2 năm. Quyền lợi/loại trừ phụ thuộc sản phẩm và điều kiện hợp pháp; không "
        "tự khẳng định mọi tai nạn giao thông đều được bảo hiểm. Người không có người phụ thuộc "
        "vẫn có thể cần bảo hiểm sức khỏe; nhu cầu nhân thọ khác chi phí y tế bản thân. "
        "BHYT xã hội khác bảo hiểm thương mại theo hợp đồng; cơ sở tư nhân có hợp đồng BHYT "
        "vẫn có thể khám BHYT. Không khẳng định BHYT chỉ chi ở viện công hay không chi ngoại trú. "
        "Bảo hiểm thương mại cũng không mặc nhiên chi mọi dịch vụ cao cấp/thẩm mỹ. "
        "Bán chéo không đồng nghĩa lừa đảo; kiểm tra sự tự nguyện, quyền lợi, phí và loại trừ. "
        "Không áp ngân sách phí bảo hiểm theo một tỷ lệ bắt buộc.",
        (
            "https://xaydungchinhsach.chinhphu.vn/toan-van-luat-kinh-doanh-bao-hiem-119240130070753445.htm",
            "https://mof.gov.vn/quan-ly-giam-sat-bao-hiem/pho-bien-kien-thuc-ve-bao-hiem/mofucm282399",
        ),
        ("bao hiem", "loai tru", "can nhac", "benh co san"),
        ("M5L1", "M5L2", "M5L3"),
    ),
    Reference(
        "bhxh_2026_rates",
        "Phân biệt phần bảo hiểm người lao động và doanh nghiệp",
        "Ví dụ người lao động thuộc đủ ba chế độ, mức thông thường: NLĐ đóng BHXH8%, BHYT1,5%, "
        "BHTN1%; phần BHYT3% là của người sử dụng lao động, không trừ thêm vào lương NLĐ. "
        "10,5% chỉ trên cơ sở đóng tương ứng, không mặc định mọi khoản gross đều thuộc cơ sở đó. "
        "BHXH/BHYT và BHTN có trần/cơ sở pháp lý khác nhau; không gọi chung là lương cơ sở vùng. "
        "Nếu không cần tính trần cho câu hỏi thì không tự thêm số trần, mức lương cơ sở hay mức "
        "phí chưa được kiểm tra. Khi ước tính gross/net phải nêu tình trạng cư trú, cơ sở đóng, "
        "phụ thuộc và giả định; không khấu trừ phần đóng của doanh nghiệp vào lương cá nhân.",
        (
            "https://baohiemxahoi.gov.vn/tintuc/Pages/cai-cach-chinh-sach-bhxh.aspx?CateID=0&ItemID=23352",
            "https://cms.baochinhphu.vn/quy-dinh-moi-ve-doi-tuong-muc-dong-bao-hiem-y-te-102250711120524105.htm",
            "https://isos.gov.vn/tin-hoat-dong/diem-tin/chinh-sach-bao-hiem-that-nghiep-thay-doi-the-nao-tu-112026-43755.html",
        ),
        ("bhxh", "bhyt", "bhtn", "luong", "bao hiem bat buoc"),
        ("M5L1", "M6L4"),
    ),
    Reference(
        "deposit_insurance_2026",
        "Quỹ khẩn cấp và phạm vi bảo hiểm tiền gửi",
        "Quỹ khẩn cấp ưu tiên khả năng rút khi cần và an toàn vốn. Ví điện tử/quỹ mở/MMF "
        "không mặc nhiên là tiền gửi được bảo hiểm, rút tức thì hay được bảo toàn vốn; phải "
        "phân biệt tiền gửi tại tổ chức tham gia BHTG với sản phẩm đầu tư/số dư ví. "
        "Thông tư05/2026/TT-NHNN: từ13/07/2026 hạn mức350triệu đồng gồm gốc+lãi thuộc diện "
        "được bảo hiểm của một người tại một tổ chức tham gia BHTG khi phát sinh nghĩa vụ chi trả. "
        "Không dùng hạn mức75triệu hoặc125triệu như mức hiện hành, không coi hạn mức là bảo đảm "
        "rút ngay hoặc bảo đảm mọi sản phẩm bán qua ngân hàng. Không tự nêu lãi gửi hiện hành "
        "không có nguồn/ngày. Lãi chính sách NHNN khác lãi tiền gửi bán lẻ.",
        (
            "https://www.div.gov.vn/han-muc-chi-tra-tien-bao-hiem-350-trieu-dong-viet-nam-dang-o-dau-so-voi-khu-vuc-va-the-gioi",
            "https://www.div.gov.vn/doi-moi-tai-chinh-va-so-hoa-nhung-van-de-dt-ra-doi-voi-he-thong-bao-hiem-tien-gui",
        ),
        ("quy khan cap", "quy du phong", "bao hiem tien gui", "gui tiet kiem", "an toan"),
        ("M2L1", "M2L5", "M4L1", "M8L10"),
    ),
    Reference(
        "digital_safety",
        "OTP/PIN và xử lý giao dịch lạ",
        "Không đọc, gửi, cung cấp OTP/PIN/mật khẩu/CVV cho bất kỳ ai, kể cả nhân viên và khi "
        "chính mình gọi tổng đài. Chỉ nhập mã trong ứng dụng/trang chính thức cho giao dịch "
        "mình chủ động, đã kiểm tra nội dung/số tiền/người nhận; không nhập mã vào link người gọi "
        "gửi. Tự lấy hotline trong app/thẻ/website chính thức; số gọi đến, tên email hay việc "
        "app không hiện cảnh báo không chứng minh danh tính. Sinh trắc học/thiết bị tin cậy "
        "không bảo đảm không mất tiền: còn lộPIN, máy mở khóa, ép buộc, chiếmSIM. Khi nghi lộ mã "
        "hay giao dịch lạ: ngừng chuyển tiền/liên lạc, khóa trên kênh chính thức và báo ngân hàng "
        "ngay, giữ chứng cứ, trình báo công an phù hợp. Yêu cầu tra soát/thu hồi khi có thể, "
        "không hứa hủy giao dịch đã hoàn tất trong vài giờ. Không hướng dẫn CSGT hay111 làm "
        "đầu mối chung cho vay/lừa ngân hàng; không gỡ app trước khi giữ chứng cứ.",
        (
            "https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2025/10/22/Thu-doan-gia-mao-the-Ngan-hang",
        ),
        ("otp", "pin", "vi dien tu", "bao mat", "giao dich la", "gia mao", "cuoc goi", "lua dao"),
        ("M4L4", "M7L4", "M9L1", "M9L2", "M9L3", "M9L4"),
    ),
    Reference(
        "cic_debt_groups",
        "CIC và phân loại nợ: không suy đoán thuật toán điểm",
        "Nguồn mô tả nhóm nợ không công bố công thức chấm điểm CIC. Không nhập quy tắcFICO "
        "(tuổi trung bình tài khoản, credit mix, trọng số, utilization30%) thành quy định CIC; "
        "không khẳng định đóng thẻ cũ luôn giảm điểm hay giữ thẻ mở chắc tốt hơn. "
        "Thanh toán đủ tối thiểu đúng hạn KHÔNG tự động là quá hạn/nợ xấu; chỉ trả tối thiểu "
        "có thể vẫn phát sinh lãi và kéo dài dư nợ. Phân loại nợ dựa trên toàn bộ tiêu chí "
        "áp dụng, không từ việc còn dư nợ hoặc chỉ trả tối thiểu. Miễn lãi và thời điểm bắt đầu "
        "tính lãi giao dịch mới tùy hợp đồng/sao kê; không khẳng định mọi giao dịch đều bị tính "
        "lãi ngay. Chưa có biểu phí/hợp đồng thì không nêu khoảng lãi suất hay tỷ lệ tối thiểu "
        "như thông lệ đã kiểm chứng; hỏi điều khoản trước. "
        "Hỏi ngân hàng về trạng thái đóng/tất toán, nghĩa vụ phí và cập nhật báo cáo; không hứa điểm phục hồi "
        "trong một số ngày. TT31/2024/TT-NHNN thay TT11/2021 từ01/07/2024; nợ xấu gồm nhóm3-5. "
        "Số ngày quá hạn chỉ là một tiêu chí, không bỏ cơ cấu nợ/định tính. Phân biệt nợ xấu "
        "pháp lý với cách nói nợ tạo giá trị/nợ tiêu dùng; tài sản nhà đất không chắc tăng giá.",
        ("https://vbpl.vn/binhduong/Pages/vbpq-toanvan.aspx?ItemID=168260",),
        ("cic", "tin dung", "diem tin", "no tot", "no xau", "dong the"),
        ("M3L1", "M3L4", "M3L5", "M4L5"),
    ),
    Reference(
        "lending_law",
        "Vay lãi nặng và lời hứa lợi nhuận",
        "Cho vay lãi nặng trong giao dịch dân sự được xem xét theo Điều201 BLHS và "
        "NQ01/2021/NQ-HĐTP, không phảiĐiều307. Giới hạn lãi dân sự thông thường20%/năm có "
        "theo Điều468 Bộ luật DÂN SỰ, có ngoại lệ theo luật; không áp máy móc cho tín dụng tổ chức được điều chỉnh riêng. "
        "Trách nhiệm hình sự cần điều kiện mức lãi và thu lợi bất chính/tiền sử theo luật, "
        "không phải cứ vượt20% là phạm tội. Lợi nhuận cao cam kết an toàn là dấu hiệu cảnh báo, "
        "chưa đủ để kết luận mọi lãi cố định đều bất hợp pháp. Phải kiểm pháp nhân/giấy phép "
        "đúng hoạt động, hợp đồng, nguồn tiền trả lãi, khả năng mất vốn và điều kiện rút. "
        "Không bảo chứng vì người quen; không coi thiếu giấy phép môi giới là bằng chứng "
        "duy nhất mọi hoạt động kinh doanh đều trái phép.",
        (
            "https://xaydungchinhsach.chinhphu.vn/cho-vay-tien-voi-lai-suat-cao-hon-lai-suat-quy-dinh-cua-phap-luat-se-bi-xu-ly-nhu-the-nao-119230404145343359.htm",
        ),
        ("lai nang", "tin dung den", "app vay", "cam ket", "loi nhuan", "gop von"),
        ("M3L7", "M8L10", "MK5L1"),
    ),
    Reference(
        "vbpl_24_2025",
        "Cổ phiếu, cổ tức và dẫn nguồn pháp luật",
        "Theo Điều4 Luật Chứng khoán54/2019: khoản2 định nghĩa cổ phiếu; khoản3 trái phiếu; "
        "khoản4 chứng chỉ quỹ. Không gán định nghĩa cổ phiếu vào khoản4, không gán quyền cổ đông "
        "vàoĐiều6 khi chưa đối chiếu. Cổ phiếu xác nhận phần vốn cổ phần, không phải khoản nợ "
        "được bảo đảm; cổ tức phổ thông phụ thuộc quyết định phân phối và điều kiện chi trả. "
        "Cổ tức tiền mặt theo tỷ lệ mệnh giá khác tỷ suất trên giá mua: tiền nhận trước thuế "
        "=số cổ phiếu*mệnh giá*tỷ lệ. Thiếu số cổ phiếu/mệnh giá/cơ sở tỷ lệ thì không suy tiền "
        "nhận từ tổng giá mua. Nêu rõ tiền mặt/cổ phiếu và thuế/phí nếu có. Lãi tiền gửi theo "
        "hợp đồng cũng có điều kiện, không gọi chắc chắn tuyệt đối.",
        ("https://vsd.vn/vi/ad/173046", "https://vanban.chinhphu.vn/?docid=198541&pageid=27160"),
        ("co phieu", "co tuc", "menh gia", "trai phieu"),
        ("MK1L1",),
    ),
    Reference(
        "tt_135_2025",
        "Phạm vi giáo dục và chứng cứ",
        "TT135/2025 quy định hành nghề chứng khoán; bản tóm tắt này không khẳng định "
        "Điều8/Điều12 nói về quảng cáo hoặc chatbot. Không tự dựng điều khoản hay kết luận "
        "mọi lãi suất/lợi nhuận cố định là bất hợp pháp. Giới hạn không chốt mã/lệnh mua bán "
        "của trợ giảng là chính sách sản phẩm, không phải trích nguyên văn một điều luật. "
        "Mẫu phân tích chưa có dữ liệu phải để trống hoặc dùng doanh nghiệpX ghi rõ giả định. "
        "Không gắn số tưởng tượng vớiVNM/FPT, không bịa trang báo cáo, ngày công bố, phát ngôn "
        "CEO, liên kết hay tên nguồn. Dữ kiện cần có đoạn dữ liệu hỗ trợ; URL có thật không "
        "tự chứng minh con số. Phát biểu có thể kiểm chứng chưa phải dữ kiện đã xác minh.",
        ("https://vanban.chinhphu.vn/?classid=1&docid=216437&orggroupid=4&pageid=27160",),
        ("mau", "ghi chu", "bang chung", "nhan dinh", "quang cao", "cam ket", "phan tich"),
        ("MK5L1", "MK5L2"),
    ),
)


def references_for(query: str = "", lesson_id: str | None = None) -> list[Reference]:
    text = normalize(query)
    return [
        ref
        for ref in REFERENCES
        if lesson_id in ref.lessons or any(term in text for term in ref.terms)
    ]


def reviewed_payload(source_id: str) -> dict | None:
    return next((ref.payload() for ref in REFERENCES if ref.id == source_id), None)


def reviewed_seed(source_id: str) -> str:
    return next(ref.context() for ref in REFERENCES if ref.id == source_id)
