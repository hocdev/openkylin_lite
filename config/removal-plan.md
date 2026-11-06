# Danh sách gỡ WPS và AI của ISO 20260918

Đã được người dùng chấp thuận: bỏ WPS, nhóm AI và đặc biệt `kylin-aiassistant`.

Danh sách thực thi là `remove-packages.txt` (69 gói); phiên bản và lý do của từng gói nằm trong `reviewed-apps.json`, lấy từ artifact kiểm kê thành công của chính ISO nguồn.

- Gỡ `wps-office`, `kylin-aiassistant`, `kylin-bot`.
- Gỡ môi trường Python riêng của AI, mô hình OCR/giọng nói/ảnh/embedding và dịch vụ AI.
- Gỡ `kolourpaint`: bản openKylin này phụ thuộc trực tiếp vào `kylin-aiassistant`, nên không thể giữ nó khi gỡ trợ lý bằng APT mà vẫn bảo toàn phụ thuộc.
- Gỡ thêm backend Kytensor/LLM/ONNX, SDK AI riêng và các plugin Baidu/Xunfei/Qwen/DeepSeek/custom/freetrial đã xác định. Chỉ các tên cụ thể trong danh sách được phép gỡ; không xóa thư viện theo wildcard.
- Giữ kernel, firmware, UKUI, trình cài đặt, mạng/âm thanh/hiển thị, font, bộ gõ và các thư viện dùng chung khác.

Các gói AI không có launcher có ngoại lệ được giới hạn theo tên và phiên bản cụ thể. Gói Essential/Protected vẫn bị chặn; chỉ một số file systemd user/polkit của chính AI đã đọc từ inventory được phép biến mất. Nếu gặp file tích hợp hệ thống khác, phải dừng và kiểm tra.

APT mô phỏng trước, không autoremove; gói ngoài danh sách bị kéo theo sẽ làm job dừng. Sau purge, so sánh toàn bộ gói đã cài và phiên bản. ISO vượt 4.000.000.000 byte không được upload. Kết quả chỉ là draft Release, cần boot/cài thử trước khi dùng thật.

Mỗi push lên main hiện kiểm kê danh sách này và xác minh tag nguồn Gitee; chỉ mode build chạy thủ công mới gỡ gói/đóng gói ISO. ISO nguồn được lấy lại từ cache nếu có. Chưa có bản vá hoặc build lại desktop bỏ AI; các ngoại lệ còn giữ phải được xử lý bằng nguồn đã khóa trước khi có thể công bố ISO sạch AI.

## Ngoại lệ bắt buộc để giữ desktop

Còn 7 thư viện dùng chung có phụ thuộc cứng từ UKUI, clipboard, trình quản lý file, photo viewer hoặc trợ năng. Chi tiết từng thư viện và gói cần nó được lưu trong `retained-ai-dependencies.json`. Không được gỡ bằng cách bỏ qua phụ thuộc. Muốn loại bỏ cả các ABI này cần sửa và build lại ứng dụng/desktop liên quan; ISO hiện không được mô tả là hoàn toàn không còn mã AI.
