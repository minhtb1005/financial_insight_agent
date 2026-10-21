import source from "@/content/curriculum.json"

export type Lesson = { id: string; title: string; originalTitle: string; topics: string[]; activity: string; question: string }
export type CourseModule = { id: string; title: string; description: string; outcome: string; stage: string; hours: number; lessons: Lesson[] }

export const MODULE_STORIES: Record<string, { title: string; description: string; outcome: string; stage: string }> = {
  M1: { title: "Tiền của mình đi đâu?", description: "Từ lần quẹt thẻ vô thức đến một kế hoạch chi tiêu có chủ đích.", outcome: "Bản đồ chi tiêu và ngân sách đầu tiên", stage: "Làm chủ mỗi ngày" },
  M2: { title: "Một khoản để an tâm", description: "Chuẩn bị cho những ngày cuộc sống không đi đúng kế hoạch.", outcome: "Kế hoạch xây quỹ dự phòng của riêng bạn", stage: "Làm chủ mỗi ngày" },
  M3: { title: "Hiểu nợ, bớt áp lực", description: "Đọc rõ chi phí đi vay và tìm cách sắp xếp các khoản nợ.", outcome: "Bảng ưu tiên và lộ trình trả nợ", stage: "Làm chủ mỗi ngày" },
  M4: { title: "Dùng ngân hàng thông minh", description: "Hiểu tiền trong tài khoản, lãi suất và những khoản phí dễ bỏ quên.", outcome: "Danh sách kiểm tra tài khoản và dịch vụ", stage: "Bảo vệ nền tảng" },
  M5: { title: "Bảo vệ điều quan trọng", description: "Bắt đầu từ nhu cầu của mình trước khi đọc một lời chào bảo hiểm.", outcome: "Bản đồ nhu cầu bảo vệ và câu hỏi cần hỏi", stage: "Bảo vệ nền tảng" },
  M6: { title: "Hiểu lương, rõ nghĩa vụ", description: "Tự tin đọc bảng lương, nhận diện chứng từ và tìm đúng nguồn thuế.", outcome: "Checklist bảng lương và hồ sơ thuế", stage: "Bảo vệ nền tảng" },
  M7: { title: "Bình tĩnh trước nút mua", description: "Nhận ra cảm xúc, quảng cáo và áp lực đang ảnh hưởng đến ví tiền.", outcome: "Bộ quy tắc chi tiêu có chủ đích", stage: "Bảo vệ nền tảng" },
  M8: { title: "Viết kế hoạch cho tương lai", description: "Chuyển những dự định lớn thành các câu hỏi và con số cụ thể.", outcome: "Bản kế hoạch tài chính theo giai đoạn sống", stage: "Đi đường dài" },
  M9: { title: "Giữ tiền an toàn trên mạng", description: "Luyện cách dừng lại, kiểm tra và phản ứng trước dấu hiệu bất thường.", outcome: "Checklist bảo mật và kịch bản ứng phó", stage: "Đi đường dài" },
  M10: { title: "Cùng nhau nói chuyện tiền", description: "Tìm tiếng nói chung với bạn đời, cha mẹ và những người thân yêu.", outcome: "Bản thỏa thuận tiền bạc trong gia đình", stage: "Đi đường dài" },
}

export const LESSON_TITLES: Record<string, string> = {
  M1L1: "Ngày nhận lương, chia tiền thế nào?", M1L2: "Mình cần hay chỉ đang muốn?", M1L3: "Theo dấu từng khoản chi", M1L4: "Nếu tháng sau thu nhập thay đổi?", M1L5: "Một lần freeship, bao nhiêu lần phí?", M1L6: "Sống ổn với ngân sách sinh viên", M1L7: "Ở chung vui, chia tiền rõ",
  M2L1: "Một khoản dành cho những bất ngờ", M2L2: "Biến điều muốn làm thành mục tiêu", M2L3: "Dành một phần cho mình trước", M2L4: "Bắt đầu nhỏ vẫn là bắt đầu", M2L5: "Thu nhập thất thường, quỹ vẫn có kế hoạch",
  M3L1: "Khoản vay này có phục vụ mình?", M3L2: "Nhiều khoản nợ, bắt đầu từ đâu?", M3L3: "Đọc phần chữ nhỏ trước khi vay", M3L4: "Dùng thẻ chủ động, nhớ ngày thanh toán", M3L5: "Lịch sử tín dụng kể gì về bạn?", M3L6: "Dùng tiền để dành hay đi vay?", M3L7: "Vay nhanh: dừng lại một nhịp",
  M4L1: "Mỗi tài khoản, một nhiệm vụ", M4L2: "Lãi nhận được, sức mua còn lại", M4L3: "Những khoản phí âm thầm", M4L4: "Chuyển tiền đúng, xác minh trước", M4L5: "Dọn gọn chiếc ví tài chính",
  M5L1: "Bạn đang cần bảo vệ điều gì?", M5L2: "Nhu cầu của mình hay lời chào hấp dẫn?", M5L3: "Đọc hợp đồng bằng những câu hỏi đúng",
  M6L1: "Từ thu nhập đến nghĩa vụ thuế", M6L2: "Khoản nào cần kiểm tra giảm trừ?", M6L3: "Đến kỳ kê khai, hồ sơ ở đâu?", M6L4: "Công việc đầu tiên, đọc kỹ bảng lương",
  M7L1: "Cảm xúc đang cầm ví của bạn?", M7L2: "Đừng để bảng tin quyết định ngân sách", M7L3: "Một thói quen nhỏ, một mục tiêu rõ", M7L4: "Lời hứa quá đẹp: kiểm tra lại",
  M8L1: "Cuộc sống bạn muốn có hình gì?", M8L2: "Hình dung một ngày không còn đi làm", M8L3: "Chuẩn bị cho cột mốc lớn", M8L4: "Chụp một bức ảnh tài chính của mình", M8L5: "Cùng một số tiền, khác một thời điểm", M8L6: "Sáu bước từ dự định đến kế hoạch", M8L7: "Giá mua chưa phải toàn bộ chi phí", M8L8: "Thuê hay mua: đặt các con số lên bàn", M8L9: "Khởi nghiệp, vẫn giữ nền tảng riêng", M8L10: "Hiểu rõ trước khi chọn cách dùng tiền",
  M9L1: "Nhận diện những chiếc bẫy quen mặt", M9L2: "Thêm một bước xác minh", M9L3: "Xây nhiều lớp bảo vệ tài khoản", M9L4: "Có điều bất thường: xử lý theo thứ tự", M9L5: "Người quen giới thiệu, vẫn cần kiểm tra",
  M10L1: "Tiền chung, tiền riêng, cùng thống nhất", M10L2: "Một cuộc hẹn mỗi tháng để nói về tiền", M10L3: "Nói chuyện tiền trước khi về chung nhà", M10L4: "Dạy con hiểu tiền từ trải nghiệm nhỏ", M10L5: "Cho người thân vay, nói rõ từ đầu", M10L6: "Chăm lo cha mẹ trong khả năng của mình",
}

export const curriculum: CourseModule[] = source.modules.map((module) => ({
  id: module.id, hours: module.hours, ...MODULE_STORIES[module.id],
  lessons: module.lessons.map((lesson) => ({ ...lesson, originalTitle: lesson.title, title: LESSON_TITLES[lesson.id] ?? lesson.title })),
}))
export const lessonCount = curriculum.reduce((sum, module) => sum + module.lessons.length, 0)
export const stages = ["Tất cả", "Làm chủ mỗi ngày", "Bảo vệ nền tảng", "Đi đường dài"]
