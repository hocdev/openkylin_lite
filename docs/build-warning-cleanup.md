# Sửa cảnh báo build #63

Nguồn đối chiếu: [Actions #63](https://github.com/hocdev/openkylin_lite/actions/runs/42456950251), commit `dc96e958f6f36d5f346c85a008ab2b309462392a`.

Yêu cầu: sửa toàn bộ cảnh báo build, giữ Firefox và tiếp tục gỡ AI hệ thống. Đợt sửa được kiểm thử trên nhánh `codex/build-warning-cleanup`; chưa được coi là đã sạch cảnh báo hoặc đã đạt kiểm thử desktop.

## Những thay đổi đã đưa vào nguồn

- Installer: định nghĩa kết quả cho các nhánh thiếu return, trả 0 cho child index của list model, trả nullptr khi không có control được focus, sửa phép so sánh bị dùng nhầm thay cho gán GPT và định dạng QString khi ghi lỗi mật khẩu. Khai báo boolean trùng tên `syncUdev` không được biến thành một lời gọi có tác dụng phụ mới. PluginService liên kết trực tiếp yaml-cpp mà nó sử dụng.
- Greeter/screensaver: kiểm tra SDK ngày giờ trả nullptr, giải phóng kết quả khi loại ngày giờ không được hỗ trợ, kết quả xác định cho các nhánh thiếu return, kết thúc đọc DBus array đúng thứ tự. Greeter sửa memset đảo tham số, giới hạn strnlen theo kích thước buffer, khởi tạo tham số biến đổi XRandR và sửa header guard.
- Scanner: tránh truy cập danh sách với index chưa khởi tạo, khởi tạo con trỏ đầu ra SANE bằng nullptr thay cho memset nhầm sizeof con trỏ, sửa phép gán kép và dùng range thực tế khi nhận diện kích thước A2.
- Settings: giá trị mặc định blur không đọc chính biến chưa khởi tạo; con trỏ GFileInfo được khởi tạo; chuỗi lỗi được kiểm tra nội dung thay vì so sánh địa chỉ.
- Photo Viewer: định nghĩa fallback cho các nhánh return còn thiếu (bao gồm nhánh UNUI của test), kiểm tra schema theme trước khi dùng QGSettings, tránh giữ pointer tới QByteArray tạm, khởi tạo trạng thái định dạng/TIFF/crop và xử lý rõ event/format không thuộc nhóm được xử lý riêng.
- Thay API Qt/STL đã lỗi thời bằng API tương đương: QTransform, horizontalAdvance chỉ trên QFontMetrics, Qt::SkipEmptyParts, Qt::endl/hex, idClicked/idToggled, textActivated, std::sort, lambda predicates và API thời lượng TagLib tính bằng giây. Callback dùng Q_UNUSED trong thân hàm để giữ nguyên tên/chữ ký và tương thích Qt 5 MOC; không thêm thuộc tính vào kiểu tham số mà MOC xử lý.
- Sắp xếp initializer list của 39 constructor theo thứ tự khai báo, giữ nguyên thứ tự khởi tạo thực tế mà C++ đã quy định. Bỏ các binding local không dùng khi vẫn giữ lời gọi tạo menu, mở dialog và các tác dụng phụ cần thiết.
- Search: ghi đủ các trường header cache, xử lý EINTR/short write và loại bỏ file tạm riêng khi ghi thất bại. Không công bố cache lỗi. Bổ sung test mô phỏng ghi ngắn, bị ngắt, hết dung lượng và write trả 0; đóng gói các file cấu hình dịch vụ và symlink development từng bị dh_missing báo bỏ sót.
- Orca: bỏ shlibs substvar của gói Python không còn module native AI, không sinh GNOME version substvars không được sử dụng, bỏ yêu cầu ngôn ngữ C/C++ dư trong Meson. Giữ nguyên SVG symbolic vì Scour thay đổi hình raster vượt ngưỡng; các SVG khác vẫn được tối ưu. Chuyển 10 thông báo nhiều tham số và các bên gọi sang mapping có tên, đồng thời chuyển các mục dịch có sẵn; giữ nguyên các mục fuzzy chưa hoạt động.
- Dùng quy tắc GTK Builder upstream cụ thể khi trích xuất bản dịch Orca; khai báo rõ policy không khởi chạy dịch vụ trong container build.

## Kiểm chứng và phần còn phải xác minh

Các patch trong `patches/build-warnings/` được áp dụng sau patch gỡ AI/password-only/installer hiện có. Đã kiểm tra chúng với cây nguồn khớp phiên bản. Test Python chạy cục bộ; test C++ dùng Qt và UBSan được cấu hình chạy trong container. Build #64 đã chạy đạt hai test thực tế cho fallback installer và lỗi SDK ngày giờ greeter; Orca build thành công với 0 warning trong báo cáo. Những kết quả này không chứng minh các job khác đã sạch cảnh báo.

Mỗi job build lưu nguyên log và `warnings.json` vào artifact `build-warnings-*`. Bộ thu thập giữ mã thoát thật của build và không tắt lớp cảnh báo compiler. Cần đọc artifact của build mới để xác định chính xác cảnh báo còn lại. Chưa tuyên bố đã sửa hết cảnh báo upstream về OpenSSL, QDesktopWidget, constructor order, unused locals hoặc công cụ build; không thay đổi diện rộng các API này khi chưa có bản build đối chiếu.

Chưa boot/cài VM, chưa xác minh đăng nhập, khóa màn hình, phân vùng, Settings, Orca, clipboard, Peony và Photo Viewer trên ISO mới. Các thay đổi cleanup không thay thế bước xác minh đó.
