# Tiêu chí chọn ngách và tìm 1 app để làm

Cập nhật: 2026-10-27. File sống, vừa research vừa update.

## Phễu 4 bước

1. **Hot Map**: quét Top Free + Trending Google Play theo 6-8 nước (US, BR, IN, ID, MX, DE, JP, VN) × category. Chỉ ghi app phát hành 12-24 tháng đã lọt top. Ra bảng nước × category, ô nhiều app mới nhất là vùng nóng.
2. **Category**: giữ Tools, Personalization, Art & Design, Entertainment, Lifestyle, Photography. Bỏ Finance, Health, Medical, News, Dating, ngách dính bản quyền. Chỉ giữ category mà app dẫn đầu kiếm tiền IAA hoặc hybrid.
3. **Chấm ngách** theo bảng dưới. Nhóm A, B rớt 1 tiêu chí là loại. Nhóm C, D chấm 1-5.
4. **Chọn 1 app**: app tham chiếu là app mới nhất trong ngách vẫn đang tăng. Mổ xẻ core loop 1 phút đầu, vị trí ads, lý do quay lại hôm sau. Định nghĩa đúng 1 điểm khác biệt.

## A. Thị trường (loại ngay nếu rớt)

| Tiêu chí | Số đo | Ngưỡng |
|---|---|---|
| Xu hướng tải | Tải/ngày tháng này so với 3 tháng trước | Tăng hoặc đi ngang |
| Độ rộng địa lý | Số nước app top ngách lọt Top 100 category | Từ 5 nước, có ít nhất 1 nước eCPM cao (US, DE, JP) |
| Mùa vụ | Google Trends từ khóa ngách 5 năm | Không lệch mùa quá 50% |
| Tuổi ngách | Năm app top ngách phát hành | Có app mới thắng trong 24 tháng |
| Tổng cầu | Volume từ khóa chính trên Play (asolytics) | Đủ lớn để organic nuôi app |

## B. Rào cản và rủi ro (loại ngay nếu rớt)

| Tiêu chí | Số đo | Ngưỡng |
|---|---|---|
| Chính sách Play | Category, permission, dữ liệu nhạy cảm | Không rơi vào Finance, Health, Families, VPN, loan |
| Bản quyền | Nội dung cần giấy phép không | Toàn bộ asset tự làm hoặc AI tạo được |
| Phụ thuộc API ngoài | App top có sống nhờ API bên thứ ba không | Không phụ thuộc, hoặc có API thay thế |
| Rủi ro Google làm native | Tính năng có sẵn trong Android mới không | Android chưa làm, hoặc làm kém |
| Dễ bị clone | Thời gian 1 dev clone core loop | Trên 3 tuần, hoặc có lợi thế nội dung tích lũy |

## C. Kiếm tiền (chấm 1-5)

| Tiêu chí | Số đo | Ngưỡng |
|---|---|---|
| Mô hình app top | IAA, hybrid, hay subscription | IAA hoặc hybrid |
| Số vị trí ads tự nhiên | Điểm nghỉ trong flow đặt interstitial, rewarded | Từ 3 vị trí |
| Rewarded fit | Có vật phẩm user muốn đổi xem ads không | Có (mở khóa nội dung, bỏ chờ) |
| eCPM ngách | eCPM trung bình category tại nước đích | Không thấp hơn trung bình Tools |
| Cạnh tranh UA từ khóa | Số app chạy ads từ khóa Play, số advertiser app-ads.txt, CPC | Dưới 3 app chạy UA, CPC thấp |
| Cạnh tranh organic | Số app cùng từ khóa có trên 1M tải | Dưới 10 app |

### C bổ sung. Chi phí mua user

| Tiêu chí | Số đo | Ngưỡng |
|---|---|---|
| Ít cạnh tranh vị thế UA | Số advertiser chạy creative cho từ khóa ngách trên Meta Ad Library, Google Ads Transparency, AppLovin/Unity | Dưới 5 advertiser trong 30 ngày |
| Big company chưa chạy UA | Top 3 app ngách có thuộc publisher lớn đổ tiền UA không | Không có publisher có trên 10 app 10M+ |
| Số creative đang chạy | Tổng creative active của ngách trên Ad Library | Dưới 50 |
| Keyword bid | CPC từ khóa ngách trên Keyword Planner, nước đích | Dưới trung bình category |
| eCPI thấp | CPI benchmark UAC theo category và nước, kiểm bằng test 50-100 USD | Tier 3 dưới 0,1 USD, Tier 1 dưới 0,5 USD |
| eCPI so với LTV | LTV D30 = eCPM × ads/phiên × retention đối thủ; chia cho eCPI | LTV D30 / eCPI từ 1,5 |
| Thời gian hoàn vốn | Số ngày doanh thu ads cộng dồn vượt CPI | Dưới 14 ngày |
| Creative dễ làm | Quay từ chính app, không cần diễn viên hay 3D | Có, UGC hoặc screen record đủ |
| IPM cao | Ngách có creative kiểu "show kết quả" được không | IPM dự đoán trên 10 |

Đo nhanh eCPI khi chưa test: CPC Keyword Planner × tỉ lệ click sang install của category (20-40% với app content), đối chiếu benchmark CPI của AppsFlyer/Adjust.

## D. Sản phẩm và thói quen (chấm 1-5)

| Tiêu chí | Số đo | Ngưỡng |
|---|---|---|
| Tần suất dùng | Lý do mở hằng ngày: widget, lock screen, nội dung mới, streak | Ít nhất 1 trigger hằng ngày |
| Thời gian phiên | Phiên đủ dài để xem ads | Trên 2 phút |
| Retention đối thủ | Review nhắc "daily", "every day", "months" | Trên 10% review |
| Nội dung tích lũy | Càng dùng càng có giá trị (bộ sưu tập, lịch sử) | Có |
| Số app thắng lặp lại | App mới dưới 2 năm, trên 5k tải/ngày, không big company | Từ 3 app |
| Rating và nỗi đau | Rating app top, review 1-2 sao kêu gì | Có nỗi đau chung chưa ai giải |
| Độ phức tạp build | Số màn hình core, cần backend không | Dưới 8 màn hình, không backend hoặc chỉ Firebase |
| Khả năng mở rộng nội dung | Thêm nội dung có tốn dev không | Chỉ thêm data, không sửa code |

## Trọng số và ngưỡng

- Nhân đôi điểm: Số app thắng lặp lại, Tần suất dùng, eCPI so với LTV.
- Ngách dưới 3 điểm ở bất kỳ tiêu chí C/D nào: loại, không bù trừ.
- Rớt ngay nếu LTV D30 / eCPI dưới 1.
- Tổng tối đa (C + D, có nhân đôi): 115. Ngách dưới 80 bỏ.

## Giả thuyết ngách cần kiểm chứng

| Ngách | Kỳ vọng | Rủi ro đoán trước | Trạng thái |
|---|---|---|---|
| Widget ảnh / lock screen wallpaper | Thói quen mạnh, IAA tốt | Google native hóa | Hot Map: Lock screen 10 app, median 33k/ngày cao nhất. Wallpaper 32 app. Qua bước 2 |
| Âm thanh ngủ / white noise | Dùng hằng đêm, ít UA | Gần Health | Hot Map: chỉ 6 app Ringtone/Sound, không có white noise mới. Yếu |
| Sticker / emoji maker | Tải nhiều | Bản quyền | Hot Map: 5 app, 0 app toàn cầu. Yếu |
| Keyboard theme | Tải lớn | Cạnh tranh ads cao | Hot Map: 13 app, 2 toàn cầu. Trung bình |
| Battery / Charging emoji | Mới nổi, build đơn giản | Dễ clone, sóng ngắn | Hot Map: 17 app, 15 app dưới 12 tháng, 3 toàn cầu. Qua bước 2 |
| Drawing / AR trace | Nhiều app thắng, toàn cầu | Braly JSC thống trị, UA mạnh | Hot Map: 35 app, 8 toàn cầu, top 449k/ngày. Qua bước 2 |
| Mini / ASMR games | Median dl cao nhất | Thuộc Game, sóng trend | Hot Map: 42 app, 10 toàn cầu, median 33k. Qua bước 2 |
| Widget / Icon / Theme | Thói quen, IAA | Cạnh tranh ads cao | Hot Map: 21 app, 4 toàn cầu, median 19.8k. Qua bước 2 |
| Launcher theo game (Candy Race, Pillow Chase) | Xu hướng mới, tải lớn | Google siết launcher, sóng ngắn | Hot Map: 27 app, 3 toàn cầu. Qua bước 2 |
| Coloring / ASMR coloring | Đã có ngách trong Dream100 | Cạnh tranh ads | Hot Map: 9 app, Sand ASMR Coloring 175k/ngày. Đối chiếu Dream100 |
| AI video / photo generator | Nóng nhất, 9 app toàn cầu | Phụ thuộc API, chi phí server, rớt nhóm B | Loại ở bước 2 |
| Short drama | 90 app mới | Bản quyền nội dung, rớt nhóm B | Loại |
| Cleaner / VPN / Scanner | Nhiều app | Chính sách, UA đắt | Loại |

## Nhật ký research

- 2026-10-27: chạy Hot Map bước 1. Nguồn: Top Free 200 của 8 nước × 8 category (TOOLS, PERSONALIZATION, ART_AND_DESIGN, ENTERTAINMENT, LIFESTYLE, PHOTOGRAPHY, MUSIC_AND_AUDIO, GAME_CASUAL), 12.779 dòng, 5.924 app, 2.735 app phát hành dưới 24 tháng. Script: `scripts/hotmap_list.mjs` (Node, cần `npm i`), `scripts/hotmap.py` (chi tiết + bảng nhiệt), `scripts/hotmap_cluster.py` (ngách con). Kết quả: `data/hotmap/hotmap.md`, `data/hotmap/clusters.md`, `data/hotmap/hotmap_apps.csv`.
  - Bảng nước × category không phân biệt được: category nào cũng 40-60% app mới. Hot Map phải nhìn ở ngách con.
  - Lọc ads + không big dev + trên 5k tải/ngày + lọt top ở từ 3 nước: 986 app. Xếp ngách con theo số app thắng, xem bảng giả thuyết.
  - JP là nước lệch nhất (LIFESTYLE chỉ 8 app mới), không dùng JP làm nước đích cho ngách Lifestyle.
- 2026-10-27: lập khung tiêu chí. Chưa đối chiếu với Dream100 và ngách Coloring đã log, sẽ đối chiếu sau khi có điểm bước 3.
