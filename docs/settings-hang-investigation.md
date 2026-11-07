# Điều tra Settings không phản hồi — PID 4414

Ngày rà soát: 07/11/2026. Đây là điều tra tĩnh mã nguồn; chưa có backtrace hoặc
phiên chạy UKUI tái hiện lỗi. Số `4414` trong ảnh là PID, không phải mã lỗi.
Không thể dùng PID trong ảnh để xác định hàm đang treo.

## Nguồn đã kiểm tra

- `ukui-control-center_4.24.0.0-ok2.8.tar.xz` tại kho upstream được ghim trong
  `scripts/build_control_center_candidate.sh`.
- SHA256 đã kiểm tra:
  `6810d2ec5f4b186b6473206566270c5537605f1adc912b5a7199a91b2f0ed508`.
- Đối chiếu cả nguồn gốc và cây áp dụng lần lượt `about-network.patch`,
  `about-startup.patch`, `privacy.patch`. Những điểm trong shell bên dưới vẫn
  tồn tại sau ba bản vá này.
- Các số dòng dưới đây thuộc cây sau ba bản vá, không phải dòng trong file patch.

## Phát hiện chính: About chưa phải bước đầu tiên

Luồng khởi động xác định từ mã:

```text
main() -> MainWindow::MainWindow()
         -> preInit()
            -> new SearchWidget()
               -> initExcludeSearch() -> isExitBattery()
               -> new QDBusInterface(... /Shortcut ...)
            -> getModuleHideStatus()

main() -> initPlugins() -> show() -> timer 10 ms
         -> closePrescene()
            -> setupUi()
            -> loadAllModules()
               -> loadPlugins()
               -> loadSearchXml() -> setLanguage() -> loadxml()
            -> initPageWidget() -> initPageWidgetSlot()
               -> initUI()
               -> HomePageWidget()
               -> Font interface
               -> xử lý đối số -m và chọn plugin được yêu cầu
```

Do đó, mở thẳng một trang bằng `-m` vẫn đi qua khởi tạo shell và chỉ mục tìm kiếm.
Cửa sổ đã được `show()` trước `loadSearchXml()` và trước trang được yêu cầu.
Nếu luồng giao diện chờ dịch vụ ở các bước đó, người dùng có thể thấy cửa sổ
trắng/không phản hồi mà About chưa chạy. Đây là cơ chế phù hợp với triệu chứng,
không phải bằng chứng xác nhận chính hàm đó đang chặn PID trong ảnh.

## Các điểm chặn được xác nhận trong mã

| Vị trí | Thao tác trên luồng giao diện | Hệ quả khi backend chậm hoặc không trả lời |
|---|---|---|
| `shell/searchwidget.cpp:76, 976` | Constructor gọi `initExcludeSearch()`, rồi `isExitBattery()` | Khởi động ô tìm kiếm phụ thuộc UPower dù người dùng chỉ mở About. |
| `libukcc/interface/ukcccommon.cpp:273` | Tạo interface UPower và gọi `Get(...PowerSupply)` đồng bộ | Chờ introspection/phản hồi; không có thời hạn riêng tại vị trí gọi. |
| `shell/searchwidget.cpp:107` | Constructor tạo `QDBusInterface` cho `/Shortcut` | Có thể chờ introspection trước cả khi gọi phương thức. |
| `shell/searchwidget.cpp:363` | `loadxml()` tạo interface và gọi `isSupportHostLightStrip` đồng bộ | Chặn lúc dựng chỉ mục, trước khi chọn About. |
| `shell/searchwidget.cpp:428` | `getUnsupportTranslation` gọi vào `com.ksc.defender` | Phụ thuộc dịch vụ bảo mật ngoài About; truy vấn vẫn chạy dù `isKscDefender` là false. |
| `shell/searchwidget.cpp:443` | Gọi lại `isExitBattery()` | UPower bị truy vấn thêm một lần trong giai đoạn nạp chỉ mục. |
| `shell/searchwidget.cpp:698` | Hai lệnh đồng bộ `getSystemShortcut`, `getWindowShortcut` | Nạp chỉ mục có thể tiếp tục chờ session service. |
| `shell/mainwindow.cpp:454, 617` | Tạo interface Font/system, rồi mới gọi `asyncCall()` | Phương thức bất đồng bộ không loại bỏ bước tạo interface đồng bộ trước đó. |
| `shell/mainwindow.cpp:709` | Tạo interface statusmanager và gọi `get_current_tabletmode` đồng bộ | Có thêm điểm chờ trong `initUI()`. |
| `libukcc/interface/ukcccommon.cpp:58` | `connection.call(...QDBus::Block, 3000)` lấy chính sách module | Có giới hạn 3 giây nhưng vẫn chặn; được gọi từ preInit, HomePage và ModulePage. |

Qt xác định `QDBusConnection::call()` là thao tác chờ phản hồi và
`asyncCall()` trả về ngay; thời hạn mặc định của call thường khoảng 25 giây.
Không được hiểu rằng dịch vụ vắng mặt luôn làm chờ đủ thời gian này: lỗi
ServiceUnknown/UnknownMethod có thể trả ngay. Dịch vụ đã đăng ký nhưng bị kẹt
mới là tình huống cần tái hiện.
Nguồn: [Qt D-Bus — call/asyncCall](https://doc.qt.io/qt-6/qdbusconnection.html#call).
Nguồn dự án dùng Qt 5; không suy ra thời gian treo thực tế của máy từ tài liệu Qt 6.

## Vì sao bản vá trước chưa đủ

- Các bản vá About xử lý truy vấn thuộc plugin About, không xử lý các probe
  đồng bộ trong `SearchWidget` và `MainWindow` nêu trên.
- Bản vá riêng tư bỏ đường telemetry/SSO và dịch vụ tương ứng. Nó không thay
  thế các truy vấn UPower, shortcut, statusmanager, Font hay security filter.
- `getHostName()` trong About còn chạy `hostname` và `waitForFinished()`;
  `getCpuArchitecture()` trong tìm kiếm chạy `lscpu` và chờ tiến trình. Đây là
  các điểm chặn bổ sung, chưa có bằng chứng chúng là thủ phạm trên máy người dùng.
- `netDate` của nguồn gốc được đọc bởi `compareTime()`, chủ yếu từ luồng xem
  thông tin kích hoạt. Chưa có bằng chứng rằng NTP gây treo ở lần mở Properties
  trong ảnh. Không nên coi việc đổi máy chủ NTP là xác nhận sửa lỗi cửa sổ trắng.
- `tests/qt/about-startup.cpp` kiểm tra helper D-Bus bất đồng bộ; nó không tạo
  `MainWindow` hoặc `SearchWidget`. Test đó không chứng minh luồng mở Properties
  đầy đủ còn phản hồi.

## Phạm vi bản vá `shell-startup.patch`

1. Tách probe dịch vụ tùy chọn khỏi constructor và `loadxml()`. Nạp XML cục bộ
   trước; lấy khả năng phần cứng và danh sách phím tắt bằng message bất đồng bộ,
   có thời hạn, cập nhật cache/model khi có phản hồi.
2. Bỏ tạo `QDBusInterface` trên đường khởi động chỉ để gửi lời gọi bất đồng bộ;
   dùng message trực tiếp cho Font, disk preload và tablet mode. Giữ đăng ký
   tín hiệu tablet mode và hành vi khi backend sẵn sàng.
3. Tránh gọi lặp chính sách module theo kiểu chặn. Nếu dùng cache/prefetch,
   phải giữ cập nhật chính sách và cách xử lý hạn chế quyền; không thay toàn bộ
   chính sách bằng map rỗng chỉ để mở giao diện nhanh.
4. Kiểm thử chính đường mở Settings với backend trả bình thường, backend vắng
   mặt và backend có tên D-Bus nhưng không trả lời, cả mở thường và `-m About`.
   Phải đo heartbeat/khả năng xử lý sự kiện của cửa sổ, không chỉ thời gian build.

## Kết luận và giới hạn

Đã xác nhận nhiều thao tác IPC đồng bộ trên luồng giao diện trước khi vào About.
Đây là lỗi thiết kế về khả năng phản hồi và là nhóm nghi phạm ưu tiên cao cho
triệu chứng trong ảnh. `shell-startup.patch` thay các probe tìm kiếm bằng cache
cập nhật bất đồng bộ, lấy chính sách trước khi dựng trang và chia sẻ kết quả
cho shell/libukcc; bỏ introspection đồng bộ ở disk/font/tablet preload.

Rà tiếp phía backend phát hiện constructor `ukccSessionServer` gọi
`monitoFileChanged()` → `GetSecurityConfigPath()` → interface/call đồng bộ tới
Settings Daemon. `getModuleHideStatus()` cũng lặp lại truy vấn đó khi chưa có
đường dẫn USD. Bản vá thêm `SecurityPathProvider` có thời hạn 1,5 giây, gộp các
yêu cầu đồng thời và trả D-Bus trễ thay vì chặn session service. Chính sách vẫn
đọc theo thứ tự USD → user → system, giữ đường dẫn đã biết qua lỗi backend và
làm mới khi có tín hiệu cấu hình hoặc service owner đổi.

Qt test mới `security-path.cpp` kiểm tra các trường hợp trên bằng tiến trình
backend riêng. Test helper cũ vẫn kiểm tra deadline 2 giây, phản hồi sai kiểu và
hủy context. Các test Linux được gắn vào job build; môi trường Windows không
chạy được desktop UKUI để xác nhận trực tiếp triệu chứng của PID trong ảnh.

Build #49 (`42367044424`, commit `3a550c7`) dừng tại qmake với
`Project ERROR: kysdk-datacollect development package not found`. Nguyên nhân
độc lập với lỗi runtime: `libukcc/interface.pri` còn dòng PKGCONFIG của SDK.
Bản vá xóa dòng này; script build kiểm tra cả `.pro` lẫn `.pri` trước biên dịch.

Chưa xác định được hàm chính xác chặn PID 4414 từ backtrace; bản vá xử lý các
đường chặn đã xác nhận trong mã và chưa được coi là chứng nhận boot/desktop.
