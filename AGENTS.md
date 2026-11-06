# Nguyên tắc build ISO

- Mỗi push vào nhánh được cấu hình build phải khởi chạy workflow ISO cho commit mới. Dùng cùng nhóm concurrency `openkylin-lite` với `cancel-in-progress: true` để hủy lượt build cũ đang chạy hoặc đang chờ.
- Giữ ISO gốc trong GitHub Actions cache với khóa ổn định theo SHA256 của ISO. Khôi phục và kiểm tra SHA256 trước khi dùng. Chỉ tải lại từ upstream khi cache không có hoặc ISO khôi phục không khớp SHA256. Lưu cache ngay sau khi xác minh ISO gốc, trước khi remaster. Các bước dọn build chỉ dọn dữ liệu tạm và đầu ra.
