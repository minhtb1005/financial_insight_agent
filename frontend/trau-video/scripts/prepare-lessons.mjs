// Editorial corrections for the existing scene scripts; run before TTS/rendering.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.join(root, 'public/lessons');
const course = JSON.parse(fs.readFileSync(path.join(root, '../src/content/learning-tracks.json'), 'utf8'));
const patches = {};
const set = (id, scene, text, lines) => ((patches[id] ??= {})[scene] = {text, lines});
const taxSource = 'https://chinhsachonline.chinhphu.vn/thoi-diem-ap-dung-bieu-thue-thu-nhap-ca-nhan-moi-84963.htm';
const insuranceSource = 'https://xaydungchinhsach.chinhphu.vn/toan-van-luat-kinh-doanh-bao-hiem-119240130070753445.htm';
const safetySource = 'https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2025/10/22/Thu-doan-gia-mao-the-Ngan-hang';

set('M1L6','S8','Khoản thiết yếu trong ví dụ đã vượt ba triệu gia đình hỗ trợ. Vì vậy không thể coi toàn bộ tiền làm thêm là tiền linh hoạt. Hãy cộng các khoản bắt buộc, khoản theo kỳ, rồi mới xác định phần còn lại để chi hoặc để dành.',['Tổng thu − khoản bắt buộc − khoản theo kỳ','Phần còn lại mới linh hoạt']);
set('M2L1','S4','Một mốc tham khảo là ba đến sáu tháng chi phí thiết yếu, không phải chuẩn bắt buộc. Với bảy triệu mỗi tháng, ba tháng là hai mươi mốt triệu, sáu tháng là bốn mươi hai triệu. Chọn mức phù hợp với thu nhập, người phụ thuộc và khả năng tiếp cận hỗ trợ.',['Mốc tham khảo, không bắt buộc','7tr × 3 = 21tr','7tr × 6 = 42tr']);
set('M2L5','S5','Giả sử thu nhập này đã trừ thuế và chi phí công việc. Sáu tháng thu bảy mươi triệu, chi năm mươi bốn triệu, chênh lệch là mười sáu triệu. Nhưng tháng đầu chỉ thu tám triệu và cần chi chín triệu, nên phải có ít nhất một triệu đệm ban đầu. Tổng cuối kỳ dương chưa bảo đảm từng tháng đủ tiền.',['70tr − 54tr = 16tr','Tháng đầu thiếu 1tr','Cần đệm ban đầu']);
set('M3L1','S2','Nợ tốt và nợ xấu trong cách nói về mục đích vay chỉ là nhãn tham khảo. Nợ xấu trong quy định ngân hàng lại là khái niệm phân loại riêng. Đừng dùng hai nghĩa này thay cho nhau. Một khoản vay học nghề vẫn có thể quá sức.',['Mục đích vay ≠ phân loại nợ pháp lý']);
set('M3L1','S8','Khoản vay có mục đích tốt vẫn có thể vượt khả năng trả. Hãy liệt kê dư nợ, lãi, phí và nghĩa vụ trả mỗi tháng. Sau đó kiểm tra phần tiền còn lại có đủ sinh hoạt và dự phòng không.',['Mục đích · Chi phí · Khả năng trả']);
set('M3L2','S7','Quả cầu tuyết ưu tiên cảm giác hoàn thành sớm. Tuyết lở ưu tiên lãi suất cao. Muốn so tổng lãi, còn cần mức trả tối thiểu, ngân sách trả nợ, lịch tính lãi và các khoản phí. Chưa đủ dữ kiện thì không thể đưa một con số tổng lãi đáng tin.',['So tổng lãi cần đủ dữ kiện','Ngân sách · Tối thiểu · Lãi · Phí']);
set('M3L3','S6','Một phần trăm mỗi tháng nhân mười hai là mười hai phần trăm một năm theo cách quy đổi danh nghĩa. Nếu lãi nhập gốc mỗi tháng thì lãi suất hiệu dụng khoảng mười hai phẩy sáu tám phần trăm. So sánh cả cách tính, kỳ trả và phí.',['Danh nghĩa: 1% × 12 = 12%','Nhập gốc tháng: 1,01¹² − 1 ≈ 12,68%']);
for (const scene of ['S2','S8']) set('M3L4',scene,'Miễn lãi phụ thuộc loại giao dịch và điều kiện của hợp đồng. Trả đủ đúng hạn có thể đáp ứng điều kiện cho giao dịch mua hàng; rút tiền mặt hoặc khoản khác có thể có cách tính riêng. Trả đủ tối thiểu đúng hạn không tự động là nợ xấu, nhưng dư nợ còn lại có thể phát sinh lãi. Hãy đọc sao kê và điều khoản của thẻ.',['Miễn lãi: kiểm đúng điều kiện','Tối thiểu đúng hạn ≠ tự động nợ xấu']);
set('M3L5','S2','Thông tin tín dụng được tổng hợp tại Trung tâm Thông tin tín dụng Quốc gia Việt Nam, thường gọi là CIC. Khi kiểm tra hồ sơ, hãy dùng kênh chính thức và đối chiếu dư nợ, trạng thái khoản vay với ngân hàng.',['CIC: thông tin tín dụng','Kiểm tra qua kênh chính thức']);
set('M3L5','S3','Đừng áp công thức điểm của nước ngoài vào hồ sơ CIC. Không thể suy ra điểm tăng hay giảm từ một tỷ lệ dùng hạn mức nếu chưa có căn cứ về cách chấm điểm. Việc cần làm là theo dõi nghĩa vụ trả nợ và kiểm tra dữ liệu của mình.',['Không suy đoán công thức điểm','Theo dõi nghĩa vụ trả nợ']);
set('M3L5','S4','Ngân hàng còn xem khả năng trả nợ và điều kiện cấp tín dụng của họ. Có lịch sử vay lâu không bảo đảm được duyệt. Không nên mở thêm khoản vay chỉ để cố tạo điểm tín dụng.',['Khả năng trả nợ · Điều kiện ngân hàng']);
set('M3L5','S5','Phân loại nợ có nhiều tiêu chí. Không chỉ dựa vào việc còn dư nợ hay trả tối thiểu để kết luận nợ xấu. Nếu báo cáo có thông tin chưa đúng, hỏi tổ chức cung cấp dữ liệu và CIC về cách kiểm tra, điều chỉnh.',['Phân loại nợ: nhiều tiêu chí','Sai dữ liệu → yêu cầu kiểm tra']);
set('M3L5','S7','Lập lịch nhắc hạn, kiểm tra số tiền phải trả và dành ngân sách phù hợp. Nếu khó trả, liên hệ ngân hàng sớm để trao đổi phương án. Không có bảo đảm rằng điểm sẽ phục hồi trong sáu tháng.',['Nhắc hạn · Kiểm tra · Liên hệ sớm']);
set('M3L5','S8','Hồ sơ tín dụng cần dữ liệu đúng và nghĩa vụ được thực hiện đầy đủ. Trước khi đóng thẻ, hỏi về dư nợ, phí còn lại và xác nhận tất toán. Đừng mặc định giữ thẻ cũ luôn tốt hơn hay đóng thẻ chắc chắn làm giảm điểm.',['Dữ liệu đúng · Nghĩa vụ rõ','Đóng thẻ: xác nhận dư nợ và phí']);
set('M3L6','S5','Sau khi dùng quỹ, Lan còn mười tám triệu. Muốn trở về mục tiêu hai mươi bốn triệu, cần bù sáu triệu: ba tháng nếu để dành hai triệu mỗi tháng. Muốn trở lại số dư ban đầu ba mươi triệu thì cần sáu tháng. Giả sử không có lần rút thêm và chưa tính lãi.',['Về mục tiêu 24tr: 3 tháng','Về số dư 30tr: 6 tháng']);
set('M3L7','S7','Đừng dùng một trần lãi suất để kết luận cho mọi loại khoản vay. Giao dịch dân sự và tín dụng của tổ chức có thể chịu quy định khác nhau. Trách nhiệm hình sự còn phụ thuộc các điều kiện pháp luật. Khi gặp lãi phí bất thường hoặc đe dọa, giữ hợp đồng và chứng cứ để hỏi cơ quan có thẩm quyền.',['Kiểm đúng loại giao dịch','Giữ hợp đồng và chứng cứ']);
set('M4L2','S4','Nếu lãi ba phần trăm mà lạm phát bốn phần trăm, sức mua giảm. Phép trừ nhanh cho kết quả xấp xỉ âm một phần trăm; công thức chính xác là một phẩy không ba chia một phẩy không bốn, trừ một, khoảng âm không phẩy chín sáu phần trăm.',['Xấp xỉ: 3% − 4% = −1%','Chính xác: 1,03 / 1,04 − 1 ≈ −0,96%']);
set('M4L5','S5','Tổng phí giả định là một triệu chín trăm ba mươi hai nghìn đồng mỗi năm. Nhưng không yêu cầu bồi thường chưa có nghĩa bảo hiểm không tạo giá trị. Hãy xét nhu cầu bảo vệ và điều kiện hủy trước khi coi toàn bộ số này là tiền có thể tiết kiệm.',['600k + 132k + 1,2tr = 1,932tr','Chưa dùng ≠ không cần bảo vệ']);
set('M5L2','S3','Có ai phụ thuộc thu nhập của mình không? Quyền lợi mới có bổ sung cho hợp đồng đang có không? Người độc thân vẫn có thể cần bảo hiểm sức khỏe. Hai hợp đồng có quyền lợi tương tự cũng không tự động vô ích: phải xem cách chi trả và giới hạn.',['Người phụ thuộc: một yếu tố','Đối chiếu cách chi trả và giới hạn']);
set('M5L3','S4','Loại trừ và thời gian chờ là hai điều khác nhau. Hết thời gian chờ không tự xóa loại trừ bệnh có sẵn. Hãy khai báo trung thực, đọc điều kiện của từng quyền lợi và yêu cầu giải thích bằng văn bản.',['Hết thời gian chờ ≠ hết loại trừ']);
set('M5L3','S5','Điều ba mươi lăm Luật Kinh doanh bảo hiểm quy định: với hợp đồng thời hạn trên một năm, có hai mươi mốt ngày cân nhắc từ ngày nhận hợp đồng. Khi từ chối tiếp tục, phí hoàn lại trừ chi phí hợp lý nếu có theo thỏa thuận. Không áp thời hạn này cho mọi hợp đồng.',['Hợp đồng trên 1 năm','21 ngày từ khi nhận hợp đồng','Hoàn phí trừ chi phí hợp lý theo thỏa thuận']);
set('M5L3','S7','Năm phút đầu dùng để đánh dấu quyền lợi, loại trừ và thời gian chờ. Đây chỉ là bước rà soát, không thay việc đọc toàn bộ hợp đồng. Ghi lại câu hỏi rồi xác nhận bằng văn bản trước khi quyết định.',['5 phút: bước rà soát đầu','Đọc toàn bộ hợp đồng']);
set('M6L1','S1','Lan thấy lương trên hợp đồng khác số tiền vào tài khoản. Có thể có bảo hiểm, thuế hoặc khoản khấu trừ khác. Hãy đối chiếu từng dòng thay vì mặc định mọi chênh lệch đều đúng.',['Đối chiếu từng khoản khấu trừ']);
set('M6L1','S4','Cần xác định kỳ tính thuế và tình trạng cư trú trước khi chọn cách tính. Đừng suy ra tình trạng cư trú chỉ từ quốc tịch. Khi chưa rõ, đối chiếu hồ sơ với cơ quan thuế hoặc người có chuyên môn.',['Kỳ tính thuế · Tình trạng cư trú']);
set('M6L1','S5','Với lương cá nhân cư trú kỳ hai nghìn không trăm hai mươi sáu, biểu tháng có năm bậc: đến mười triệu là năm phần trăm; phần trên mười đến ba mươi là mười; trên ba mươi đến sáu mươi là hai mươi; trên sáu mươi đến một trăm là ba mươi; phần trên một trăm là ba mươi lăm phần trăm. Chỉ áp cho từng phần thu nhập tính thuế.',['2026 · Thu nhập tính thuế/tháng','≤10tr: 5% · >10–30tr: 10%','>30–60tr: 20% · >60–100tr: 30%','>100tr: 35%']);
set('M6L1','S6','Minh họa riêng cách áp bậc: giả sử đã xác định thu nhập tính thuế là mười hai triệu một tháng, sau mọi giảm trừ hợp lệ. Mười triệu đầu nhân năm phần trăm là năm trăm nghìn. Hai triệu tiếp theo nhân mười phần trăm là hai trăm nghìn. Tổng thuế là bảy trăm nghìn. Đây không phải mức lương gộp.',['Thu nhập tính thuế: 12tr','10tr × 5% + 2tr × 10% = 700.000đ','Đã trừ các khoản hợp lệ']);
set('M6L2','S2','Giảm trừ gia cảnh gồm phần bản thân và người phụ thuộc đủ điều kiện. Mức áp dụng phải đối chiếu đúng kỳ tính thuế. Không tự dùng một mức cũ cho mọi năm.',['Giảm trừ gia cảnh: kiểm đúng kỳ']);
set('M6L2','S3','Điều kiện người phụ thuộc khác nhau theo nhóm quan hệ, tuổi, khả năng lao động và thu nhập. Không phải cứ không đi làm là đủ điều kiện. Cần đăng ký, hồ sơ phù hợp và tránh tính trùng; thời điểm tính giảm trừ phải kiểm theo trường hợp.',['Quan hệ · Tuổi · Thu nhập · Hồ sơ','Không đi làm ≠ tự động đủ điều kiện']);
set('M6L2','S5','Kiểm tra khoản bảo hiểm được trừ theo quy định, cơ sở đóng và phần thực do người lao động đóng. Không trừ thêm phần doanh nghiệp đóng, cũng không tự coi mọi phí bảo hiểm tự nguyện đều được giảm trừ.',['Kiểm khoản thực được trừ','Không trừ phần doanh nghiệp đóng']);
set('M6L2','S6','Khoản miễn thuế cần đúng loại thu nhập và đúng điều kiện. Hãy lưu chứng từ và kiểm tra văn bản của kỳ áp dụng. Tên gọi phụ cấp trên bảng lương chưa đủ để kết luận miễn thuế.',['Miễn thuế: đúng loại và điều kiện']);
set('M6L3','S4','Phân biệt được ủy quyền, phải tự quyết toán và không phải quyết toán. Có hai nơi trả thu nhập không tự động buộc tự quyết toán trong mọi trường hợp. Hãy liệt kê nguồn thu, hợp đồng, số đã khấu trừ và hỏi theo đúng năm.',['Ủy quyền · Tự quyết toán · Không phải quyết toán']);
set('M6L3','S6','Kiểm tra hạn nộp áp dụng cho cá nhân và hồ sơ của mình. Nếu phát hiện sai hoặc thiếu, tìm hướng dẫn khai bổ sung qua cơ quan thuế. Đừng đoán mức phạt chỉ từ việc có sai sót.',['Kiểm hạn nộp và hướng dẫn khai bổ sung']);
set('M7L2','S4','Mua trước trả sau vẫn tạo nghĩa vụ thanh toán. Cần đọc lịch trả, lãi, phí và điều kiện trễ hạn của từng dịch vụ trước khi mua. Không có lãi quảng cáo chưa chắc không có chi phí.',['Trả sau = nghĩa vụ thanh toán','Đọc lịch trả · Lãi · Phí']);
set('M7L4','S3','Cẩn thận khi bị yêu cầu chuyển phí để mở khóa giải ngân, cài ứng dụng lạ hoặc cấp quyền đọc danh bạ không cần thiết. Tự xác minh đơn vị cung cấp và điều kiện bằng kênh chính thức trước khi tiếp tục.',['Phí mở khóa · App lạ · Quyền không cần thiết']);
set('M7L4','S6','Chỉ một dấu hiệu nghiêm trọng cũng đủ để dừng và kiểm tra; không cần chờ đủ cả ba. Giấy tờ trông thật chưa bảo đảm an toàn. Tự liên hệ qua kênh chính thức và hỏi người tin cậy trước khi chuyển tiền.',['Một dấu hiệu nghiêm trọng → dừng kiểm tra']);
set('M8L3','S3','Sinh con cần dự trù trước sinh, khi sinh và chăm sóc sau sinh. Khoản hỗ trợ thai sản nếu có phải kiểm điều kiện và mức hưởng theo hồ sơ. Chỉ đưa khoản đã xác nhận vào nguồn tiền chắc chắn.',['Trước sinh · Khi sinh · Sau sinh','Quyền lợi: kiểm hồ sơ trước']);
set('M8L10','S7','Bạn có thể bắt đầu học khái niệm bất cứ lúc nào. Trước khi dùng tiền thật, hãy xem quỹ dự phòng, nợ lãi cao, dòng tiền, thời hạn mục tiêu và khả năng chịu mất vốn. Hiểu biết và quyết định bỏ tiền là hai bước khác nhau.',['Có thể học bất cứ lúc nào','Dùng tiền thật: kiểm nền tảng và rủi ro']);
set('M8L10','S8','Học giúp bạn nhận ra câu hỏi cần đặt ra. Dùng tiền thật đòi hỏi đánh giá thêm hoàn cảnh và rủi ro. Bạn có thể mở lộ trình kiến thức thị trường để thực hành đọc dữ liệu và kiểm chứng nguồn.',['Học khái niệm → kiểm chứng dữ liệu']);
set('M9L3','S2','Không chia sẻ mã xác thực, mã PIN, mật khẩu hay mã bảo mật thẻ cho bất kỳ ai, kể cả khi chính bạn gọi tổng đài. Chỉ nhập mã trong ứng dụng hoặc trang chính thức cho giao dịch bạn chủ động và đã kiểm tra.',['Không đọc/gửi OTP, PIN, mật khẩu, CVV','Kể cả khi bạn gọi tổng đài']);
set('M9L3','S3','Đăng ký sinh trắc học theo hướng dẫn trong ứng dụng chính thức của ngân hàng. Yêu cầu xác thực phụ thuộc loại giao dịch và quy định hiện hành. Sinh trắc học giúp tăng bảo vệ nhưng không bảo đảm tránh mọi gian lận.',['Sinh trắc học trên kênh chính thức','Không bảo đảm an toàn tuyệt đối']);
set('M9L3','S4','Đặt hạn mức phù hợp với nhu cầu và chỉ tăng khi cần. Hạn mức có thể giảm thiệt hại trong một số tình huống, nhưng không thay việc bảo vệ thiết bị và xác minh người nhận.',['Hạn mức phù hợp · Xác minh người nhận']);
set('M9L5','S3','Tự gọi số đã lưu hoặc xác minh trực tiếp qua kênh độc lập. Tên tài khoản nhận khớp cũng chưa đủ chứng minh yêu cầu thật. Câu hỏi riêng có thể bị lộ, nên đừng chỉ dựa vào một câu trả lời để chuyển tiền.',['Xác minh qua kênh độc lập','Tên khớp chưa đủ']);
set('M10L5','S9','Tính phần tiền sau khi giữ đủ dự phòng, trừ các nghĩa vụ và khoản chi sắp tới. Phần dư chỉ là giới hạn để cân nhắc, không phải khuyến nghị đem cho vay hết. Chỉ quyết định sau khi xét khả năng chấp nhận mất tiền và thỏa thuận trả nợ.',['Dư sau dự phòng và nghĩa vụ','Không mặc định cho vay hết phần dư']);

// Independent arithmetic checks for examples retained in the scripts.
assert.equal(25000*5*52+30000*3*52,11180000);
assert.equal(2*300000+11000*12+1200000,1932000);
assert.equal(10000000*.05+2000000*.10,700000);
const pmt=(p,r,n)=>p*r/(1-(1+r)**-n);
const payment=pmt(1.4e9,.09/12,240);
assert(Math.abs(payment-12596163)<2);
let balance=1.4e9, interest=0;
for(let i=0;i<60;i++){const charge=balance*.09/12;interest+=charge;balance-=payment-charge;}
assert(Math.abs((interest+1e8)/1e6-698)<1);
assert(Math.abs((.6e9+1.4e9-balance)/1e6-758)<1);
set('M8L8','S3','Ví dụ giả định: nhà hai tỷ, trả trước sáu trăm triệu, vay một tỷ bốn trong hai mươi năm. Lãi cố định chín phần trăm một năm, chia mười hai để tính lãi tháng trên dư nợ giảm dần; trả đều cuối tháng. Chưa tính phí vay hay bảo hiểm. Thu nhập hộ gia đình bốn mươi triệu mỗi tháng.',['Vay 1,4 tỷ · 240 tháng · 9%/năm','Trả đều cuối tháng · Lãi cố định','Chưa tính phí vay, bảo hiểm']);
set('M8L8','S7','Giả sử bảo trì và các phí sở hữu là hai mươi triệu mỗi năm. Năm năm đầu, tổng lãi vay và phần này khoảng sáu trăm chín mươi tám triệu. Thuê mười hai triệu mỗi tháng trong sáu mươi tháng là bảy trăm hai mươi triệu nếu giá thuê không đổi. Chưa tính chi phí mua bán, cơ hội và biến động giá nhà.',['5 năm, giả định giá thuê không đổi','Lãi + bảo trì ≈ 698tr · Thuê = 720tr','Chưa gồm chi phí mua bán, cơ hội']);

const resolved = new Set(['M2L1','M3L1','M3L3','M3L4','M3L5','M4L1','M4L2','M4L3','M4L4','M5L1','M5L2','M5L3','M6L1','M6L2','M6L3','M7L1','M7L2','M7L4','M8L2','M8L3']);
const existing = new Map();
for(const filename of fs.readdirSync(dir).filter(f=>f.endsWith('_scenes.json'))){
  const lesson=JSON.parse(fs.readFileSync(path.join(dir,filename),'utf8'));
  for(const scene of lesson.scenes){
    const patch=patches[lesson.lesson_id]?.[scene.id];
    if(patch){scene.vo.text=patch.text;scene.on_screen_text=[{text:patch.lines.join(' · '),split_hint:patch.lines,position:'auto'}];}
    scene.vo.word_count=scene.vo.text.split(/\s+/).length;
    scene.duration_sec_estimate=Math.round((scene.vo.word_count/2.8+.6)*10)/10;
    assert(!/\[\[/.test(JSON.stringify([scene.vo,scene.on_screen_text])),`${lesson.lesson_id}/${scene.id}: unresolved placeholder`);
  }
  for(const v of lesson.verification||[]){
    if(v.type==='placeholder'&&v.status==='open'){
      assert(resolved.has(lesson.lesson_id),`Unreviewed source request: ${lesson.lesson_id}`);
      v.status='resolved';
      v.resolution='Đã thay nội dung phụ thuộc dữ liệu chưa có bằng khái niệm/giả định rõ ràng; không đưa số hiện hành chưa xác minh hoặc trích nghiên cứu chưa có nguồn vào lời đọc.';
    }
  }
  lesson.production_revision='2026-10-22';
  lesson.status='draft_ready_for_review';
  lesson.sources=lesson.sources||[];
  const addSource=(title,url)=>{if(!lesson.sources.some(s=>s.url===url))lesson.sources.push({title,url});};
  if(lesson.lesson_id.startsWith('M6'))addSource('Cổng TTĐT Chính phủ — Thuế lương kỳ 2026',taxSource);
  if(lesson.lesson_id.startsWith('M5'))addSource('Luật Kinh doanh bảo hiểm — Điều 35',insuranceSource);
  if(lesson.lesson_id.startsWith('M9')||['M4L4','M7L4'].includes(lesson.lesson_id))addSource('Vietcombank — Cảnh báo giả mạo',safetySource);
  existing.set(lesson.lesson_id,lesson);
  fs.writeFileSync(path.join(dir,filename),JSON.stringify(lesson,null,2)+'\n');
}

// Short market-literacy videos use the existing reviewed reading and exercise.
// Numerical examples remain explicitly hypothetical; no company data is fabricated.
const marketExamples={
  MK1L1:['Ví dụ giả định: bạn mua một cổ phiếu giá một trăm, sau đó bán giá chín mươi mà chưa nhận cổ tức. Bạn đã lỗ mười, chưa tính thuế phí. Quyền sở hữu không bảo đảm giữ nguyên vốn.','Ví dụ giả định: 100 → 90','Chưa có cổ tức, thuế và phí'],
  MK1L2:['Thử tra cứu một mã rồi ghi tên pháp nhân, ngành, kỳ dữ liệu và nguồn. Nếu chưa có báo cáo thì để trống các chỉ tiêu. Tên thương hiệu quen thuộc không thay thế bằng chứng về hoạt động kinh doanh.','Pháp nhân · Kỳ dữ liệu · Nguồn'],
  MK2L1:['Trước khi đọc đường giá, kiểm tra trục ngang là ngày nào và trục dọc tính theo đồng hay nghìn đồng. Dữ liệu đã điều chỉnh và dữ liệu chưa điều chỉnh có thể cho hình khác nhau khi chia tách hoặc trả cổ tức.','Ngày · Đơn vị · Điều chỉnh giá'],
  MK2L2:['Một ví dụ giả định: giá từ một trăm xuống tám mươi rồi lên chín mươi. Đo từ đáy, giá tăng mười hai phẩy năm phần trăm. Đo cả đoạn, giá vẫn giảm mười phần trăm. Hai nhận xét cùng đúng vì điểm bắt đầu khác nhau.','Giả định: 100 → 80 → 90','80 → 90: +12,5% · 100 → 90: −10%'],
  MK3L1:['Một trăm tăng hai mươi phần trăm thành một trăm hai mươi. Sau đó giảm hai mươi phần trăm của một trăm hai mươi, tức giảm hai mươi bốn, còn chín mươi sáu. Muốn từ chín mươi sáu về một trăm, cần tăng bốn chia chín mươi sáu, khoảng bốn phẩy một bảy phần trăm.','Giả định: 100 → 120 → 96','Toàn kỳ: −4% · Hồi về 100: +4,17%'],
  MK3L2:['Trong chuỗi một trăm, tám mươi, chín mươi, đáy thấp hơn đỉnh hai mươi phần trăm. Cuối kỳ lại chỉ thấp hơn điểm đầu mười phần trăm. Biểu đồ chưa nói hết rủi ro thanh khoản, chất lượng thông tin hay khả năng doanh nghiệp mất vốn.','Giả định: 100 → 80 → 90','Giảm sâu nhất: 20% · Cuối kỳ: −10%'],
  MK4L1:['Giả sử doanh nghiệp bán chịu một trăm triệu và ghi nhận chi phí bảy mươi triệu đã trả bằng tiền. Bỏ qua thuế và khoản khác, lợi nhuận là ba mươi triệu. Khách chưa trả tiền nên dòng tiền từ các giao dịch này âm bảy mươi triệu.','Doanh thu 100tr − chi phí 70tr = lãi 30tr','Tiền thu 0 − tiền chi 70tr = −70tr'],
  MK4L2:['Khi so hai tỷ số, hãy kiểm cùng kỳ, cùng cách tính và đơn vị. Lợi nhuận chỉ phát sinh một lần có thể làm P trên E trông thấp. Vốn chủ sở hữu nhỏ có thể làm R O E cao. Một tỷ số riêng lẻ chưa đủ để kết luận doanh nghiệp tốt hay giá rẻ.','Cùng kỳ · Cùng định nghĩa · Cùng đơn vị'],
  MK5L1:['Câu giá tăng năm phần trăm tuần qua là phát biểu có thể kiểm tra, chưa phải dữ kiện được xác minh. Câu doanh nghiệp sẽ dẫn đầu là nhận định. Cam kết lời ba phần trăm mỗi tháng là lời chào cần kiểm chứng pháp nhân, hợp đồng và rủi ro, không phải lợi nhuận chắc chắn.','Có thể kiểm chứng ≠ đã xác minh','Nhận định · Quảng cáo · Bằng chứng'],
  MK5L2:['Tạo mẫu với các ô: câu hỏi, dữ kiện, nguồn và ngày, giả định, giới hạn, bước kiểm tra tiếp. Chưa có tài liệu thì ghi chưa biết. Không tự điền số trang báo cáo, ngày công bố hay số lợi nhuận để làm mẫu trông đầy đủ.','Câu hỏi · Dữ kiện và nguồn · Giả định','Giới hạn · Bước kiểm tra tiếp'],
};
for(const track of course.tracks)for(const module of track.modules)for(const item of module.lessons){
  if(existing.has(item.id))continue;
  const ex=marketExamples[item.id];assert(ex,`Missing script: ${item.id}`);
  const rows=[
    [`Cùng Trâu Tí tìm hiểu: ${item.title} Hôm nay mình bắt đầu từ câu hỏi: ${item.question}`,[item.title]],
    [item.reading,[...item.topics]],
    [ex[0],ex.slice(1)],
    ['Hãy ghi rõ phần nào là ví dụ giả định và phần nào có nguồn thật. Kiểm tra kỳ, đơn vị và định nghĩa trước khi so sánh. Khi dữ liệu còn thiếu, đánh dấu chưa biết để tìm tiếp.',['Kỳ · Đơn vị · Định nghĩa','Thiếu dữ liệu: ghi chưa biết']],
    [`Bài thực hành của bạn: ${item.activity}` ,['Thử ngay với bài thực hành bên dưới']],
    ['Sau khi làm xong, ghi lại một điều bạn hiểu rõ hơn và một câu hỏi cần kiểm chứng. Bạn có thể hỏi trợ giảng ngay trong bài học. Nội dung này giúp đọc hiểu dữ liệu, không đưa khuyến nghị mua bán.',['Ghi lại điều học được','Kiểm chứng trước khi kết luận']],
  ];
  const lesson={schema_version:'1.0',lesson_id:item.id,module_id:module.id,module_title:module.title,title:item.title,production_revision:'2026-10-22',status:'draft_ready_for_review',source_script:'frontend/src/content/learning-tracks.json',sources:item.sources||[],format:{width:1080,height:1920,fps:30,aspect_ratio:'9:16'},scenes:rows.map(([text,lines],i)=>({id:`S${i+1}`,order:i+1,duration_sec_estimate:Math.round((text.split(/\s+/).length/2.8+.6)*10)/10,visual:{description:lines.join(' · '),mascot_pose:i===0?'wave':'point',characters:['Trâu Tí']},vo:{text,word_count:text.split(/\s+/).length},on_screen_text:[{text:lines.join(' · '),split_hint:lines}],transition_out:'cut'})),end_card:{duration_sec:3,on_screen_text:['Nội dung giáo dục. Ví dụ giả định không phải dữ liệu doanh nghiệp hay khuyến nghị mua bán.']},verification:[]};
  fs.writeFileSync(path.join(dir,`${item.id}_scenes.json`),JSON.stringify(lesson,null,2)+'\n');
}
console.log('Prepared 66 lesson scripts; arithmetic checks passed.');
