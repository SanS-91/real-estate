const assert=require('node:assert/strict');
const fs=require('node:fs');
const editorial=require('../assets/js/home-editorial.js');
const norm=editorial.normalize;
assert.equal(norm('BẤT ĐỘNG SẢN – Đồng Nai'),'bat dong san dong nai');
const make=(category,title,date='2026-11-01',source='rss')=>({
  id:category+':'+norm(title),category,title,display_title:title,date,
  content_type:'publisher-rss',source_id:source,attention_score:10
});
const noise=[
make('market','3 mẹo nâng cấp nội thất giá rẻ trong sáng trong ít tốn kém'),
make('market','Chủ đầu tư sân bay Long Thành giảm gần 1.400 nhân sự trong ba tháng'),
make('market','Chốt phương án xử lý sai phạm ở HH Linh Đàm: Ai phải di dời, ai được ở lại?'),
make('infrastructure','Đôi nam nữ bị xe ben cán tử vong trong hầm chui ở TPHCM'),
make('infrastructure','Đầu tư 110 tỷ đồng xóa 71 điểm đen trên quốc lộ 49'),
make('macro','Giá vàng hôm nay 1.11.2026: Lao dốc đẩy người mua lỗ hơn 11 triệu sau 2 tuần'),
make('macro','Giá bán vàng trong nước ở mức 139 triệu đồng')
];
assert(noise.slice(0,5).every(row=>!editorial.inspect(row).eligible));
const good=[
make('market','Dự án Izumi City mở bán giai đoạn mới tại Đồng Nai'),
make('market','Giá bán căn hộ TP HCM tăng, nguồn cung tiếp tục khan hiếm','2026-10-31'),
make('market','Thị trường bất động sản giao dịch cải thiện ở Đồng Nai','2026-10-30'),
make('legal','Bộ trưởng: Không lạm dụng thu hồi đất'),
make('legal','Thu hồi đất phải đảm bảo sinh kế cho dân, không phải chỉ bồi thường là xong','2026-10-31'),
make('legal','Đề xuất bổ sung nguyên tắc bồi thường tối thiểu khi thu hồi đất','2026-10-30'),
make('infrastructure','Cầu Cần Thơ 2 được thiết kế cho cả đường bộ và đường sắt'),
make('infrastructure','Dự án cao tốc Biên Hòa Vũng Tàu đẩy nhanh tiến độ','2026-10-31'),
make('macro','Ngân hàng Nhà nước công bố tăng trưởng tín dụng mới'),
make('macro','Lãi suất cho vay VND được điều chỉnh tại ngân hàng','2026-10-31'),
make('macro','CPI tháng 10 tăng so với cùng kỳ','2026-10-30'),
make('market','Nguồn cung nhà ở xã hội mới được mở bán','2026-10-08')
];
for(const row of good)assert(editorial.inspect(row).eligible,'Rejected '+row.title);
for(const category of ['market','legal','infrastructure','macro']){
  const rows=[...noise,...good].filter(row=>row.category===category);
  const choices=editorial.curated(rows,'2026-11-01',{max:3});
  assert(choices.length>0 && choices.length<=3);
  assert(choices.every(x=>x.eligible),'Noise leaked into '+category);
  assert(!choices.some(x=>noise.includes(x)),'Noisy story chosen for '+category);
}
const m=editorial.curated([noise[0],...good.filter(x=>x.category==='market')],'2026-11-01',{max:3});
assert(!m.some(x=>x.row.title.includes('nội thất')));
const late=editorial.curated([
  make('market','Giá bán căn hộ Đồng Nai tăng mạnh','2026-10-04'),
  make('market','Nguồn cung dự án nhà ở xã hội mới','2026-09-10')
],'2026-11-01',{max:3});
assert(late.length===1 && late[0].age>=7,'Only genuine updates <=30 days, no 90-day padding');
const gold=editorial.curated([...noise.slice(-2),
  make('macro','Phố Wall chờ Fed công bố lãi suất mới'),
  make('macro','Tăng trưởng tín dụng ngân hàng Việt Nam cải thiện')
],'2026-11-01',{max:3});
assert(gold.filter(x=>x.topic==='gold').length<=1);
assert(gold.some(x=>x.topic==='credit'));
assert.equal(editorial.label('credit','vi'),'Tín dụng');
assert.equal(editorial.label('rail','en'),'Rail');
const html=fs.readFileSync('index.html','utf8');
const home=fs.readFileSync('assets/js/home.js','utf8');
const components=fs.readFileSync('assets/js/components.js','utf8');
const css=fs.readFileSync('assets/css/main.css','utf8');
assert(html.includes('assets/js/home-editorial.js?v=HOME-EDITORIAL-1101'));
assert(html.indexOf('home-editorial.js')<html.indexOf('assets/js/home.js'));
assert(home.includes('HomeEditorial?.curated'));
assert(!home.includes('within(365)'),'No year-long noise as Home news');
assert(home.includes('Chưa có tin phù hợp trong 30 ngày'));
assert(components.includes('compact-link__topic'));
assert(components.includes('home-news-item--lead'));
assert(css.includes('body[data-page="home"] .today-grid'));
assert(css.includes('body[data-page="home"] .today-grid {'));
assert(css.includes('grid-template-columns: repeat(4, minmax(0, 1fr))'));
assert(css.includes('@media (max-width: 1120px) and (min-width: 761px)'));
assert(css.includes('body[data-page="home"] .today-card .compact-link__meta'));
console.log('PASS Home editorial: rejects screenshot noise, balanced topic selection, 30-day cap and mobile styling');
