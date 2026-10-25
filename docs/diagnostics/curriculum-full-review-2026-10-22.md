# Đánh giá nội dung đầy đủ 82 câu — 22/10/2026

Đã chạy và đọc toàn bộ **68 câu tài chính cá nhân + 14 câu thị trường**, chấm từng rubric và ghi bằng chứng nguyên văn. **Chưa đủ chất lượng để coi toàn bộ curriculum đã đạt.** Kiểm tra tự động gần như xanh nhưng còn lỗi số học, lời khuyên an toàn, luật hiện hành và nguồn minh họa.

| Lộ trình | Đủ kết quả | Đạt kiểm tra tự động | Đạt nội dung | Cần bổ sung/sửa | Không đạt nội dung |
|---|---:|---:|---:|---:|---:|
| Tài chính cá nhân | 68/68 | 67/68 | 24 | 21 | 23 |
| Thị trường tự chọn | 14/14 | 14/14 | 5 | 6 | 3 |

Không gộp thành một điểm hai lộ trình. Đây là đánh giá **Codex AI**, không phải duyệt độc lập của chuyên gia/con người; trạng thái đó vẫn `pending`. Các câu hỏi cùng curriculum là development examples, chưa phải kiểm tra khái quát hóa held-out. Kết quả áp dụng cho đúng câu trả lời của lần chạy này, không chứng minh tỉ lệ tái hiện qua nhiều lần lấy mẫu.

## Hồ sơ từng câu

- [68 câu tài chính cá nhân: rubric, bằng chứng, nhận xét và toàn văn trả lời](../../frontend/artifacts/curriculum-full-20261022/personal_finance.reviewed.md).
- [14 câu thị trường: rubric, bằng chứng, nhận xét và toàn văn trả lời](../../frontend/artifacts/curriculum-full-20261022/market_literacy.reviewed.md).
- [JSON 68 câu để kiểm toán/xử lý tiếp](../../frontend/artifacts/curriculum-full-20261022/personal_finance.reviewed.json), [JSON 14 câu](../../frontend/artifacts/curriculum-full-20261022/market_literacy.reviewed.json).
- [Nguồn pháp lý/dữ liệu đối chiếu và giới hạn xác minh](../../frontend/artifacts/curriculum-full-20261022/sources.md).
- [Ghi chú chấm do AI soạn](../../frontend/artifacts/curriculum-full-20261022/review-notes.jsonl). Script `evals/render_curriculum_review.py` kiểm tra đủ ID, số điểm bằng số rubric, và mọi trích dẫn có nguyên văn trong đáp án; script không tự chấm bằng từ khóa.

## Tiêu chí chấm

Mỗi rubric được chấm0(sai/thiếu),1(một phần),2(đúng và rõ). Tiêu chí có điều kiện không liên quan câu hỏi cụ thể được ghiN/A và giải thích trong nhận xét. Không ép người hỏi một phép chia đơn giản phải nhận toàn bộ nội dung một bài học rộng.

`pass`: đáp đúng câu hỏi và các tiêu chí áp dụng, không có lỗi trọng yếu phát hiện. `partial`: cơ bản đúng nhưng thiếu giải thích/chứng cứ/giới hạn hoặc có phát biểu cần sửa cục bộ. `fail`: có sai số học làm hỏng hướng dẫn, chỉ dẫn bảo mật nguy hiểm, pháp lý sai/cũ hoặc nguồn/số minh họa không được chứng minh. Verdict còn xét lỗi quan trọng ngoài rubric hẹp; vì vậy một câu có hỏi đủ đầu vào vẫn có thể fail khi tự giảng sai luật2026.

Bằng chứng là các đoạn nguyên văn trong câu trả lời và chart/tool result của chính lần chạy. Các câu fail không được sửa đáp án rồi giữ điểm cho câu cũ. Nguồn bên ngoài chỉ dùng đối chiếu các khẳng định nhạy cảm; không chứng nhận mọi chi tiết luật/dữ liệu của tất cả câu đã được chuyên gia xác minh.

## Các nhóm phải sửa trước khi xuất bản

| Ưu tiên | Nhóm | Bằng chứng/case tiêu biểu | Hành động cần làm |
|---|---|---|---|
| P0 | OTP/PIN | M4L4 cho phép nhậpOTP/PIN khi tự gọi tổng đài, mâu thuẫn với không chia sẻ | Chỉ nhập trong kênh chính thức cho giao dịch do mình chủ động; không đọc/gửi mã cho người gọi hoặc tổng đài. |
| P0 | Thuế hiện hành | `tax_missing_inputs` quay về11/4,4 triệu và7 bậc; M6L1 bỏ bảo hiểm; M6L2 cho vợ không đi làm tự động đủ điều kiện; M6L3 dựng ngưỡng100 triệu và hạn31/3 cho cá nhân | Dùng nguồn áp dụng2026, phân biệt thu nhập chịu/tính thuế, điều kiện giảm trừ và ngoại lệ quyết toán; cập nhật rubric case thiếu dữ liệu. |
| P0 | Nguồn minh họa | MK5L2 tự đưa sốVNM/FPT cùng trang/ngày báo cáo khi không truy xuất | Dùng ô trống hoặc doanh nghiệp giả định, không giả nguồn. Kiểm lại bằng chứng từng con số. |
| P1 | Bảo toàn tiền/quỹ | M1L4 thu10 triệu nhưng rút1 triệu để đủ nền9; M8L9 có100 triệu/quỹ72 mà cho dùng30–50; `budget_zero` lương15 nhưng nạp18 triệu trước chi sống | Kiểm tổng thu-chi, tồn quỹ, phép trừ và tính khả thi trước phát hành. |
| P1 | Tính khoản vay | M3L6 sai tổng lãi; M8L8 khoản trả9 triệu/9%/20 năm suy1,1 tỷ | Dùng calculator thật, nêu cách trả và phí; đối chiếu prose với kết quả. |
| P1 | Bảo hiểm | M2L1 đánh đồng ví/quỹ với BHTG; M5L2/M5L3 sai thời gian cân nhắc; M8L10 nêu hạn mức75 triệu | Tách sản phẩm/phạm vi, kiểm văn bản hiệu lực và điều kiện hợp đồng. |
| P1 | CIC và luật vay | M3L5/M4L5 suy cơ chếFICO thành CIC; M3L7 dẫnĐiều 307 | Không khẳng định thuật toán chưa công bố; thay nguồn cũ, kiểm đúngĐiều 201 và điều kiện áp dụng. |
| P1 | Cổ tức/phạm vi luật | MK1L1 suy5% giá mua; MK5L1/fraud_return nói mọi lợi nhuận cố định đều bất hợp pháp | Nêu số cổ phiếu/mệnh giá/cơ sở tính; phân biệt dấu hiệu cảnh báo với kết luận pháp lý. |
| P2 | Cách dạy và ngôn ngữ | Bài tự kiểm tra thiếu đầu vào, biểu đồclose bị mô tả bằnghigh, chữ ngoại ngữ lỗi chen vào | Kiểm câu tự hỏi có đáp số xác định; phân biệt field; làm sạch văn bản. |

Các sửa nội dung trên **chưa được triển khai vào prompt/dataset/nguồn RAG trong công việc này**; bảng là kết quả đánh giá cần xử lý tiếp. Đường gọi MCP và bộ kiểm tra lỗi công cụ đã được sửa để việc đánh giá chạy đúng.

## API/MCP và mã mới

Khi bắt đầu không có API/MCP của dự án lắng nghe. Đã khởi động standalone MCP:8001 và API:8000 bằng môi trường `.venv` có sẵn, rồi khởi động lạiAPI sau bản sửa thực thi công cụ.

Phát hiện khi bỏ fallback nội bộ: công cụMCP qua mạng là `StructuredTool` chỉ có coroutine, nhưng action node gọi `.invoke()`, gây `StructuredTool does not support sync invocation`. `custom_tool_node.py` hiện dùng `.ainvoke()` với cầu nối đồng bộ, giữ context khi caller có event loop, và tháo text content blocks để chart JSON đi qua như công cụ nội bộ. Bổ sung `no_tool_error` vào evaluator để lỗiTOOL_ERR không được tính đạt; chưa coi check này là chứng nhận mọi dữ liệu upstream hợp lệ.

Đã kiểm tra thực tế: `tools/list` nhận20 tools; `budget_template` qua mạng trả6m/3,6m/2,4m; API `/health` trả200, `agent_ready=true`; đăng nhậpdemo200; `/api/v1/ask-stream`200 có`chart_spec`, không có`error`. [Bằng chứng triển khai và hash nguồn](../../frontend/artifacts/curriculum-full-20261022/deployment-check.json), [SSE ngân sách](../../frontend/artifacts/curriculum-full-20261022/api-budget-smoke.sse).

**60 kiểm thử hồi quy đạt**, Ruff đạt cho các file sửa/thêm. Kiểm thử tập trung agent/action node, scope, evaluator, API/SSE và chart; không phải toàn bộ test suite của repository. Có cảnh báo deprecation LangChain và lần thử export LangSmith bị sandbox chặn trong test; không ảnh hưởng60 kết quả, không có bằng chứng export thành công. Các lượt benchmark đặt cả hai cờ tracing bên ngoài=false, giữ trace cục bộ.

## Tính đầy đủ và tái lập

Raw reports: [68 câu](../../frontend/artifacts/curriculum-full-20261022/personal_finance.json), [14 câu](../../frontend/artifacts/curriculum-full-20261022/market_literacy.json). Giữ `semantic_review` gốc pending; phần `ai_semantic_review` riêng có hash đáp án để truy vết. Chạy đầu gặp lỗi sync MCP được giữ trong`pilot-sync-error`, không dùng làm điểm chính.

14 câu cá nhân đầu được bảo toàn từ checkpoint;54 câu còn lại chạy3tiến trình độc lập, mỗi tiến trình18 câu, cùng mã/model cấu hình, không patch agent đang phục vụAPI. Báo cáo gộp theo đúng thứ tựdataset, kiểm chính xác68 ID duy nhất, ghi file phần/hash; checkpointpart0 vẫn có nhãn`running` gốc do bị dừng có chủ đích, nhưng không dùng nó để tự nhận đủ68 câu. Báo cáo cuối chỉ`completed` sau khi đối chiếu đủ tập ID và3 phần còn lại hoàn tất.

`loan_zero_rate` là một lỗi tự động do không gọi tool bắt buộc: đáp số1 triệu/tháng vẫn đúng nội dung. Không sửa benchmark sau khi biết kết quả để tăng điểm. Chartbudget/inflation khớp các fixture số đã định nghĩa.

Độ trễ ở lần chạy: cá nhân p50≈17,2s/p95≈56,3s; thị trường p50≈29,8s/p95≈84,6s (ước lượng percentile theo thứ hạng trên mẫu nhỏ). Không phải SLO và chưa có benchmark tải đồng thời API.

Tạo lại bản hiển thị từ kết quả và ghi chú hiện có:

```powershell
& .\.venv\Scripts\Activate.ps1
python evals/render_curriculum_review.py frontend/artifacts/curriculum-full-20261022
```
