# openKylin Lite qua GitHub Actions

Nguồn cố định: `openKylin-Desktop-V3.0-20260918-x86_64.iso` (7.647.188.992 byte, khoảng 7,12 GiB).

## Khả năng chạy miễn phí

- Repository public + runner Ubuntu tiêu chuẩn: compute miễn phí. Runner public Ubuntu có 4 CPU, 16 GB RAM, nhưng chỉ công bố 14 GB SSD. RAM không phải vấn đề chính; ổ đĩa mới là giới hạn.
- Dùng OverlayFS để đọc trực tiếp squashfs gốc, chỉ ghi file thay đổi; không giải nén toàn bộ rootfs. Dọn lớp thay đổi ngay sau khi nén. Đỉnh dung lượng vẫn gồm ISO gốc + squashfs mới + ISO mới, nên 14 GB chưa được bảo đảm đủ. Không còn yêu cầu cố định 60 GiB.
- Chế độ inspect cần ít nhất 10 GiB trống. Build đã bỏ ngưỡng cứng 35 GiB và ghi dung lượng từng giai đoạn vào disk-stages.txt. Nếu hết dung lượng, job sẽ dừng; cần dùng kết quả thực tế để quyết định đổi runner. Workflow không tự xóa SDK trên runner.
- GitHub Free cho repository private hiện có $12 compute/tháng, tương đương khoảng 2.000 phút Linux chuẩn ở mức $0,006/phút, và 500 MB artifact dùng chung với Packages. Chưa kiểm tra mức sử dụng còn lại của tài khoản cụ thể.
- Không upload ISO nhiều GB vào Actions artifacts. Chỉ upload báo cáo nhỏ trong 3 ngày. ISO được chia thành phần 1.900 MiB và đưa vào **draft Release**. GitHub giới hạn mỗi release asset dưới 2 GiB, không giới hạn tổng dung lượng release hay băng thông theo tài liệu hiện tại.
- Nếu runner tiêu chuẩn thiếu ổ đĩa, đổi `runs-on` sang `[self-hosted, linux, x64]` trên máy Linux có sudo, hỗ trợ OverlayFS và đủ dung lượng theo báo cáo thực tế. Self-hosted không tính phí Actions compute theo tài liệu hiện tại; chi phí máy/điện/mạng do bạn chịu.

Nguồn kiểm tra ngày 06/11/2026:

- [ISO upstream](https://releases.openkylin.top/3.0/)
- [Thông số runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Giới hạn Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

## Sử dụng

Quy tắc ổn định bổ sung: xem [config/README.md](config/README.md). Mỗi gói xóa phải có phiên bản và lý do được ghi trong `config/reviewed-apps.json`; script xác minh launcher thuộc gói đó và đối chiếu thay đổi gói thực tế sau purge. Không xóa app theo ngôn ngữ hoặc tên nhà phát triển.

1. Đưa thư mục này lên repository GitHub, nên dùng public nếu muốn compute miễn phí.
2. Mở **Actions → openKylin Lite → Run workflow → inspect**.
3. Tải báo cáo: `packages.tsv` liệt kê gói theo dung lượng giảm dần; `iso-files.tsv` liệt kê file ISO; `desktop-files.txt` liệt kê launcher. Kiểm tra `disk-before.txt` và summary để biết dung lượng thực tế.
4. Điền tên gói chính xác vào `config/remove-packages.txt`, commit rồi chạy lại với `mode=build`. Phải cung cấp SHA256 đáng tin cậy của ISO gốc, lấy từ nguồn upstream hoặc xác minh độc lập. Hash workflow tính lần đầu chỉ là dấu vân tay, không tự chứng minh tính xác thực.
5. Nếu build thành công, tải các phần ISO và checksum từ draft Release. Draft không tự xuất bản công khai.

Không coi mọi gói `kylin-*`, `ukui-*` hoặc gói do Trung Quốc phát triển là app cần xóa: chúng có thể là desktop, trình cài đặt hoặc thư viện hệ thống. Cần xác định từng app không muốn giữ qua inventory. Danh sách xóa hiện để trống vì chưa đọc nội dung ISO; không phỏng đoán tên gói QQ/WeChat/WPS.

Script mô phỏng purge trước, chặn việc kéo theo gói ngoài danh sách, chặn một số nhóm hệ thống và gói Essential, không autoremove. Đây không phải bảo đảm desktop vẫn hoạt động. Có thể giảm thêm bằng việc bỏ app lớn không cần dùng sau khi xem báo cáo; chưa tự xóa font/ngôn ngữ/driver để tránh làm hỏng trải nghiệm cài đặt.

Build dùng XZ cho squashfs và replay boot từ ISO gốc qua xorriso. Hiện chỉ hỗ trợ ISO có đúng một squashfs và không có manifest phụ của installer; cấu trúc khác sẽ dừng để xử lý riêng. Không tự xóa kho `.deb` trên ISO vì trình cài có thể cần chúng. Không tạo lại chữ ký upstream cho nội dung đã sửa.

## Ghép lại ISO

Linux, trong thư mục chứa các phần:

```bash
sha256sum -c PARTS-SHA256SUMS
cat lite.iso.part-* > lite.iso
sha256sum -c SHA256SUMS
```

Windows PowerShell:

```powershell
$parts = Get-ChildItem -File lite.iso.part-* | Sort-Object Name
$dest = [System.IO.File]::Create((Join-Path $PWD 'lite.iso'))
try {
    foreach ($part in $parts) {
        $src = [System.IO.File]::OpenRead($part.FullName)
        try { $src.CopyTo($dest) } finally { $src.Dispose() }
    }
} finally { $dest.Dispose() }
Get-FileHash .\lite.iso -Algorithm SHA256
# So sánh với SHA256SUMS trước khi ghi USB.
```

## Trạng thái xác minh

Chưa chạy workflow trên GitHub, chưa giải nén ISO, chưa đo dung lượng sau khi xóa app. Máy soạn thảo hiện là Windows không có Bash/Git khả dụng. Workflow chạy ShellCheck trước khi thực thi script. Kiểm tra đóng gói mount ISO đầu ra rồi so sánh trực tiếp squashfs mới, không tạo thêm bản trích trên ổ đĩa, ghi báo cáo boot và yêu cầu ISO nhỏ hơn nguồn. Vẫn cần boot thử BIOS/UEFI và cài thử trong VM trước khi dùng thật; chưa có kết quả xác nhận boot hoặc Secure Boot.

## Giải phóng dung lượng theo giai đoạn

1. Mount squashfs chỉ đọc + OverlayFS, thay cho giải nén toàn bộ.
2. Nén xong: unmount overlay và xóa lớp file thay đổi.
3. Tạo ISO mới xong: unmount và xóa ISO gốc ngay.
4. So sánh squashfs trực tiếp qua mount ISO mới, rồi xóa squashfs trung gian.
5. Chia từng phần 1.900 MiB, upload vào draft Release rồi xóa phần đó trước khi tạo phần tiếp theo. Chỉ giữ ISO mới + tối đa một phần upload.
6. Upload hoàn tất hoặc lỗi: xóa ISO mới và thư mục tạm. Upload lỗi có thể để lại draft Release chưa đủ phần; chạy lại workflow để tạo draft mới.

Đỉnh dung lượng ở bước tạo ISO vẫn tồn tại: ISO gốc + squashfs mới + ISO mới. OverlayFS không giải phóng dữ liệu gốc chỉ vì app đã bị xóa; phần đó chỉ biến mất trong squashfs mới. Chưa đo đỉnh dung lượng bằng lần chạy thật.

