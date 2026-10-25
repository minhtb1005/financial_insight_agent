# AGENTS.md — Financial Insight Agent

## Mục tiêu

Repo này là trợ lý phân tích chứng khoán Việt Nam: LangGraph agent, FastAPI, Next.js, nguồn dữ liệu thị trường và bộ đánh giá. Đọc `README.md` trước khi thay đổi. Chỉ thiết lập Vnstock khi tác vụ yêu cầu; không tự động cài công cụ, phát hiện gói tài khoản hay tải dữ liệu ở đầu mọi phiên.

## Quy trình cho mỗi tác vụ

1. Đọc yêu cầu và các file liên quan trong `docs/`. Kiểm tra `git status`; giữ nguyên thay đổi có sẵn. Xác định một phạm vi nhỏ cùng tiêu chí hoàn thành có thể kiểm chứng (đầu vào, đầu ra, trường hợp lỗi và lệnh test).
2. Đọc đúng module trước khi sửa. Không coi ý tưởng hoặc số liệu trong README là tính năng đã triển khai; kiểm tra code và test. Không tự mở rộng sang việc huấn luyện ML hay thay đổi phạm vi sản phẩm nếu yêu cầu không nêu.
3. Sửa theo quy ước sẵn có, chạy kiểm tra phù hợp, ghi kết quả thực tế. Nếu thiếu API key, dịch vụ ngoài hoặc dữ liệu, ghi rõ **chưa xác minh đầy đủ** và lệnh cần chạy tiếp.
4. Kết thúc bằng bản bàn giao: mục tiêu, file đổi, bằng chứng kiểm thử, giả định, rủi ro, việc còn mở và trạng thái working tree. Nếu tác vụ kéo dài nhiều phiên, cập nhật `WORKFLOW_STATE.md` local khi có và bàn giao ngắn trong PR.

## WORKFLOW_STATE.md và compact

`WORKFLOW_STATE.md` là ghi chú local, dài và không commit lên repo. Nếu file có trong working tree, đọc `AGENTS.md`, yêu cầu mới nhất rồi đọc phần trạng thái hiện hành và các mục liên quan của `WORKFLOW_STATE.md` trước khi tiếp tục việc cũ. Kiểm tra lại bằng code và `git status`; ghi chú lịch sử không thay thế yêu cầu mới. Nếu file không có trong clone, không tự coi tác vụ đã hoàn tất: đọc PR/commit và hỏi phần trạng thái còn thiếu chỉ khi nó thực sự chặn công việc.

Cập nhật file local sau khi chốt phạm vi, sau mốc triển khai hoặc kiểm thử quan trọng, và trước khi dừng/chuyển phiên. Giữ rõ mục tiêu, trạng thái hiện tại, quyết định còn hiệu lực, file/PR/commit, lệnh và kết quả thực tế, blocker, bước tiếp theo. Không ghi pass cho test chưa chạy, không lưu secret hoặc dữ liệu nhạy cảm. Không tự commit hoặc ép `git add -f` file này. Khi làm ở clone khác, đưa bản bàn giao ngắn vào PR hoặc trao trực tiếp cho người dùng; không yêu cầu họ công khai nhật ký vài nghìn dòng.

Khi file phình lớn, các phiên lặp lại cùng bối cảnh, hoặc trước handoff dài hạn, compact **phần lịch sử đã ổn định**. Nếu môi trường agent có cave-man skill, đọc hướng dẫn skill rồi dùng nó để compact; xem diff để bảo toàn trạng thái hiện tại, quyết định, bằng chứng, blocker và bước tiếp theo. Nếu không có skill, compact thủ công theo cùng tiêu chí; không tự cài một skill không rõ nguồn. Không compact giữa một bước chưa ghi đủ bằng chứng và không biến việc chưa xong thành hoàn thành.

## Bản đồ repo

- `src/application/`: điều phối use case và agent; `src/domain/`: nghiệp vụ; `src/infrastructure/`: nguồn dữ liệu, DB và tích hợp; `src/interfaces/`: API; `src/shared/`: mã dùng chung.
- `src/tests/unit/`, `src/tests/integration/`: kiểm thử; cấu hình pytest trong `pyproject.toml`. Integration có thể cần dịch vụ ngoài.
- `evals/`: golden dataset, benchmark và baseline; đọc `evals/README.md` trước khi sửa prompt, tool, RAG, dashboard hoặc dữ liệu.
- `frontend/`: Next.js; đọc `frontend/AGENTS.md` khi sửa UI. `docs/` có đặc tả API, RAG và observability. `.github/workflows/ci.yml` là nguồn tham chiếu cho lệnh CI.

## Môi trường

- CI dùng Python 3.13. Tạo `.venv` riêng cho repo; `python -m pip install -e ".[dev]"` từ `pyproject.toml`. Phiên bản Vnstock trong manifest là `>=3,<4`; không nâng lên 4.x chỉ vì hướng dẫn onboarding cũ nói vậy.
- Frontend: chạy `npm ci` trong `frontend/`; `npm run dev` để phát triển. Backend và dịch vụ phụ trợ theo `README.md` / `docker-compose.dev.yml`. Không khởi chạy migration, crawl hoặc benchmark live cho thay đổi tài liệu.
- Key trong biến môi trường hoặc `.env` được gitignore; không đưa key vào code, URL truy vấn, log hoặc hội thoại. Không tự động phát hiện tier/sync skill của Vnstock. Nếu setup Vnstock là mục tiêu, đọc tài liệu gói và đối chiếu dependency của repo trước khi cài.

## Docker khi người dùng yêu cầu bật/chạy

Không tự khởi động Docker cho tác vụ chỉ sửa tài liệu. Khi người dùng yêu cầu, xác định đang ở WSL/Linux hay Windows PowerShell; chạy `docker version`, `docker info`, `docker context show` để biết daemon và context hiện có. Không tự xóa volume hoặc chạy `down -v`.

- Trong WSL: nếu `docker info` hoạt động, dùng daemon hiện có. Nếu chưa, kiểm tra Docker Desktop trên Windows và WSL integration trước; có thể dùng Docker Engine riêng trong distro nếu đã được cấu hình. Không giả định `systemctl` hoạt động hoặc bật hai daemon cùng lúc.
- Trên Windows: kiểm tra `Get-Command docker` và `Test-Path "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"`. Nếu Docker Desktop đã cài và người dùng yêu cầu bật, chạy `Start-Process "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"`, đợi `docker info` thành công. Nếu dùng WSL, xác nhận lại `docker info` trong distro; khi integration chưa có, báo bước cấu hình cần thiết.
- Kiểm tra `docker compose version`, file `.env`, port và volume. Với dev, chạy `docker compose -f docker-compose.dev.yml config`, rồi `docker compose -f docker-compose.dev.yml up -d --build`; chỉ dùng `docker-compose.yml` production khi được yêu cầu. Kiểm tra `docker compose -f docker-compose.dev.yml ps`, logs và healthcheck. Backend production có migration, scheduler/API có thể dùng dịch vụ ngoài; xác nhận môi trường dữ liệu trước khi bật.

## Xác minh và định nghĩa hoàn thành

Chạy test gần phần sửa trước, sau đó chọn bước tương ứng. Không tuyên bố hoàn thành chỉ vì code trông hợp lý.

| Phạm vi | Kiểm tra |
|---|---|
| Backend Python | `pytest src/tests/unit/ -q`, `ruff check src/`, `black --check src/`; thêm integration liên quan khi đổi API/DB/agent. |
| Type check | `mypy src/ --ignore-missing-imports --no-strict-optional`; CI đang `continue-on-error`, nên báo lỗi nếu có thay vì coi job xanh là đạt. |
| Frontend | Trong `frontend/`: `npm run lint`, `npx tsc --noEmit`, `npm run build`; thử luồng UI liên quan khi có thể. |
| Golden dataset | `python evals/scripts/validate_golden_dataset.py`. |
| Agent / prompt / dashboard | Chọn smoke và benchmark theo `evals/README.md`; so report với baseline cùng tập case bằng `evals/compare_reports.py`. Ghi rõ model, dataset, ngày dữ liệu và case bỏ qua. |

Benchmark có thể gọi API và tốn chi phí; chỉ chạy khi tác vụ cần, không dùng `--pin-baseline` để ghi đè chuẩn nếu không được yêu cầu. Với dự báo tài chính, định nghĩa target, horizon, thời điểm dữ liệu khả dụng, cách chia theo thời gian, baseline, metric và kiểm tra leakage trước khi nói mô hình cải thiện. Một tác vụ đạt khi tiêu chí đã nêu được kiểm tra bằng bằng chứng thực thi; nếu không thể chạy thì bàn giao trạng thái còn thiếu xác minh.
