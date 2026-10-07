(() => {
  'use strict';

  // v7.2.1 additive dynamic localization overlay.
  // It never participates in data loading, routing, filtering, search indexing,
  // chart construction or domain rendering. If it fails, v7.2.0/v7.1.1 stays usable.

  const EN_VI = new Map(Object.entries({
    // Common controls / actions
    'Search': 'Tìm kiếm',
    'Reset': 'Đặt lại',
    'Region': 'Khu vực',
    'Developer': 'Chủ đầu tư',
    'Segment': 'Phân khúc',
    'Status': 'Trạng thái',
    'Type': 'Loại',
    'Agency': 'Cơ quan',
    'Topic': 'Chủ đề',
    'Scope': 'Phạm vi',
    'Completion': 'Hoàn thành',
    'Project': 'Dự án',
    'Event': 'Sự kiện',
    'Indicator': 'Chỉ số',
    'Source': 'Nguồn',
    'Current': 'Hiện tại',
    'Previous': 'Trước đó',
    'Change': 'Thay đổi',
    'Data Period': 'Kỳ dữ liệu',
    'Published': 'Công bố',
    'Open': 'Mở',
    'Open view': 'Mở mục',
    'View all': 'Xem tất cả',
    'Open database': 'Mở cơ sở dữ liệu',
    'Open Pricing': 'Mở Giá bán',
    'Open FX': 'Mở Tỷ giá',
    'View news': 'Xem tin tức',
    'View projects': 'Xem dự án',
    'Open documents': 'Mở văn bản',
    'Indicator details': 'Chi tiết chỉ số',
    'Open historical series': 'Mở chuỗi lịch sử',
    'View related market news': 'Xem tin thị trường liên quan',
    'Close source details': 'Đóng chi tiết nguồn',
    'Open original source ↗': 'Mở nguồn gốc ↗',
    'Open official document ↗': 'Mở văn bản chính thức ↗',

    // Generic options
    'All regions': 'Tất cả khu vực',
    'All developers': 'Tất cả chủ đầu tư',
    'All segments': 'Tất cả phân khúc',
    'All statuses': 'Tất cả trạng thái',
    'All types': 'Tất cả loại',
    'All agencies': 'Tất cả cơ quan',
    'All topics': 'Tất cả chủ đề',
    'All scopes': 'Tất cả phạm vi',
    'All horizons': 'Tất cả mốc thời gian',
    'All projects': 'Tất cả dự án',
    'All events': 'Tất cả sự kiện',
    'All indicators': 'Tất cả chỉ số',

    // Shared source/provenance UI
    'Data Sources': 'Nguồn dữ liệu',
    'Source ID': 'Mã nguồn',
    'Priority': 'Ưu tiên',
    'Language': 'Ngôn ngữ',
    'Collection': 'Thu thập',
    'Update frequency': 'Tần suất cập nhật',
    'Data / source date': 'Ngày dữ liệu / nguồn',
    'Data period': 'Kỳ dữ liệu',
    'Methodology note': 'Ghi chú phương pháp',
    'Priority is a sourcing preference, not a quality score. P1 is used for primary official sources; lower-priority evidence is retained rather than discarded.': 'Mức ưu tiên thể hiện thứ tự ưu tiên nguồn, không phải điểm chất lượng. P1 dành cho nguồn chính thức gốc; các nguồn ưu tiên thấp hơn vẫn được lưu làm bằng chứng bổ sung.',
    'Source registry unavailable; continuing with source IDs only.': 'Không tải được danh mục nguồn; hệ thống tiếp tục sử dụng mã nguồn.',
    'Source Registry is unavailable. Existing records will continue to display their source IDs.': 'Không tải được Danh mục nguồn. Các bản ghi hiện có vẫn tiếp tục hiển thị mã nguồn.',
    'No live source URL in the illustrative demo registry. Real URLs will be connected in Phase 4.': 'Danh mục nguồn mô phỏng chưa có URL trực tiếp. URL thực sẽ được kết nối trong Phase 4.',
    'View ›': 'Xem ›',
    'Official': 'Chính thức',
    'Operator': 'Đơn vị vận hành',
    'Research': 'Nghiên cứu',
    'Brokerage': 'Môi giới',
    'Financial Institution': 'Tổ chức tài chính',
    'Media': 'Truyền thông',
    'Other': 'Khác',
    'Manual': 'Thủ công',
    'Html': 'HTML',
    'Api': 'API',
    'Rss': 'RSS',
    'Scraper': 'Thu thập tự động',

    // Search overlay
    'Projects': 'Dự án',
    'Developers': 'Chủ đầu tư',
    'Legal Documents': 'Văn bản pháp lý',
    'Infrastructure': 'Hạ tầng',
    'Macro Indicators': 'Chỉ số vĩ mô',
    'Events': 'Sự kiện',
    'Articles & Research': 'Bài viết & Nghiên cứu',
    'Type at least 2 characters. Vietnamese accents are optional.': 'Nhập ít nhất 2 ký tự. Có thể tìm không dấu tiếng Việt.',
    'Searching structured datasets…': 'Đang tìm trong dữ liệu có cấu trúc…',
    'Loading research index…': 'Đang tải chỉ mục nghiên cứu…',
    'Search index could not be loaded.': 'Không thể tải chỉ mục tìm kiếm.',
    'Unable to load the demo search datasets. Refresh the page and try again.': 'Không thể tải dữ liệu tìm kiếm mô phỏng. Hãy tải lại trang và thử lại.',

    // Home dynamic component labels
    'Market': 'Thị trường',
    'Legal': 'Pháp lý',
    'Macro': 'Vĩ mô',
    'View context': 'Xem chi tiết',
    'No updates.': 'Không có cập nhật.',
    'High relevance': 'Mức liên quan cao',
    'Important': 'Quan trọng',
    'Watch': 'Theo dõi',
    'Region': 'Khu vực',
    'Legal topic': 'Chủ đề pháp lý',
    'Interest Rates': 'Lãi suất',
    'Track deposit, lending, interbank and policy-rate series without mixing publication dates with observation periods.': 'Theo dõi chuỗi lãi suất tiền gửi, cho vay, liên ngân hàng và lãi suất điều hành mà không trộn ngày công bố với kỳ dữ liệu.',
    'Interbank Overnight Rate': 'Lãi suất liên ngân hàng qua đêm',
    'Policy Refinancing Rate': 'Lãi suất tái cấp vốn',
    'Policy Rediscount Rate': 'Lãi suất tái chiết khấu',
    'SBV Overnight Lending Facility Rate': 'Lãi suất cho vay qua đêm của NHNN',
    'Projects, infrastructure and recent developments.': 'Dự án, hạ tầng và các diễn biến gần đây.',
    'Developer profile, projects and recent activity.': 'Hồ sơ chủ đầu tư, dự án và hoạt động gần đây.',
    'Official documents, effective dates and analysis.': 'Văn bản chính thức, ngày hiệu lực và phân tích.',
    'Deposit, lending and interbank rate views.': 'Theo dõi lãi suất tiền gửi, cho vay và liên ngân hàng.',
    'Domestic Gold': 'Vàng trong nước',
    'Domestic Gold Sell': 'Giá bán vàng trong nước',
    '12M Deposit Rate': 'Lãi suất tiền gửi 12T',
    'Lending Rate': 'Lãi suất cho vay',
    'Average Lending Rate': 'Lãi suất cho vay bình quân',
    'VND Deposit Rate 6–12M': 'Lãi suất tiền gửi VND 6–12T',
    'Average VND Lending Rate Range': 'Biên lãi suất cho vay VND bình quân',
    'Credit Growth': 'Tăng trưởng tín dụng',
    'Credit Growth YTD': 'Tăng trưởng tín dụng YTD',
    'Bank Funding Growth YTD': 'Tăng trưởng huy động vốn YTD',
    'CPI YoY': 'CPI so với cùng kỳ',
    'CANONICAL': 'CHÍNH THỨC',
    'CORROBORATED': 'ĐÃ ĐỐI CHIẾU',
    'Stable': 'Ổn định',
    'Illustrative average': 'Bình quân minh họa',
    'Monthly · Demo': 'Theo tháng · Mô phỏng',
    'VND/USD · Demo snapshot': 'VND/USD · Ảnh chụp mô phỏng',
    'VND/tael · Demo': 'VND/lượng · Mô phỏng',
    'YTD · Demo': 'Từ đầu năm · Mô phỏng',
    'Demo': 'Mô phỏng',
    'DEMO': 'MÔ PHỎNG',
    'Demo data': 'Dữ liệu mô phỏng',
    'Integrated data': 'Dữ liệu tích hợp',
    'Curated registries': 'Cơ sở dữ liệu tuyển chọn',
    'Unavailable': 'Chưa khả dụng',
    'No production data': 'Chưa có dữ liệu production',
    '8 curated projects': '8 dự án tuyển chọn',
    '9 official documents': '9 văn bản chính thức',
    '8 infrastructure projects': '8 dự án hạ tầng',
    '15 production records': '15 bản ghi production',
    'Nam Long Experience 2026 showcases Waterpoint, Mizuki Park and Izumi City': 'Nam Long Experience 2026 giới thiệu Waterpoint, Mizuki Park và Izumi City',
    'CBRE: HCMC Q2/2026 condominium launches fall to 850 units': 'CBRE: Nguồn cung căn hộ mở bán mới tại TPHCM Q2/2026 giảm còn 850 căn',
    '226/2025/NĐ-CP · Amendments to Land Law implementation decrees': '226/2025/NĐ-CP · Sửa đổi các nghị định hướng dẫn thi hành Luật Đất đai',
    '102/2024/NĐ-CP · Detailed implementation of the Land Law': '102/2024/NĐ-CP · Quy định chi tiết thi hành Luật Đất đai',
    'Bến Lức – Long Thành expressway opens along the full route': 'Cao tốc Bến Lức – Long Thành thông xe toàn tuyến',
    'Government calls for Ring Road 4 land-clearance and funding bottlenecks to be resolved': 'Chính phủ yêu cầu gỡ vướng mặt bằng và nguồn vốn cho Vành đai 4 TPHCM',
    'USD/VND central rate at 25,643': 'Tỷ giá trung tâm USD/VND ở mức 25.643',
    'Domestic gold selling price at VND 143.5 mn/tael': 'Giá bán vàng trong nước ở mức 143,5 triệu đồng/lượng',
    'The expressway moved to operational status after the full-route opening reported by the Government source.': 'Tuyến cao tốc chuyển sang trạng thái vận hành sau khi nguồn Chính phủ xác nhận thông xe toàn tuyến.',
    'HCMC apartment new supply falls to 850 units': 'Nguồn cung căn hộ mới tại TPHCM giảm còn 850 căn',
    'CBRE reports 850 new condominium units in Q2/2026, down from 1,642 units in Q1/2026. Sales remain blank where the source does not publish a comparable figure.': 'CBRE ghi nhận 850 căn hộ mở bán mới trong Q2/2026, giảm từ 1.642 căn trong Q1/2026. Doanh số được để trống khi nguồn không công bố số liệu có thể so sánh.',
    'Decree 226/2025/NĐ-CP amends Land Law implementation decrees': 'Nghị định 226/2025/NĐ-CP sửa đổi các nghị định hướng dẫn Luật Đất đai',
    'The official Government document updates parts of the detailed Land Law implementation framework and is tracked together with the original decrees.': 'Văn bản chính thức của Chính phủ cập nhật một số nội dung trong hệ thống nghị định hướng dẫn Luật Đất đai và được theo dõi cùng các nghị định gốc.',
    'USD/VND central rate recorded at 25,643': 'Tỷ giá trung tâm USD/VND ghi nhận 25.643',
    'Latest controlled production observation, corroborated by the approved source set.': 'Quan sát production có kiểm soát mới nhất, đã được đối chiếu theo bộ nguồn được phê duyệt.',
    'Domestic gold selling price recorded at VND 143.5 mn/tael': 'Giá bán vàng trong nước ghi nhận 143,5 triệu đồng/lượng',
    'Latest corroborated gold observation in the controlled production repository.': 'Quan sát giá vàng mới nhất đã được đối chiếu trong kho production có kiểm soát.',
    'September CPI YoY recorded at 5.08%': 'CPI tháng 9 so với cùng kỳ ghi nhận 5,08%',
    'NSO September 2026 CPI observation is stored as a verified production record.': 'Quan sát CPI tháng 9/2026 của NSO được lưu dưới dạng bản ghi production đã xác minh.',
    'The latest infrastructure milestone changes the project status to operational in the curated registry.': 'Mốc hạ tầng mới nhất chuyển trạng thái dự án sang vận hành trong cơ sở dữ liệu tuyển chọn.',
    'Effective 15 Aug 2025 · Government': 'Hiệu lực 15 Aug 2025 · Chính phủ',
    'Effective 01 Aug 2024 · Government': 'Hiệu lực 01 Aug 2024 · Chính phủ',
    '01 Oct 2026 · Government': '01 Oct 2026 · Chính phủ',
    '28 Aug 2026 · Government': '28 Aug 2026 · Chính phủ',
    '05 Oct 2026 · Corroborated': '05 Oct 2026 · Đã đối chiếu',
    'Meta unavailable': 'Không có metadata',

    // Market UI
    'Tracked Projects': 'Dự án theo dõi',
    'Official registry': 'Cơ sở dữ liệu chính thức',
    'Current snapshot': 'Tình hình hiện tại',
    'Current situation': 'Tình hình hiện tại',
    'Key Infrastructure Projects': 'Dự án hạ tầng trọng điểm',
    'Open database': 'Mở cơ sở dữ liệu',
    'Recent milestones': 'Mốc gần đây',
    'What Changed': 'Điểm thay đổi',
    'View timeline': 'Xem tiến độ',
    'Schedule monitor': 'Theo dõi tiến độ',
    'Upcoming Targets': 'Mốc sắp tới',
    'Latest Infrastructure News': 'Tin hạ tầng mới nhất',
    'View all': 'Xem tất cả',
    'Curated first-party entities': 'Hồ sơ tuyển chọn từ nguồn chủ đầu tư',
    'Active / Selling': 'Đang triển khai / bán hàng',
    'Current disclosed status': 'Trạng thái công bố hiện tại',
    'Known Product Units': 'Số sản phẩm đã công bố',
    'Verified Price Snapshots': 'Ảnh chụp giá đã xác minh',
    'No estimated project pricing': 'Không tự ước tính giá dự án',
    'Published observations': 'Quan sát đã công bố',
    'HCMC apartment': 'Căn hộ TP.HCM',
    'Supply & Sales': 'Nguồn cung & Bán hàng',
    'Latest activity': 'Hoạt động mới nhất',
    'Market Developments': 'Diễn biến thị trường',
    'Curated first-party entities': 'Hồ sơ tuyển chọn từ nguồn chủ đầu tư',
    'Active / Selling': 'Đang triển khai / bán hàng',
    'Current disclosed status': 'Trạng thái công bố hiện tại',
    'Known Product Units': 'Số sản phẩm đã công bố',
    'Verified Price Snapshots': 'Ảnh chụp giá đã xác minh',
    'No estimated project pricing': 'Không tự ước tính giá dự án',
    'Published observations': 'Quan sát đã công bố',
    'Verified project pricing': 'Giá dự án đã xác minh',
    'Pricing Snapshot': 'Ảnh chụp giá',
    'Market Benchmarks': 'Benchmark thị trường',
    'Verified Project Pricing': 'Giá dự án đã xác minh',
    'Project entity source': 'Nguồn hồ sơ dự án',
    'ongoing': 'đang triển khai',
    'Tracked projects': 'Dự án theo dõi',
    'Key Projects': 'Dự án chính',
    'Selected projects': 'Dự án được chọn',
    'ASP Trend': 'Xu hướng giá bán',
    'Project database': 'Cơ sở dữ liệu dự án',
    'Filter structured project records, then open a project for metrics, phases and related market updates.': 'Lọc hồ sơ dự án có cấu trúc, sau đó mở từng dự án để xem chỉ số, phân kỳ và cập nhật thị trường liên quan.',
    'Historical observations': 'Quan sát lịch sử',
    'Only source-published metrics are stored. Missing sales, absorption or price values remain blank rather than being inferred.': 'Chỉ lưu các chỉ tiêu được nguồn công bố. Doanh số, hấp thụ hoặc giá thiếu được để trống thay vì suy diễn.',
    'Observation History': 'Lịch sử quan sát',
    'Evidence-backed price observations': 'Quan sát giá có bằng chứng',
    'Developer-stated project prices and independent market benchmarks are kept separate. No missing project price is estimated.': 'Giá do chủ đầu tư công bố được tách khỏi benchmark nghiên cứu độc lập. Không tự ước tính giá dự án còn thiếu.',
    'Verified Project Pricing': 'Giá dự án đã xác minh',
    'Latest Pricing Snapshot': 'Ảnh chụp giá mới nhất',
    'Developer registry': 'Danh mục chủ đầu tư',
    'Developer records resolve to project relationships instead of storing duplicate project lists.': 'Hồ sơ chủ đầu tư liên kết tới dự án thay vì lưu trùng danh sách dự án.',
    'Evidence layer': 'Lớp bằng chứng',
    'Market News & Research': 'Tin tức & Nghiên cứu thị trường',
    'Articles are evidence linked to projects, developers and regions; they are not treated as the same thing as market events.': 'Bài viết là bằng chứng liên kết với dự án, chủ đầu tư và khu vực; không được xem là cùng một loại dữ liệu với sự kiện thị trường.',
    'Project': 'Dự án',
    'Units': 'Số căn',
    'Latest ASP': 'Giá bán mới nhất',
    'Absorption': 'Hấp thụ',
    'New Supply': 'Nguồn cung mới',
    'Sales': 'Bán hàng',
    'Average ASP': 'Giá bán TB',
    'Basis': 'Cơ sở giá',
    'Planned units': 'Số căn dự kiến',
    'Area': 'Diện tích',
    'Overview': 'Tổng quan',
    'Segments': 'Phân khúc',
    'Phases': 'Phân kỳ',
    'Related Infrastructure': 'Hạ tầng liên quan',
    'Data Provenance': 'Nguồn gốc dữ liệu',
    'Recent Evidence': 'Bằng chứng gần đây',
    'No phase records yet.': 'Chưa có dữ liệu phân kỳ.',
    'No direct infrastructure links in the curated dataset.': 'Chưa có liên kết hạ tầng trực tiếp trong bộ dữ liệu tuyển chọn.',
    'No quantitative market observation is published for this project in the curated dataset.': 'Chưa có quan sát định lượng được công bố cho dự án này trong bộ dữ liệu tuyển chọn.',
    'No related articles.': 'Không có bài viết liên quan.',
    'No projects match the selected filters.': 'Không có dự án phù hợp với bộ lọc.',
    'No observations for this region.': 'Không có quan sát cho khu vực này.',
    'No comparable pricing records.': 'Không có dữ liệu giá có thể so sánh.',
    'No articles match the selected filters.': 'Không có bài viết phù hợp với bộ lọc.',
    'selling': 'đang bán',
    'construction': 'đang xây dựng',
    'handover': 'bàn giao',
    'pre launch': 'chuẩn bị mở bán',
    'apartment': 'căn hộ',
    'landed': 'nhà thấp tầng',
    'township': 'đô thị tích hợp',
    'industrial': 'BĐS công nghiệp',
    'hospitality': 'nghỉ dưỡng',
    'development phase': 'giai đoạn phát triển',
    'tower': 'tòa',
    'block': 'khối',
    'parcel': 'lô',
    'subdivision': 'phân khu',
    'cluster': 'cụm',

    // Legal official-registry cleanup
    'Official registry': 'Cơ sở dữ liệu chính thức',
    'Curated official registry.': 'Cơ sở dữ liệu văn bản chính thức.',
    'Core real-estate legal documents are linked to official Government sources. Summaries are research notes for navigation only and are not legal advice; always open the official document for interpretation and application.': 'Các văn bản pháp lý bất động sản cốt lõi được liên kết tới nguồn chính thức của Chính phủ. Phần tóm tắt chỉ phục vụ tra cứu nghiên cứu, không phải tư vấn pháp lý; khi áp dụng cần mở văn bản gốc.',
    'Official Government document registry': 'Danh mục văn bản chính thức từ nguồn Chính phủ',
    'Official document layer': 'Lớp văn bản chính thức',
    'Latest Documents': 'Văn bản mới nhất',
    'Effective Timeline': 'Lịch hiệu lực',
    'No upcoming effective dates.': 'Không có văn bản sắp có hiệu lực.',
    'Research shortcuts': 'Lối tắt nghiên cứu',
    'Legal Topics': 'Chủ đề pháp lý',
    'Recently active': 'Có hiệu lực gần đây',
    'Recently Effective': 'Mới có hiệu lực',
    'Government': 'Chính phủ',
    'National Assembly': 'Quốc hội',
    'Ministry of Construction': 'Bộ Xây dựng',
    'Ministry of Finance': 'Bộ Tài chính',
    'HCMC People’s Committee': 'UBND TP.HCM',
    'Effective today': 'Có hiệu lực hôm nay',
    'Official URL is not available for this record. Source metadata remains visible through the registry.': 'Chưa có URL chính thức cho bản ghi này. Metadata nguồn vẫn được hiển thị trong danh mục.',

    // Legal UI
    'Tracked Documents': 'Văn bản theo dõi',
    'Illustrative legal database': 'Cơ sở dữ liệu pháp lý minh họa',
    'Currently Effective': 'Đang có hiệu lực',
    'Derived from status + effective date': 'Suy ra từ trạng thái + ngày hiệu lực',
    'Drafts': 'Dự thảo',
    'Draft is a status, not a document type': 'Dự thảo là trạng thái, không phải loại văn bản',
    'Effective ≤ 90 Days': 'Có hiệu lực ≤ 90 ngày',
    'Upcoming effective dates': 'Ngày hiệu lực sắp tới',
    'Number': 'Số hiệu',
    'Document': 'Văn bản',
    'Issued / Draft': 'Ban hành / Dự thảo',
    'Effective': 'Hiệu lực',
    'Official document database': 'Cơ sở dữ liệu văn bản chính thức',
    'Filter structured legal records by type, status, issuing agency, topic and scope. Media analysis remains a separate evidence layer.': 'Lọc hồ sơ pháp lý có cấu trúc theo loại, trạng thái, cơ quan ban hành, chủ đề và phạm vi. Phân tích truyền thông vẫn là một lớp bằng chứng riêng.',
    'Effective-date monitor': 'Theo dõi ngày hiệu lực',
    'Effective Soon': 'Sắp có hiệu lực',
    'Upcoming dates are derived from canonical effective dates; “effective soon” is never stored as source-of-truth.': 'Các mốc sắp tới được suy ra từ ngày hiệu lực chuẩn; “sắp có hiệu lực” không được lưu như dữ liệu nguồn gốc.',
    'Next 30 Days': '30 ngày tới',
    'Near term': 'Ngắn hạn',
    '31–90 Days': '31–90 ngày',
    'Upcoming': 'Sắp tới',
    'Later': 'Sau đó',
    'Longer horizon': 'Dài hạn hơn',
    'Controlled taxonomy': 'Danh mục phân loại kiểm soát',
    'Topics are controlled categories used for document filters and research links, rather than free-text tags invented by the crawler.': 'Chủ đề là danh mục kiểm soát dùng cho bộ lọc và liên kết nghiên cứu, thay vì thẻ văn bản tự do do bộ thu thập tự tạo.',
    'Legal News & Analysis': 'Tin tức & Phân tích pháp lý',
    'Analysis helps interpret a document, but the official legal record remains the source of truth. Related documents are shown explicitly on each item.': 'Phân tích hỗ trợ diễn giải văn bản, nhưng hồ sơ pháp lý chính thức vẫn là nguồn chuẩn. Văn bản liên quan được hiển thị rõ trên từng mục.',
    'Lifecycle': 'Vòng đời văn bản',
    'Key Changes': 'Thay đổi chính',
    'Topics': 'Chủ đề',
    'Related Regulations': 'Quy định liên quan',
    'Related Analysis / News': 'Phân tích / Tin liên quan',
    'Official Source': 'Nguồn chính thức',
    'Issued': 'Ban hành',
    'Draft published': 'Công bố dự thảo',
    'Replaced': 'Bị thay thế',
    'Implements': 'Thi hành',
    'Guides': 'Hướng dẫn',
    'Amends': 'Sửa đổi',
    'Replaces': 'Thay thế',
    'References': 'Tham chiếu',
    'Implemented by': 'Được thi hành bởi',
    'Guided by': 'Được hướng dẫn bởi',
    'Amended by': 'Được sửa đổi bởi',
    'Replaced by': 'Được thay thế bởi',
    'Referenced by': 'Được tham chiếu bởi',
    'No documents match the selected filters.': 'Không có văn bản phù hợp với bộ lọc.',
    'No documents in this window.': 'Không có văn bản trong khoảng thời gian này.',
    'No documents became effective in the last 30 days.': 'Không có văn bản có hiệu lực trong 30 ngày gần đây.',
    'No lifecycle dates available.': 'Không có dữ liệu ngày trong vòng đời văn bản.',
    'No structured change notes.': 'Không có ghi chú thay đổi có cấu trúc.',
    'No related-document records.': 'Không có dữ liệu văn bản liên quan.',
    'No related analysis.': 'Không có phân tích liên quan.',
    'No legal articles match the selected filters.': 'Không có bài viết pháp lý phù hợp với bộ lọc.',
    'Official URL is intentionally not connected in this illustrative demo dataset. Source metadata remains visible through the registry.': 'URL chính thức chưa được kết nối trong bộ dữ liệu mô phỏng. Metadata nguồn vẫn được hiển thị qua danh mục nguồn.',
    'draft': 'dự thảo',
    'issued': 'đã ban hành',
    'effective': 'có hiệu lực',
    'expired': 'hết hiệu lực',
    'replaced': 'bị thay thế',
    'withdrawn': 'đã rút',
    'Law': 'Luật',
    'Resolution': 'Nghị quyết',
    'Decree': 'Nghị định',
    'Circular': 'Thông tư',
    'Decision': 'Quyết định',
    'Guidance': 'Hướng dẫn',
    'National': 'Toàn quốc',
    'Local': 'Địa phương',
    'Multi Region': 'Nhiều khu vực',

    // Infrastructure UI
    'Curated official infrastructure registry': 'Cơ sở dữ liệu hạ tầng chính thức được tuyển chọn',
    'Under Construction': 'Đang thi công',
    'Operational': 'Đang vận hành',
    'Historical records remain searchable': 'Dữ liệu lịch sử vẫn có thể tra cứu',
    'Regions Covered': 'Khu vực được theo dõi',
    'No numeric progress': 'Không có % tiến độ',
    'Infrastructure Project': 'Dự án hạ tầng',
    'Progress': 'Tiến độ',
    'Current Target': 'Mốc hiện tại',
    'Related RE': 'BĐS liên quan',
    'Current target': 'Mốc hiện tại',
    'Investment': 'Vốn đầu tư',
    'Research links': 'Liên kết nghiên cứu',
    'Schedule History': 'Lịch sử tiến độ',
    'Recent Milestones': 'Mốc gần đây',
    'Related Real Estate Projects': 'Dự án BĐS liên quan',
    'Related Evidence': 'Bằng chứng liên quan',
    'No schedule records yet.': 'Chưa có dữ liệu tiến độ.',
    'No milestone records.': 'Không có dữ liệu mốc tiến độ.',
    'No direct real-estate project links in the current registry.': 'Chưa có liên kết trực tiếp tới dự án BĐS trong cơ sở dữ liệu hiện tại.',
    'No infrastructure projects match the selected filters.': 'Không có dự án hạ tầng phù hợp với bộ lọc.',
    'No infrastructure articles match the selected filters.': 'Không có bài viết hạ tầng phù hợp với bộ lọc.',
    'Infrastructure News & Research': 'Tin tức & Nghiên cứu hạ tầng',
    'Articles support project records and milestones; they do not replace schedule history or current master status.': 'Bài viết hỗ trợ hồ sơ dự án và mốc tiến độ; không thay thế lịch sử tiến độ hay trạng thái hiện tại.',
    'Expressway': 'Cao tốc',
    'Ring Road': 'Đường vành đai',
    'Major Road': 'Đường trục chính',
    'Bridge': 'Cầu',
    'Metro': 'Metro',
    'Railway': 'Đường sắt',
    'Airport': 'Sân bay',
    'Port': 'Cảng',
    'Urban Infrastructure': 'Hạ tầng đô thị',
    'Proposed': 'Đề xuất',
    'Planning': 'Lập kế hoạch',
    'Approved': 'Đã phê duyệt',
    'Land Clearance': 'Giải phóng mặt bằng',
    'land clearance': 'giải phóng mặt bằng',
    'partially operational': 'vận hành một phần',
    'quarter': 'quý',
    'Partially Operational': 'Vận hành một phần',
    'Completed': 'Hoàn thành',
    'under construction': 'đang thi công',
    'operational': 'đang vận hành',
    'current': 'hiện tại',
    'superseded': 'đã thay thế',
    'Expected Completion': 'Dự kiến hoàn thành',
    'Approval': 'Phê duyệt',
    'Funding': 'Nguồn vốn',
    'Construction Start': 'Khởi công',
    'Schedule Change': 'Điều chỉnh tiến độ',
    'Delay': 'Chậm tiến độ',
    'Partial Opening': 'Mở một phần',
    'Operation Start': 'Bắt đầu vận hành',
    'Operation Preparation': 'Chuẩn bị vận hành',
    'Official Update': 'Cập nhật chính thức',

    // Macro UI
    'Canonical': 'Chính thức',
    'Corroborated': 'Đã đối chiếu',
    'Production': 'Production',
    'Controlled production mode.': 'Chế độ production có kiểm soát.',
    'Production observations are labeled by evidence status: verified official data as Canonical and independently matched data as Corroborated. Unpromoted indicators remain illustrative demo data.': 'Quan sát production được gắn nhãn theo mức độ bằng chứng: dữ liệu chính thức đã xác minh là Chính thức, dữ liệu được đối chiếu độc lập là Đã đối chiếu. Các chỉ số chưa được promote vẫn là dữ liệu mô phỏng minh họa.',
    'Controlled production now includes verified NSO banking indicators: Credit Growth YTD and Bank Funding Growth YTD. Canonical and Corroborated labels remain evidence-based; unpromoted indicators remain illustrative demo data.': 'Production có kiểm soát hiện đã bao gồm các chỉ số ngân hàng NSO đã xác minh: Tăng trưởng tín dụng YTD và Tăng trưởng huy động vốn YTD. Nhãn Chính thức và Đã đối chiếu tiếp tục dựa trên mức độ bằng chứng; các chỉ số chưa được promote vẫn là dữ liệu mô phỏng minh họa.',
    'Controlled production includes verified NSO banking indicators plus customer-rate ranges published by the State Bank of Vietnam and independently corroborated through secondary sources. Rate ranges remain low–high ranges; no scalar average is fabricated.': 'Production có kiểm soát bao gồm các chỉ số ngân hàng NSO đã xác minh và các biên lãi suất khách hàng do NHNN công bố được đối chiếu qua các nguồn độc lập. Biên lãi suất luôn giữ dạng thấp–cao; không tạo số bình quân giả.',
    'Latest range': 'Biên mới nhất',
    'Range updated': 'Biên đã thay đổi',
    'No range change': 'Biên không đổi',
    'Lower bound': 'Cận dưới',
    'Upper bound': 'Cận trên',
    'Latest only': 'Chỉ có kỳ mới nhất',
    'Latest observation only · no synthetic history is created.': 'Chỉ có quan sát mới nhất · không tạo lịch sử giả.',
    'Current effective event only · no synthetic history is created.': 'Chỉ hiển thị sự kiện hiệu lực hiện tại · không tạo lịch sử giả.',
    'Controlled production includes verified NSO banking indicators, independently corroborated customer-rate ranges, and independently corroborated SBV policy rates. Rate ranges remain low–high ranges; no scalar average is fabricated.': 'Production có kiểm soát bao gồm các chỉ số ngân hàng NSO đã xác minh, các biên lãi suất khách hàng được đối chiếu độc lập và các lãi suất điều hành NHNN được đối chiếu độc lập. Biên lãi suất vẫn giữ dạng thấp–cao; không tạo số bình quân giả.',
    'Controlled production history · demo points are not mixed into this series.': 'Lịch sử production có kiểm soát · không trộn điểm dữ liệu mô phỏng vào chuỗi này.',
    'Illustrative demo history.': 'Lịch sử mô phỏng minh họa.',
    'No controlled production observations are available. All displayed macro series are illustrative demo data.': 'Chưa có quan sát production có kiểm soát. Toàn bộ chuỗi vĩ mô đang hiển thị là dữ liệu mô phỏng minh họa.',
    'Canonical production series · demo points are not mixed into this indicator. Historical coverage will build as new approved observations are persisted.': 'Chuỗi production chính thức · không trộn điểm dữ liệu mô phỏng vào chỉ số này. Lịch sử sẽ được tích lũy khi các quan sát mới được phê duyệt và lưu.',
    'Corroborated production series · demo points are not mixed into this indicator. Historical coverage will build as new approved observations are persisted.': 'Chuỗi production đã đối chiếu · không trộn điểm dữ liệu mô phỏng vào chỉ số này. Lịch sử sẽ được tích lũy khi các quan sát mới được phê duyệt và lưu.',
    'Illustrative demo series · data date and publication date are stored separately.': 'Chuỗi mô phỏng minh họa · ngày dữ liệu và ngày công bố được lưu riêng.',
    'Demo context': 'Bối cảnh mô phỏng',
    'Illustrative Developments': 'Diễn biến minh họa',
    'View demo news': 'Xem tin mô phỏng',
    'No demo developments remain for unpromoted macro indicators.': 'Không còn diễn biến mô phỏng cho các chỉ số vĩ mô chưa được promote.',
    'Illustrative Macro News & Research': 'Tin tức & Nghiên cứu vĩ mô minh họa',
    'This article layer remains demo-only. Demo articles linked to production indicators are hidden to avoid mixing illustrative evidence with controlled observations.': 'Lớp bài viết này vẫn chỉ là dữ liệu mô phỏng. Các bài mô phỏng liên quan đến chỉ số production được ẩn để tránh trộn bằng chứng minh họa với quan sát có kiểm soát.',
    'No demo macro articles match the selected filters.': 'Không có bài viết vĩ mô mô phỏng phù hợp với bộ lọc.',
    'No promoted evidence articles yet.': 'Chưa có bài viết bằng chứng nào được promote.',
    'Corroborated production is displayed as the official low–high range. The frontend pairs separately promoted range components and never fabricates a scalar average.': 'Production đã đối chiếu được hiển thị theo biên thấp–cao đã công bố. Giao diện ghép các cấu phần biên được promote riêng biệt và không tạo số bình quân giả.',
    'Corroborated production is displayed as the official low–high range. The frontend pairs separately promoted range components and never collapses the range into a single average.': 'Production đã đối chiếu được hiển thị theo biên thấp–cao đã công bố. Giao diện ghép các cấu phần biên được promote riêng biệt và không rút gọn biên thành một số bình quân.',
    'Matched across independent sources': 'Khớp giữa các nguồn độc lập',
    'Daily monitor': 'Theo dõi hằng ngày',
    'USD/VND Central Rate': 'Tỷ giá trung tâm USD/VND',
    'Latest releases': 'Công bố mới nhất',
    'Macro Developments': 'Diễn biến vĩ mô',
    'Comparable series': 'Chuỗi có thể so sánh',
    'Key Indicators': 'Chỉ số chính',
    'Foreign Exchange': 'Tỷ giá',
    'Gold': 'Vàng',
    'Liquidity, Credit & Money Supply': 'Thanh khoản, Tín dụng & Cung tiền',
    'Inflation': 'Lạm phát',
    'Historical series': 'Chuỗi lịch sử',
    "State Bank of Vietnam refinancing policy rate.": "Lãi suất tái cấp vốn của Ngân hàng Nhà nước Việt Nam.",
    "State Bank of Vietnam rediscount policy rate.": "Lãi suất tái chiết khấu của Ngân hàng Nhà nước Việt Nam.",
    "State Bank of Vietnam overnight lending / clearing-deficit facility rate.": "Lãi suất cho vay qua đêm/bù thiếu hụt thanh toán của Ngân hàng Nhà nước Việt Nam.",
    "Event-driven policy rate. Controlled production requires two independent trusted sources to agree on the decision, effective date and value. No synthetic history is created.": "Lãi suất điều hành theo sự kiện. Production có kiểm soát yêu cầu hai nguồn tin cậy độc lập cùng xác nhận quyết định, ngày hiệu lực và mức lãi suất. Không tạo lịch sử giả.",
    "Event-driven administered policy rate. It is distinct from the market interbank overnight rate. Controlled production requires two independent trusted sources to agree on the decision, effective date and value.": "Lãi suất điều hành theo sự kiện, tách biệt với lãi suất qua đêm trên thị trường liên ngân hàng. Production có kiểm soát yêu cầu hai nguồn tin cậy độc lập cùng xác nhận quyết định, ngày hiệu lực và mức lãi suất.",
    'Observation history': 'Lịch sử quan sát',
    'Value': 'Giá trị',
    'Recent Data': 'Dữ liệu gần đây',
    'Macro News & Research': 'Tin tức & Nghiên cứu vĩ mô',
    'Articles explain or contextualize series; they do not replace the underlying observations.': 'Bài viết giải thích hoặc bổ sung bối cảnh cho chuỗi dữ liệu; không thay thế các quan sát gốc.',
    'Macro Indicator': 'Chỉ số vĩ mô',
    'Definition': 'Định nghĩa',
    'Methodology': 'Phương pháp',
    'Recent Observations': 'Quan sát gần đây',
    'Previous available observation': 'Quan sát khả dụng trước đó',
    'Current displayed observation': 'Quan sát hiện đang hiển thị',
    'No current observation source available.': 'Không có nguồn cho quan sát hiện tại.',
    'No related articles.': 'Không có bài viết liên quan.',
    'No macro articles match the selected filters.': 'Không có bài viết vĩ mô phù hợp với bộ lọc.',
    'Interest Rate': 'Lãi suất',
    'Banking Liquidity': 'Thanh khoản ngân hàng',
    'Credit': 'Tín dụng',
    'Money Supply': 'Cung tiền',
    'Fx': 'Tỷ giá',
    'Daily': 'Hằng ngày',
    'Weekly': 'Hằng tuần',
    'Monthly': 'Hằng tháng',
    'Quarterly': 'Hằng quý',
    'Annual': 'Hằng năm',
    'Event Driven': 'Theo sự kiện',
    'Preliminary': 'Sơ bộ',
    'Final': 'Chính thức',
    'Revised': 'Điều chỉnh',

    // Article/content type badges (only exact badge text is changed)
    'news': 'tin tức',
    'research': 'nghiên cứu',
    'report': 'báo cáo',
    'analysis': 'phân tích',
    'announcement': 'thông báo',
    'press release': 'thông cáo báo chí',
    'press-release': 'thông cáo báo chí'
  }));

  const PLACEHOLDERS = new Map(Object.entries({
    'Project or location…': 'Dự án hoặc vị trí…',
    'Number, title or topic…': 'Số hiệu, tiêu đề hoặc chủ đề…',
    'Analysis, document or topic…': 'Phân tích, văn bản hoặc chủ đề…',
    'Project, region or related market…': 'Dự án, khu vực hoặc thị trường liên quan…',
    'Infrastructure news…': 'Tin hạ tầng…',
    'Rates, FX, gold, CPI…': 'Lãi suất, tỷ giá, vàng, CPI…'
  }));


  const originalText = new WeakMap();
  const originalPlaceholder = new WeakMap();

  function language() {
    return window.AppLocalization?.getLanguage?.() || document.documentElement.lang || 'vi';
  }

  function withWhitespace(raw, core) {
    const lead = String(raw).match(/^\s*/)?.[0] || '';
    const tail = String(raw).match(/\s*$/)?.[0] || '';
    return `${lead}${core}${tail}`;
  }

  function translatePattern(core) {
    let match;
    if ((match = core.match(/^(\d+) updates$/))) return `${match[1]} cập nhật`;
    if ((match = core.match(/^(\d+) projects$/))) return `${match[1]} dự án`;
    if ((match = core.match(/^(\d+) tracked projects$/))) return `${match[1]} dự án theo dõi`;
    if ((match = core.match(/^(\d+) selling$/))) return `${match[1]} đang bán`;
    if ((match = core.match(/^(\d+) developers$/))) return `${match[1]} chủ đầu tư`;
    if ((match = core.match(/^(\d+) documents$/))) return `${match[1]} văn bản`;
    if ((match = core.match(/^Official registry · (\d+) documents$/))) return `Cơ sở dữ liệu chính thức · ${match[1]} văn bản`;
    if ((match = core.match(/^Official registry · (\d+) projects$/))) return `Cơ sở dữ liệu chính thức · ${match[1]} dự án`;
    if ((match = core.match(/^(\d+) legal topics$/))) return `${match[1]} chủ đề pháp lý`;
    if ((match = core.match(/^(\d+) upcoming$/))) return `${match[1]} sắp tới`;
    if ((match = core.match(/^(\d+) drafts$/))) return `${match[1]} dự thảo`;
    if ((match = core.match(/^In (\d+) days$/))) return `Còn ${match[1]} ngày`;
    if ((match = core.match(/^(\d+) days ago$/))) return `${match[1]} ngày trước`;
    if ((match = core.match(/^Demo data · (.+)$/))) return `Dữ liệu mô phỏng · ${match[1]}`;
    if ((match = core.match(/^Controlled macro · (\d+) production records$/))) return `Vĩ mô kiểm soát · ${match[1]} bản ghi production`;
    if ((match = core.match(/^Integrated data · 4 curated modules · (\d+) macro records$/))) return `Dữ liệu tích hợp · 4 module thực · ${match[1]} bản ghi vĩ mô`;
    if ((match = core.match(/^Curated registries · (.+)$/))) return `Cơ sở dữ liệu tuyển chọn · ${match[1]}`;
    if ((match = core.match(/^Mixed data · (\d+) controlled macro records$/))) return `Dữ liệu hỗn hợp · ${match[1]} bản ghi vĩ mô có kiểm soát`;
    if ((match = core.match(/^Published (.+)$/))) return `Công bố ${match[1]}`;
    if ((match = core.match(/^Announced (.+)$/))) return `Công bố ${match[1]}`;
    if ((match = core.match(/^Source: (.+)$/))) return `Nguồn: ${match[1]}`;
    if ((match = core.match(/^Related RE: (.+)$/))) return `BĐS liên quan: ${match[1]}`;
    if ((match = core.match(/^Official context: (.+)$/))) return `Ngữ cảnh chính thức: ${match[1]}`;
    if ((match = core.match(/^(\d+) targets through 2027$/))) return `${match[1]} mốc đến hết 2027`;
    if ((match = core.match(/^(\d+) source definitions$/))) return `${match[1]} định nghĩa nguồn`;
    if ((match = core.match(/^P(\d+) · lower number = higher sourcing priority$/))) return `P${match[1]} · số nhỏ hơn = mức ưu tiên nguồn cao hơn`;
    if ((match = core.match(/^Latest displayed market observation · (.+)$/))) return `Quan sát thị trường mới nhất đang hiển thị · ${match[1]}`;
    if ((match = core.match(/^Current displayed observation · (.+)$/))) return `Quan sát hiện đang hiển thị · ${match[1]}`;
    return null;
  }

  function translatedCore(core) {
    return EN_VI.get(core) || translatePattern(core) || core;
  }

  function translateTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE || !node.parentElement) return;
    const tag = node.parentElement.tagName;
    if (['SCRIPT', 'STYLE', 'CODE', 'PRE', 'CANVAS'].includes(tag)) return;
    const raw = node.nodeValue;
    const core = String(raw || '').trim();
    if (!core) return;
    const translated = translatedCore(core);
    if (translated !== core) {
      if (!originalText.has(node)) originalText.set(node, raw);
      node.nodeValue = withWhitespace(raw, translated);
    }
  }

  function restoreTextNode(node) {
    if (originalText.has(node)) {
      node.nodeValue = originalText.get(node);
      originalText.delete(node);
    }
  }

  function translateAttributes(element) {
    if (!(element instanceof Element)) return;
    if (element.hasAttribute('placeholder')) {
      const current = element.getAttribute('placeholder') || '';
      if (PLACEHOLDERS.has(current)) {
        if (!originalPlaceholder.has(element)) originalPlaceholder.set(element, current);
        element.setAttribute('placeholder', PLACEHOLDERS.get(current));
      }
    }
  }

  function restoreAttributes(element) {
    if (!(element instanceof Element)) return;
    if (originalPlaceholder.has(element)) {
      element.setAttribute('placeholder', originalPlaceholder.get(element));
      originalPlaceholder.delete(element);
    }
  }

  function walk(root, callback) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      callback(root);
      return;
    }
    if (!(root instanceof Element) && root !== document) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) callback(node);
  }

  function translateTree(root) {
    if (!root) return;
    if (root instanceof Element) translateAttributes(root);
    walk(root, translateTextNode);
    if (root.querySelectorAll) root.querySelectorAll('[placeholder]').forEach(translateAttributes);
  }

  function restoreTree(root) {
    if (!root) return;
    if (root instanceof Element) restoreAttributes(root);
    walk(root, restoreTextNode);
    if (root.querySelectorAll) root.querySelectorAll('[placeholder]').forEach(restoreAttributes);
  }

  let observer = null;
  let applying = false;

  function apply(lang = language()) {
    if (applying || !document.body) return;
    applying = true;
    try {
      if (lang === 'vi') translateTree(document.body);
      else restoreTree(document.body);
    } catch (error) {
      console.warn('[localization-dynamic] non-fatal translation error:', error);
    } finally {
      applying = false;
    }
  }

  function observe() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      if (applying || language() !== 'vi') return;
      for (const mutation of mutations) {
        mutation.addedNodes.forEach(node => {
          try { translateTree(node); } catch (_) {}
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function init() {
    try {
      apply(language());
      observe();
      document.addEventListener('app:language-changed', event => apply(event.detail?.language || language()));
    } catch (error) {
      console.warn('[localization-dynamic] disabled after non-fatal error:', error);
    }
  }

  window.AppDynamicLocalization = {
    apply,
    translate: (text, lang = language()) => lang === 'vi' ? translatedCore(String(text ?? '')) : String(text ?? '')
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
