# Sửa nội dung trợ giảng — 22/10/2026

Đã sửa mã và nguồn dùng để sinh câu trả lời về OTP, thuế, bảo hiểm, số học và ví dụ có dẫn nguồn. API/MCP đã được khởi động lại. Các kết quả bên dưới phân biệt kiểm thử mã, câu trả lời thực tế và lỗi dịch vụ; không coi việc thêm hướng dẫn là bằng chứng mọi câu trả lời đều đúng.

## Thay đổi

| Nhóm | Sửa cụ thể |
|---|---|
| OTP | Không cung cấp OTP/PIN/CVV cho người khác, kể cả khi chủ động gọi tổng đài. Chỉ nhập trên kênh chính thức cho giao dịch đã kiểm tra; không hứa thu hồi giao dịch trong vài giờ. |
| Thuế | Nêu đúng kỳ áp dụng; công thức có bảo hiểm, giảm trừ hợp lệ và sàn 0. Bỏ lương mặc định khi chưa được cung cấp; phân biệt điều kiện từng nhóm người phụ thuộc và các trường hợp quyết toán. Công cụ chỉ mô hình hóa tiền lương cá nhân cư trú năm 2026. |
| Bảo hiểm | Sửa thời gian cân nhắc, phân biệt BHYT với bảo hiểm thương mại và phần đóng của người lao động/doanh nghiệp. Không suy rằng chưa có người phụ thuộc thì không cần bảo hiểm sức khỏe. |
| Số học | Bổ sung tính ngược số tiền vay theo khoản trả tháng và kiểm tiền dư sau quỹ dự phòng. Làm rõ phương thức trả nợ, lạm phát được yêu cầu và đầu vào còn thiếu. Không đoán số năm trả hết thẻ khi chưa biết sàn thanh toán/điều khoản. |
| Nguồn và minh họa | Thay các seed sai; ghi rõ tóm tắt biên tập, ngày đối chiếu và URL. Chặn seed cũ cùng ID trong kết quả RAG. Mẫu chưa có chứng cứ dùng ô trống/Doanh nghiệp X; không dựng số liệu, trang báo cáo hay phát ngôn của doanh nghiệp thật. Bỏ việc gán chính sách không chốt lệnh của sản phẩm thành điều khoản TT135. |

Các tóm tắt nguồn nằm trong `src/application/learning/references.py`. Chúng có nhãn biên tập, không phải nguyên văn luật hoặc điểm tương đồng vector. Khi embeddings không hoạt động, tóm tắt liên quan vẫn dùng được và lỗi truy xuất vẫn được ghi nhận.

Các câu hỏi khái niệm phù hợp về OTP, thuế năm 2026, điều kiện người phụ thuộc, bảo hiểm và thanh toán tối thiểu dùng lời giải đã biên tập kèm nguồn trong `concepts.py`, độc lập với ID bài học. Mẫu ghi chú dùng các ô chưa có dữ liệu. Câu tính thuế có số tiền cụ thể và câu hỏi kỳ thuế khác tiếp tục qua công cụ/luồng mô hình; không bị thay bằng bài giải chung.

Với câu trả lời học tập còn lại, một lượt biên tập LLM nhận câu hỏi, bản nháp, nguồn liên quan và kết quả công cụ thực tế. Mã kiểm tra thêm bằng chứng công cụ khi xuất ví dụ khoản trả/tổng lãi: thiếu kết quả vay hợp lệ thì thay bằng công thức và yêu cầu đầu vào, không phát số ước lượng. Bản nháp/token trung gian không phát ra SSE. Nếu lượt biên tập lỗi, API phát sự kiện lỗi thay vì gửi lại bản nháp chưa kiểm tra. Lượt này làm tăng số lần gọi mô hình và độ trễ; không thay thế đánh giá độc lập của con người.

## Kiểm chứng mã và tích hợp

- **69 kiểm thử đạt**, gồm tính toán, nguồn cũ/ngoại tuyến, phạm vi công cụ, cầu nối MCP bất đồng bộ, không phát bản nháp, lỗi dịch vụ, bằng chứng tính vay và lời giải khái niệm. Sau bổ sung kỳ thuế đã kiểm lại riêng 9/9 kiểm thử biên tập. Có một cảnh báo deprecation từ LangGraph.
- Ruff kiểm tra các tệp sửa đạt; cú pháp Python và mẫu prompt được kiểm tra riêng.
- MCP thật công bố **20 công cụ**. Các giá trị được kiểm trực tiếp: vay 12 triệu, lãi cố định 12%/năm, 6 tháng → khoảng 2.070.580 đồng/tháng, tổng lãi 423.482 đồng; khả năng trả 9 triệu/tháng, 9%/năm, 240 tháng → gốc khoảng 1.000.304.586 đồng; thuế lương 30 triệu, bảo hiểm 3,15 triệu, một người phụ thuộc hợp lệ → 257.500 đồng; tiền mặt 120 triệu trừ quỹ 15 triệu × 6 tháng → dư 30 triệu trước nghĩa vụ khác.
- Câu OTP ngoài bộ mẫu qua API/SSE sau khởi động lại đã trả lời rõ không đọc mã kể cả tự gọi tổng đài, không có sự kiện lỗi.

Kết quả tích hợp có đầu vào, đầu ra và cờ kiểm tra số tại [deployment-check-retry-otp.json](../../frontend/artifacts/content-fixes-20261022/final/deployment-check-retry-otp.json). Lần probe trước dùng nhầm tên tham số `insurance_monthly`; báo cáo lần đó được giữ để truy vết, không dùng để xác nhận phép tính thuế. Lần xác nhận dùng trường `insurance` đúng schema.

## Trạng thái 82 câu

Lần sửa đầu đã chạy đủ 82 câu, đạt kiểm tra tự động 66/68 ở tài chính cá nhân và 14/14 ở hiểu thị trường. Đọc nội dung cho thấy vẫn còn lỗi ước đoán thời gian trả nợ, phí vay, đầu vào mẫu và điều kiện người phụ thuộc. Vì vậy đã bổ sung hướng dẫn, nguồn và lượt biên tập cuối; không dùng số kiểm tra tự động này làm điểm chất lượng nội dung.

Lần chạy đủ 82 câu có lượt biên tập LLM, trước khi bổ sung lời giải khái niệm và kiểm tra bằng chứng vay, gặp NVIDIA **429** và Groq dự phòng **401**. Chỉ 4/82 trả lời đạt kiểm tra tự động; 78 câu có lỗi dịch vụ. **Không thể xác nhận 82/82 đã đúng nội dung với mã cuối.** Các lần lỗi được giữ nguyên, không thay bằng kết quả của phiên bản trước.

Đã kiểm lại tuần tự 14 câu trọng yếu: 14/14 đạt kiểm tra tự động sau 16 lượt thử, lưu tại [priority-retries.json](../../frontend/artifacts/content-fixes-20261022/final/priority-retries.json). Đọc nội dung vẫn thấy M3L4 đánh đồng trả tối thiểu với quá hạn, M3L6 đưa số vay chưa tính, M5L2 dùng sai điều kiện mua bảo hiểm và M6L1 thêm giảm trừ chưa có căn cứ. Kết quả này dẫn đến bổ sung lời giải biên tập và kiểm tra bằng chứng trong mã cuối; **14/14 tự động không được coi là 14 câu đúng nội dung**.

Sau lần khởi động cuối, **10/10 tình huống API/SSE thành công**, đã đọc nội dung: OTP, thiếu báo giá sửa laptop, vợ khỏe mạnh đang thất nghiệp, nhu cầu bảo hiểm khi độc thân, BHYT/thương mại, loại trừ/thời gian chờ, công thức thuế, quyết toán nhiều nơi, thanh toán thẻ tối thiểu và mẫu ghi chú có nguồn. Các lỗi nội dung nêu trên không còn trong những phản hồi đã lưu này. Tám câu đầu thành công; hai câu cuối được thử sau cửa sổ giới hạn tốc độ nội bộ. Không gộp thành điểm 82 câu.

Bằng chứng bản cuối: [tổng hợp kiểm chứng](../../frontend/artifacts/content-fixes-20261022/final/release-verification.json), [8 tình huống đầu](../../frontend/artifacts/content-fixes-20261022/final/deployment-check-release.json), [2 tình huống cuối và phép tính MCP](../../frontend/artifacts/content-fixes-20261022/final/deployment-check-release-tail.json), [dấu vân tay mã nguồn](../../frontend/artifacts/content-fixes-20261022/final/release-source-manifest.json). Đánh giá nội dung do Codex AI thực hiện; chưa có người đánh giá độc lập.

Thư mục [bằng chứng](../../frontend/artifacts/content-fixes-20261022/final/) chứa báo cáo gốc của hai lộ trình, log API/MCP, phản hồi SSE và dấu vân tay mã nguồn. [Đánh giá 82 câu trước sửa](curriculum-full-review-2026-10-22.md) được giữ nguyên để đối chiếu.

## Nguồn đối chiếu

- [Cảnh báo OTP của Vietcombank](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2025/10/22/Thu-doan-gia-mao-the-Ngan-hang).
- [Luật thuế TNCN 109/2025](https://vanban.chinhphu.vn/?docid=216495&pageid=27160), [biểu thuế và kỳ áp dụng](https://chinhsachonline.chinhphu.vn/thoi-diem-ap-dung-bieu-thue-thu-nhap-ca-nhan-moi-84963.htm), [hướng dẫn người phụ thuộc](https://baochinhphu.vn/quy-dinh-moi-ve-thue-thu-nhap-ca-nhan-102260707165524772.htm), [quyết toán](https://xaydungchinhsach.chinhphu.vn/quy-dinh-quyet-toan-thue-thu-nhap-ca-nhan-119260703162819669.htm).
- [Luật kinh doanh bảo hiểm](https://xaydungchinhsach.chinhphu.vn/toan-van-luat-kinh-doanh-bao-hiem-119240130070753445.htm), [mức đóng BHYT](https://cms.baochinhphu.vn/quy-dinh-moi-ve-doi-tuong-muc-dong-bao-hiem-y-te-102250711120524105.htm), [bảo hiểm tiền gửi](https://www.div.gov.vn/han-muc-chi-tra-tien-bao-hiem-350-trieu-dong-viet-nam-dang-o-dau-so-voi-khu-vuc-va-the-gioi).
- [Cho vay lãi nặng](https://xaydungchinhsach.chinhphu.vn/cho-vay-tien-voi-lai-suat-cao-hon-lai-suat-quy-dinh-cua-phap-luat-se-bi-xu-ly-nhu-the-nao-119230404145343359.htm), [ví dụ thông báo cổ tức trên mệnh giá của VSDC](https://vsd.vn/vi/ad/173046), [văn bản TT135/2025](https://vanban.chinhphu.vn/?classid=1&docid=216437&orggroupid=4&pageid=27160).
