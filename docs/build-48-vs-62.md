# Đối chiếu ISO #48 và #62

Kiểm tra ngày 08/11/2026 từ log Actions và artifact inspection của cả hai lượt:

- [#48](https://github.com/hocdev/openkylin_lite/actions/runs/42352234655): `eecd65b3ea324644c124408b44f42c0dff6c577c`, success, 3.962.372.096 byte.
- [#62](https://github.com/hocdev/openkylin_lite/actions/runs/42398315311): `4cfa3f680a8bf57240558427d1c8aace97b8193e`, success, 3.933.077.504 byte.

## Kết quả có bằng chứng

Manifest Live và OSTree đều cho thấy #62 gỡ thêm 21 gói: `kylin-daq`, 12 thư viện AI/OCR/ONNX/OpenCV, ba plugin/dịch vụ Peony thông minh, bốn gói Tesseract và `ukui-voice-wing`. Thêm năm gói eSpeak NG/audio để thay backend AI của Orca. Desktop liên quan được build lại từ nguồn khóa phiên bản, không ép bỏ Depends.

Các báo cáo `unexpected-removals.txt` và `dpkg-audit.txt` của hai cây #62 đều rỗng. APT check thành công; OSTree fsck thành công. Không thấy bằng chứng APT gỡ nhầm desktop qua các manifest đã đối chiếu. #62 nhỏ hơn #48 29.294.592 byte.

Các chức năng mất có chủ đích: OCR/tìm chữ trong ảnh, tìm kiếm ngữ nghĩa, plugin quản lý dữ liệu thông minh, nhập liệu giọng nói AI và backend giọng nói Kylin/Xunfei. Orca chuyển sang eSpeak NG nên giọng đọc thay đổi. Các bản vá giữ đường xem ảnh, tìm tên file/ứng dụng và clipboard thông thường, nhưng build/dependency checks không chứng minh các đường này chạy đúng khi đăng nhập.

## Lỗ hổng kiểm tra và phạm vi đã thống nhất

#62 bỏ qua mọi thư mục có tên `net.mozilla.firefox`, đồng thời chỉ quét `usr`, `opt`, `etc`. Inventory đặt Firefox tại `var/opt/apps/net.mozilla.firefox`; dữ liệu ứng dụng dưới `/var/opt` và `/var/lib` chưa được kiểm tra. Runtime độc lập cũng có thể không có NEEDED trỏ tới chính nó, nên cần kiểm tra tên payload.

Đã sửa kiểm tra để quét thêm hai vùng dữ liệu đó, phát hiện tên runtime độc lập và chỉ miễn đúng hai đường dẫn cài Firefox. Candidate `.deb` không được hưởng ngoại lệ trình duyệt. Test hồi quy kiểm tra mô hình trong `/var/opt`, thư mục giả tên Firefox và runtime độc lập.

Người dùng chọn **giữ Firefox, chỉ gỡ AI hệ thống**. Vì Firefox giữ runtime dịch riêng, không mô tả ISO là không chứa bất kỳ mã AI nào. Các báo cáo #62 cũ không được xem là kết quả của kiểm tra mới; phải build lại để kiểm tra vùng payload bổ sung.

## Giới hạn xác minh

Chưa boot ISO hoặc cài VM BIOS/UEFI. Chưa xác minh trực tiếp đăng nhập, panel/menu/search, Peony, copy/paste văn bản/ảnh, xem ảnh, quét ảnh, Settings và Orca sau cài đặt/reboot. Vì vậy chưa thể kết luận #62 không gây lỗi runtime. Sửa kiểm tra và unit tests tại máy Windows không thay cho remaster Linux và kiểm thử VM.
