# Chẩn đoán hai truy vấn chat — 2026-10-21

Phạm vi: đọc log backend và SQLite tracing hiện có, tái hiện validator/stream bằng dữ liệu giả lập, kiểm tra HTTPS công khai không gửi API key. Không thay đổi logic ứng dụng hay dữ liệu trace.

## 1. Câu hỏi phí ngân hàng bị từ chối trước khi vào agent

- Câu hỏi: `Những khoản phí ngân hàng nào mình nên kiểm tra?`
- Request ID: `b9d61fed-8221-4e55-b939-9839ec704162`.
- HTTP trace: `866e9850-d074-4f59-8c89-f882fbbc0336`.
- Log lúc `2026-10-21T16:01:39.985161Z` (23:01:39 giờ Việt Nam): `ticker_validator` chặn với lý do `Unrecognized ticker(s): TRA`.
- `src/infrastructure/guardrails/query_validator.py:250` chạy regex trên `query.upper()`. Từ thường `tra` thành `TRA` và bị coi là mã chứng khoán chưa có trong whitelist.
- Đã tái hiện trực tiếp: `passed=False`, `unknown_tickers=["TRA"]`.
- `src/interfaces/api/app.py:411` thay lý do cụ thể bằng `Query rejected.`, nên frontend chỉ hiển thị HTTP 400 chung chung.
- Agent chưa được chạy; số lần gọi LLM/tool của HTTP trace đều bằng 0.

## 2. Câu vẽ giá VNM thất bại ở kết nối LLM

- Câu hỏi: `Vẽ giá VNM 6 tháng`.
- Request ID: `274e22b3-8aad-4a75-b032-ef9d66dc29d9`.
- Agent trace: `a76e5974-6df6-477b-9cdd-f7c711e7416c`.
- Qua validator; trace mất `26439.18 ms`, có 5 span loại LLM, **0 tool call**, output `{"answer":""}`.
- NVIDIA embedding và chat gặp lỗi kết nối; pool đưa các key vào cooldown với `status=None`. Cooldown trong trường hợp này không chứng minh hết quota hay key không hợp lệ.
- Bộ tách câu hỏi thử 3 lần; cả primary NVIDIA (được log dưới nhãn `openai`) và fallback Groq đều lỗi. Sau đó reason node tiếp tục lỗi `APIConnectionError`.
- Chưa tới bước `generate_chart_spec` hoặc lấy giá; không có bằng chứng rằng lỗi hiện tại nằm ở dữ liệu VNM/vnstock.

### Kiểm tra mạng

GET công khai tới `/v1/models` của NVIDIA và `/openai/v1/models` của Groq:

| Môi trường | NVIDIA | Groq |
| --- | --- | --- |
| Trong sandbox | WinError 10013 | WinError 10013 |
| Ngoài sandbox | HTTP 200 | HTTP 403 |

Kết quả xác nhận sandbox hạn chế socket outbound; ngoài sandbox nhận được phản hồi HTTP. HTTP 403 của phép thử Groq không xác nhận một lời gọi chat có xác thực sẽ thành công. Chưa thực hiện lời gọi LLM có xác thực trong lượt chẩn đoán này.

Backend phục vụ bản xem trước được khởi động trong lượt trước qua môi trường thực thi sandbox. Cần khởi động backend trong môi trường có quyền mạng phù hợp, rồi kiểm tra lại lời gọi có xác thực; chưa có cơ sở yêu cầu đổi API key.

## 3. Thông báo lỗi bị mất trên luồng streaming

- `src/application/agents/agent.py:370`: khi LLM lỗi, reason node trả thông báo xin lỗi dạng `AIMessage`.
- `src/application/agents/agent.py:861`: `_run_single_stream` chỉ phát nội dung của `AIMessageChunk`.
- Đã chạy chính phương thức hiện tại với graph giả lập: `AIMessage` chứa thông báo lỗi cho output `[]`; `AIMessageChunk("normal token")` cho output `["normal token"]`.
- Điều này giải thích output trống thực tế. API vẫn gửi `final` với câu trả lời rỗng và ghi `completed`.
- `src/interfaces/api/app.py:480` còn nuốt exception trong producer; đây là đường khác có thể biến lỗi thành stream hoàn tất rỗng.

## 4. Trace hiện báo thành công dù yêu cầu lỗi

- HTTP 400 của câu phí ngân hàng có trace `status=ok`; mã HTTP chỉ nằm trong attributes.
- Trace VNM có `status=ok` và output rỗng dù span `ChatGroq` con có `status=error`.
- Các span `llm_provider.chain` có `all_providers_failed=true` nhưng vẫn `status=ok`: exception được raise tại `src/infrastructure/llm/llm_provider.py:286`, sau khi đã thoát context span.
- HTTP span kết thúc trước khi stream hoàn tất và dùng trace ID khác agent span, dù cùng request ID. Cần ghép theo request ID để xem đủ vòng đời.

## 5. Đường phát biểu đồ còn thiếu kết nối (phát hiện từ code)

- Frontend `useChatStream.ts` đã xử lý event `chart_spec`/`chart_error`.
- Backend có `_sse_chart_spec_event` và `_sse_chart_error_event`, nhưng endpoint `/ask-stream` hiện không gọi các hàm này; nó chỉ phát `chunk`/`final`/`error`.
- `_run_single_stream` cũng không chuyển kết quả tool `generate_chart_spec` thành event biểu đồ.
- Đây là thiếu sót độc lập cần sửa sau khi mạng LLM hoạt động. Trong request VNM thực tế, chưa gọi tool nên chưa thể đánh giá chất lượng dữ liệu hay chart-spec trả về.

## Thứ tự khắc phục đề xuất

1. Khởi động backend với quyền mạng phù hợp; kiểm tra lời gọi LLM có xác thực, không chỉ health endpoint.
2. Sửa nhận diện ticker để không chặn từ tự nhiên; thêm regression cho câu phí ngân hàng và các câu hỏi tài chính cá nhân.
3. Truyền lỗi có cấu trúc qua SSE; xử lý AIMessage cuối cùng, exception producer và câu trả lời rỗng; tránh phát trùng nội dung khi đã stream token.
4. Đánh dấu span/request lỗi đúng trạng thái và liên kết HTTP/agent trace suốt vòng đời streaming.
5. Nối kết quả tool chart-spec tới SSE/frontend; kiểm thử yêu cầu VNM 6 tháng với nguồn giá thật.

## Kết quả sau khi sửa

Đã sửa validator chỉ nhận token viết hoa rõ ràng là ticker; API trả lý do guardrail cụ thể. Agent và API chuyển lỗi qua SSE có cấu trúc, không hoàn tất với câu trả lời rỗng. Kết quả `generate_chart_spec` được kiểm tra bằng `ChartSpec` trước khi phát cho frontend. Yêu cầu chỉ vẽ biểu đồ kết thúc sau khi biểu đồ hợp lệ sẵn sàng; nếu tool lỗi tạm thời rồi thành công, không hiện cảnh báo cũ. Nguồn giá rỗng nay báo lỗi thay vì dựng điểm giá giả.

Đã sửa trạng thái span khi cả hai LLM đều lỗi, hợp nhất HTTP/stream/agent trong một trace và tính `duration_ms` tới lúc stream kết thúc. Lỗi mạng không còn tự động đưa mọi NVIDIA key vào cooldown. Backend preview được chạy lại với quyền mạng và cấu hình `.env` trỏ `QDRANT_PATH` đến `data/qdrant_local_v117`, nơi alias `finsight_knowledge` dùng chỉ mục 2048 chiều có 877 điểm dữ liệu. Chỉ mục 1536 chiều cũ được giữ nguyên trên đĩa.

Kiểm tra live sau khi sửa:

| Câu hỏi | Kết quả | Trace |
| --- | --- | --- |
| Phí ngân hàng | HTTP 200; trả lời 3.725 ký tự; `chunk` + `final`; 2 lần `search_knowledge` thành công; không còn lỗi lệch kích thước embedding | Request `6aeaa02d-2c12-42a5-8b61-3d73c388cac5`, trace `1cfa3a52-5e1e-40f7-aa9c-73d624df6708`, `status=ok` |
| VNM 6 tháng | HTTP 200; `chart_spec` + `chunk` + `final`; 126 phiên giá từ price service; không có event lỗi; 1 lần `generate_chart_spec` thành công | Request `d17b3b96-7fdd-47bc-83c5-e3e0cde41b3d`, trace `bd3c78e6-4577-4f6f-9c20-7d23f02bd239`, `status=ok`, `duration_ms=38626.58` |

Trace VNM cuối có `agent.stream` 38.570 giây và `http.stream` 38.592 giây trong cùng cây; không có span lỗi. Bộ test liên quan: 158 passed; kiểm tra riêng thay đổi thời lượng trace: 38 passed; chạy lại 5 regression API cuối: 5 passed. Ruff, TypeScript và production build frontend đều qua. Các lần gọi live phụ thuộc thời gian phản hồi của LLM/nguồn giá; kết quả trên xác nhận hai đường truy vấn tại thời điểm kiểm tra, không bảo đảm dịch vụ ngoài luôn sẵn sàng.
