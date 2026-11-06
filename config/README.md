# Quy tắc chọn ứng dụng để xóa

Chỉ chọn ứng dụng người dùng không cần giữ, sau khi đối chiếu inventory của đúng ISO. Tiếng Trung hoặc nguồn gốc nhà phát triển không xác định ứng dụng có cần thiết cho hệ thống hay không.

Mỗi tên gói trong `remove-packages.txt` phải có mục tương ứng trong `reviewed-apps.json`, ví dụ minh họa (không phải tên gói thực đã xác nhận):

```json
{
  "example-chat-app": {
    "version": "1.2.3-1",
    "reason": "Ứng dụng chat cài sẵn không cần sử dụng",
    "desktop": "/usr/share/applications/example-chat.desktop"
  }
}
```

Phiên bản phải trùng hoàn toàn. Launcher phải thuộc chính gói đó. Script chỉ chấp nhận gói optional/extra; chặn Essential, Protected, nhóm hệ thống, thư viện, kernel, desktop, trình cài đặt, driver, font và bộ gõ. Quy tắc cố ý bảo thủ: nếu bị chặn, giữ ứng dụng lại để xem xét riêng.

APT mô phỏng purge và dừng nếu cần xóa thêm gói ngoài danh sách. Không autoremove, không đổi kho phần mềm, không nâng cấp gói. Sau purge, đối chiếu toàn bộ danh sách gói: chỉ các gói được chọn được phép biến mất; không được thêm gói hoặc đổi phiên bản gói còn lại. apt-get check và dpkg --audit phải thành công cả trước và sau.

Các kiểm tra này giảm nguy cơ xóa nhầm, không xác nhận được tác động của mọi maintainer script hoặc tương tác khi chạy thực tế. ISO chỉ nằm trong draft Release cho đến khi kiểm tra:

- Boot live BIOS và UEFI; đăng nhập UKUI, mở terminal và trình quản lý file.
- Mạng, âm thanh, hiển thị, bộ gõ và trình quản lý phần mềm.
- Cài đặt vào ổ đĩa máy ảo trống; khởi động lại từ hệ điều hành đã cài.
- Xem dịch vụ lỗi và kiểm tra cập nhật/phụ thuộc sau khi cài.

Chưa có inventory thật nên hai danh sách hiện trống; chưa ứng dụng nào được xác nhận hoặc bị xóa.
