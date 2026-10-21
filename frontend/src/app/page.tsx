import Link from "next/link"
import { ArrowDown, ArrowRight, ArrowUpRight, BookOpen, Check, CheckCheck, Compass, MessageCircle, Play, ShieldCheck, Sparkles, Wallet } from "lucide-react"
import { TrauMascot } from "@/components/brand/TrauMascot"
import { curriculum, lessonCount } from "@/lib/curriculum"

export default function HomePage() {
  return (
    <div className="landing-page">
      <section className="hero-section page-shell">
        <div className="hero-copy">
          <p className="eyebrow"><span className="status-dot" /> TÀI CHÍNH CÁ NHÂN, GẦN GŨI HƠN</p>
          <h1>Hiểu tiền.<br />Chủ động<br /><span className="serif-accent">cuộc sống.</span></h1>
          <p className="hero-description">Từ khoản chi nhỏ hôm nay đến kế hoạch lớn ngày mai. Cùng Trâu Tí học cách quản lý tiền — từng tình huống thật, từng bước vừa sức.</p>
          <div className="hero-actions"><Link className="action-primary" href="/demo">Trải nghiệm 3 phút <ArrowUpRight size={18} /></Link><Link className="action-text" href="/learn"><BookOpen size={17} /> Khám phá lộ trình</Link></div>
          <p className="hero-footnote"><CheckCheck size={15} /> Demo tương tác · Không cần tài khoản</p>
        </div>
        <div className="hero-art" aria-label="Trâu Tí đồng hành cùng kế hoạch tài chính của bạn">
          <div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" />
          <span className="art-star star-one" aria-hidden="true">✳</span><span className="art-star star-two" aria-hidden="true">✳</span>
          <div className="mascot-intro"><span>Chào bạn, mình là</span><strong>Trâu Tí!</strong><svg viewBox="0 0 70 45" aria-hidden="true"><path d="M2 2q50-1 48 32m-10-9 11 11 10-13" fill="none" stroke="currentColor" strokeWidth="2" /></svg></div>
          <TrauMascot className="hero-mascot" />
          <div className="floating-note note-goal"><span className="note-icon"><Wallet size={19} /></span><div><span>Mục tiêu đầu tiên</span><strong>Làm chủ ngân sách</strong></div><span className="note-check"><Check size={14} /></span></div>
          <div className="floating-note note-progress"><span className="small-label">MỖI BƯỚC NHỎ ĐỀU CÓ Ý NGHĨA</span><div className="tiny-bars" aria-hidden="true">{[25, 39, 34, 57, 49, 72, 87].map((h, i) => <span key={i} style={{ height: `${h}%` }} />)}</div><span>Hiểu hơn. Vững vàng hơn.</span></div>
          <span className="art-caption">Bạn đồng hành trên hành trình hiểu tiền.</span>
        </div>
      </section>
      <section className="proof-strip page-shell" aria-label="Nội dung học tập"><div><strong>10</strong><span>chủ đề gần cuộc sống</span></div><div><strong>{lessonCount}</strong><span>bài học có nhiệm vụ</span></div><div><strong>01</strong><span>người bạn đồng hành</span></div><a href="#cach-hoc">Tìm hiểu cách học <ArrowDown size={17} /></a></section>
      <section id="cach-hoc" className="section-space page-shell">
        <div className="section-heading"><div><p className="eyebrow">BẮT ĐẦU TỪ CHUYỆN CỦA BẠN</p><h2>Tiền bạc là chuyện mỗi ngày.<br /><span className="text-soft">Hiểu nó cũng có thể như vậy.</span></h2></div><p>Không cần giỏi những thuật ngữ phức tạp. Bắt đầu bằng một câu hỏi bạn đang thực sự quan tâm.</p></div>
        <div className="situation-grid">{[
          { n: "01", icon: Wallet, title: "Lương vừa về, đã thấy hết?", text: "Nhìn rõ tiền đi đâu, phân biệt điều cần với điều muốn, rồi thử một ngân sách vừa với mình.", module: "M1", label: "Hiểu dòng tiền" },
          { n: "02", icon: ShieldCheck, title: "Nếu có một khoản chi bất ngờ?", text: "Tập xây một khoảng đệm tài chính và hiểu những lựa chọn bảo vệ điều quan trọng.", module: "M2", label: "Xây sự an tâm" },
          { n: "03", icon: Compass, title: "Có dự định, nhưng chưa có kế hoạch?", text: "Chia một mục tiêu lớn thành những bước cụ thể, với thời gian và nguồn lực của bạn.", module: "M8", label: "Đi đường dài" },
        ].map((item) => <Link href={`/learn?module=${item.module}`} className="situation-card" key={item.n}><div className="card-topline"><item.icon size={24} strokeWidth={1.5} /><span>{item.n}</span></div><h3>{item.title}</h3><p>{item.text}</p><span className="card-link">{item.label} <ArrowUpRight size={18} /></span></Link>)}</div>
      </section>
      <section className="method-section"><div className="page-shell method-grid"><div className="method-visual"><div className="sample-message"><span className="small-label">MỘT CÂU HỎI RẤT ĐỜI THƯỜNG</span><p>“Mình muốn để dành tiền,<br />nhưng nên bắt đầu từ đâu?”</p></div><TrauMascot mood="thinking" /><span className="handwritten">Mình cùng tìm hiểu nhé.</span></div><div className="method-copy"><p className="eyebrow">HỌC ĐỂ LÀM ĐƯỢC</p><h2>Từ “mình chưa biết”<br />đến <span className="serif-accent">“mình làm được”.</span></h2><div className="method-step"><span>1</span><div><h3>Hiểu qua một tình huống</h3><p>Mỗi bài bắt đầu từ một câu chuyện quen thuộc, với các ý chính rõ ràng.</p></div></div><div className="method-step"><span>2</span><div><h3>Thử bằng chính đôi tay</h3><p>Lập một bảng chi tiêu, kiểm tra một khoản phí, viết một kế hoạch nhỏ.</p></div></div><div className="method-step"><span>3</span><div><h3>Hỏi tiếp, hiểu sâu hơn</h3><p>Mang câu hỏi sang trợ giảng AI, đọc giải thích và kiểm tra nguồn được cung cấp.</p></div></div><Link href="/demo" className="action-text">Thử một tình huống ngay <ArrowRight size={18} /></Link></div></div></section>
      <section id="lo-trinh" className="section-space page-shell">
        <div className="section-heading"><div><p className="eyebrow">LỘ TRÌNH CỦA BẠN</p><h2>Từng chặng nhỏ.<br /><span className="serif-accent">Một nền tảng vững vàng.</span></h2></div><div><p>10 chủ đề, 56 bài học. Bắt đầu từ điều bạn cần, rồi mở rộng khi sẵn sàng.</p><Link href="/learn" className="action-text">Xem toàn bộ lộ trình <ArrowUpRight size={17} /></Link></div></div>
        <div className="curriculum-preview">{curriculum.slice(0, 3).map((module, index) => <Link href={`/learn?module=${module.id}`} key={module.id} className={`course-preview course-tone-${index}`}><span className="small-label">CHẶNG {String(index + 1).padStart(2, "0")} <span>· {module.lessons.length} bài học</span></span><div className="course-symbol" aria-hidden="true">{index === 0 ? <Wallet size={44} strokeWidth={1.2} /> : index === 1 ? <ShieldCheck size={44} strokeWidth={1.2} /> : <Compass size={44} strokeWidth={1.2} />}</div><h3>{module.title}</h3><p>{module.description}</p><div className="course-bottom"><span>{module.outcome}</span><ArrowUpRight size={20} /></div></Link>)}</div>
      </section>
      <section id="tam-nhin" className="pitch-section page-shell"><div className="pitch-intro"><p className="eyebrow">GIÁO DỤC TÀI CHÍNH CÓ NGỮ CẢNH</p><h2>Kiến thức chỉ có ý nghĩa<br />khi bước vào <span className="serif-accent">cuộc sống.</span></h2><p>Financial Insight kết nối lộ trình học, thực hành và trợ giảng AI trong một trải nghiệm tiếng Việt — dành cho sinh viên, người mới đi làm và gia đình trẻ.</p><Link className="action-primary" href="/demo"><Play size={16} /> Khám phá sản phẩm</Link></div><div className="pitch-points">{[{ icon: BookOpen, title: "Nội dung có lộ trình", text: "Từ ngân sách, tiết kiệm và nợ đến thuế, an toàn số và tiền bạc trong gia đình." }, { icon: Sparkles, title: "AI đồng hành theo câu hỏi", text: "Tiếp tục tìm hiểu điều chưa rõ, kết hợp công cụ tính toán và tra cứu nguồn trong cuộc hội thoại." }, { icon: CheckCheck, title: "Học qua việc mình làm được", text: "Mỗi bài có một nhiệm vụ cụ thể. Người học ghi lại kết quả và tự theo dõi tiến độ." }].map((item) => <div key={item.title}><item.icon size={22} strokeWidth={1.5} /><div><h3>{item.title}</h3><p>{item.text}</p></div></div>)}<p className="pitch-note">Hướng phát triển: thử nghiệm với nhóm học nhỏ, đo mức hoàn thành và chất lượng bài thực hành trước khi mở rộng.</p></div></section>
      <section className="closing-section page-shell"><div><p className="eyebrow">MỘT BƯỚC NHỎ, NGAY HÔM NAY</p><h2>Chuyện tiền bạc,<br />mình cùng học nhé?</h2><p>Trâu Tí đã sẵn sàng. Còn bạn?</p><Link href="/demo" className="action-primary">Bắt đầu trải nghiệm <ArrowUpRight size={18} /></Link><Link href="/chat" className="action-text"><MessageCircle size={17} /> Gặp trợ giảng AI</Link></div><TrauMascot mood="celebrate" /></section>
    </div>
  )
}
