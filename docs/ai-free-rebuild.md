# Tách AI bằng cách build lại các thành phần desktop

Mục tiêu: giữ chức năng desktop cơ bản nhưng loại bỏ SDK AI dùng chung còn bị liên kết. Chưa có bản build hoặc bản vá nguồn được xác minh; tài liệu này ghi kết quả khảo sát, không phải cam kết tương thích.

## Kết quả Gitee cập nhật

Ngày 06/11/2026 đã dùng `git ls-remote --tags` xác nhận đủ tag build khớp chính xác phiên bản ISO cho bảy source package: ukui-search, ukui-clipboard, kylin-photo-viewer, peony-extensions, orca, ukui-voice-wing và kolourpaint. Commit được khóa trong `config/rebuild-sources.json`. Đã đọc changelog ở commit đã khóa của search và clipboard; changelog nhánh Photo Viewer cũng có đúng bản ISO.

Kết quả này giải quyết vấn đề GitHub mirror cũ nêu bên dưới: có thể chọn đúng bản gốc trên Gitee, không cần hạ phiên bản. Tuy nhiên, tag khớp không chứng minh bản vá bỏ AI sẽ giữ ABI hoặc chức năng desktop; vẫn cần build và kiểm thử.

## Phát hiện từ mã nguồn

- `openkylin/ukui-search`, nhánh `openkylin/nile`, commit `55477116e5d256493ee9faa7adb09a12d1521149`: `libsearch/CMakeLists.txt` yêu cầu `kylin-ai-base`, đưa `index/ai-indexer.cpp` và `aisearch/ai-search-plugin.cpp` vào thư viện. `ai-indexer.cpp` gọi API data-management của AI. Phải tách đăng ký plugin, các lời gọi AI và mục link/build, đồng thời giữ tìm kiếm tên file/ứng dụng và ABI công khai cần cho panel/menu/Peony.
- `openkylin/kylin-photo-viewer`, nhánh `openkylin/ai`, commit `2dca359cf1655ecbda5d0a7642f7fad053023a43`: `debian/control` khai báo ONNX, OCR và plugin AI riêng. Tree chứa model `.onnx`, plugin `photo-viewer-aiassistant-plugin` và các file OCR. Cần tách UI OCR/matting/enhancement khỏi đường mở/xem ảnh thông thường và sửa packaging.
- `openkylin/ukui-clipboard` có nguồn nhưng `master` không có cây build đầy đủ; nhánh distro cần được chọn rõ. Không thể lấy mặc định `master` để build thay gói hiện tại.

Nguồn đã đọc:

- https://github.com/openkylin/ukui-search/blob/openkylin/nile/libsearch/CMakeLists.txt
- https://github.com/openkylin/ukui-search/blob/openkylin/nile/libsearch/index/ai-indexer.cpp
- https://github.com/openkylin/kylin-photo-viewer/blob/openkylin/ai/debian/control
- https://github.com/openkylin/ukui-clipboard/blob/openkylin/huanghe/debian/changelog

## Khớp phiên bản trước khi build

| Thành phần | Bản trong ISO | Bản nhánh GitHub đã đọc |
|---|---|---|
| ukui-search | 4.24.0.0-ok0.2 | huanghe: 4.20.0.7-ok0.1; nile: 4.10.14.0-ok0.10 |
| ukui-clipboard | 2.0.0.0-ok0.17 | huanghe: 2.0.0.0-ok0.1 |
| kylin-photo-viewer | 1.3.0.3-ok22.56 | openkylin/ai: 1.3.0.3-ok21.31 |

Các nhánh này cung cấp bằng chứng cách tích hợp AI, nhưng chưa phải nguồn khớp chính xác ISO 20260918. Ưu tiên lấy source package đúng phiên bản từ kho APT mà ISO sử dụng; GitHub/Gitee là nguồn bổ sung và phải pin commit. Không hạ phiên bản thư viện desktop chỉ để tránh AI.

## Chuỗi gói cần sửa

- ukui-search và libukui-search2: bỏ tìm kiếm/lập chỉ mục AI, giữ API desktop còn lại.
- ukui-clipboard: bỏ nhận dạng hình ảnh/AI, giữ copy/paste và lịch sử clipboard.
- peony-extensions: tách dịch vụ/plugin quản lý dữ liệu thông minh khỏi các extension file manager thông thường.
- kylin-photo-viewer: bỏ OCR/ONNX/plugin AI, giữ mở/xem ảnh.
- orca và ukui-voice-wing: kiểm tra cầu nối Kylin AI speech; bảo toàn chức năng trợ năng và speech backend thông thường khi có thể.
- kolourpaint: có thể build lại không tích hợp trợ lý để giữ ứng dụng; phương án purge hiện tại cần gỡ do phụ thuộc cứng.

Phải sửa bên gọi và liên kết phụ thuộc. Không thay SDK bằng thư viện rỗng mang cùng tên, không dùng `dpkg --force-depends`, không chỉ sửa chuỗi Depends trong control.

## Điều kiện chấp nhận

Build trong môi trường openKylin tương ứng, tạo `.deb` có version suffix riêng; kiểm tra ABI/symbol của thư viện desktop được giữ, Depends và NEEDED bằng dpkg-shlibdeps/readelf. Xác nhận không còn liên kết tới bảy SDK AI còn giữ trong `config/retained-ai-dependencies.json`. Chỉ sau đó mới gỡ chúng bằng APT và chạy lại apt-get check/dpkg audit.

Boot thử BIOS/UEFI, login, panel/menu/search, Peony, copy/paste văn bản/ảnh, photo viewer và trợ năng; cài VM rồi khởi động lại. Build thành công hoặc ISO nhỏ hơn 4 GB không tự chứng minh các chức năng này hoạt động.
