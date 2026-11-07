# openKylin Lite qua GitHub Actions

## Cập nhật quy trình

- ISO gốc được giữ trong Actions cache theo SHA256 cố định, dùng chung giữa các push. Kiểm tra hash mỗi lần restore; chỉ tải lại upstream khi cache miss hoặc file hỏng. Cache có thể bị GitHub thu hồi khi lâu không dùng hoặc hết quota, nên không phải lưu trữ vĩnh viễn. Một ISO chiếm khoảng 7,12 GiB trong quota cache 10 GiB; không tạo cache mới theo từng commit.
- Cache được lưu ngay sau tải/xác minh, trước remaster, nên lỗi build sau đó không làm mất bản gốc đã cache. Dữ liệu tạm vẫn được dọn; ISO gốc cache được giữ lại theo yêu cầu.
- Dùng `actions/checkout@v6`, `actions/upload-artifact@v6` và `actions/cache/{restore,save}@v5`, đều chạy Node.js 24.
- SHA256 mặc định là dấu vân tay từ lượt kiểm kê thành công, không phải chữ ký xác thực upstream. Có thể cung cấp hash đã xác minh độc lập khi chạy thủ công.

Nguồn cố định: `openKylin-Desktop-V3.0-20260918-x86_64.iso` (7.647.188.992 byte, khoảng 7,12 GiB).

Mục tiêu: **3–4 GB thập phân**, tối đa 4.000.000.000 byte (khoảng 3,73 GiB), giảm khoảng 48–61% so với nguồn. Cấu hình tại `config/size-target.json`. Nhỏ hơn 3 GB vẫn được chấp nhận, không chèn dữ liệu cho đủ dung lượng. Build vượt 4 GB sẽ dừng trước upload ISO; xem `size-result.txt`. Inspect xuất `size-budget.txt` để phân biệt squashfs và phần còn lại trên ISO. Chưa xác nhận có thể đạt mục tiêu chỉ bằng xóa app tùy chọn; ưu tiên ổn định, giữ desktop/trình cài đặt/driver/font/bộ gõ.

## Sửa installer và Properties/About (sau build #45)

- Sửa tiếp luồng khởi động Settings bằng `shell-startup.patch`: constructor/tìm kiếm không chờ UPower, security filter hoặc shortcut; preload disk/font và tablet mode dùng message bất đồng bộ trực tiếp. Chính sách module được lấy trước khi dựng trang, cache dùng chung trong ứng dụng và làm mới khi cấu hình/service owner đổi. Session service lấy đường dẫn chính sách USD bất đồng bộ, gộp yêu cầu đang chờ và giữ đường dẫn hợp lệ qua lỗi tạm thời; thứ tự USD → user → system được giữ. Thay tiến trình `hostname`/`lscpu` bằng API Qt cục bộ.
- #49 dừng ở qmake vì `libukcc/interface.pri` còn liên kết `kysdk-datacollect` sau khi bỏ build dependency. Bản vá xóa dòng còn sót và build kiểm tra cả `.pro`/`.pri` trước khi biên dịch. Qt test riêng kiểm tra backend chính sách không phản hồi, cache, gộp yêu cầu, giữ chính sách khi backend lỗi và bỏ phản hồi cũ sau invalidation. Chưa thay thế kiểm thử boot/desktop thực tế.

- #45 dừng ở bước biên dịch installer vì Qt chuyển tên tài nguyên Trung Quốc thành `?` trong locale C; chưa tạo ISO. Build installer dùng `C.UTF-8` cho cả Qt resource scanner và qmake.
- Ngưỡng cài đặt trong bản vá là **30 GiB** (khoảng 32,21 GB thập phân), root tối thiểu 20 GiB. Đây là cùng hệ đơn vị nhị phân mà installer gốc dùng cho ngưỡng 50G. Kiểm tra chạy script chia phân vùng thật với EFI/BIOS, máy thật/VM, swapfile/swap partition và RAM 4/64 GiB trước khi đóng gói.
- Rebuild đúng `ukui-control-center 4.24.0.0-ok2.8`, xác minh SHA256 tarball. About đọc ngày mạng từ bộ nhớ đệm và thực hiện DNS/NTP bất đồng bộ với thời hạn 2 giây; truy vấn chính sách và ngày cài đặt/cập nhật cũng bất đồng bộ. Qt test kiểm tra phản hồi hợp lệ, bỏ qua gói sai và giao diện tiếp tục xử lý sự kiện khi máy chủ im lặng.
- Bản vá bổ sung cho cửa sổ Properties trắng/không phản hồi: đọc riêng từng thuộc tính About bằng D-Bus bất đồng bộ vào cache cục bộ (tránh cả introspection đồng bộ và `GetAll` gọi các getter không cần thiết). Truy vấn RAM, ổ đĩa và tên tài khoản có thời hạn 2 giây; lỗi RAM giữ số liệu dự phòng. Không truy vấn dịch vụ kích hoạt thương mại khi mục kích hoạt bị ẩn. Qt test trên session bus riêng kiểm tra dịch vụ không trả lời, phản hồi sai kiểu và hủy đối tượng trong lúc chờ. Chưa xác nhận bản vá này bằng boot ISO/desktop UKUI.
- Chính sách riêng tư mới: gỡ các gói `kylin-daq`, `kylin-sso-client`, `kylin-cloud-sync`, `libsync-plugin` nếu có, với phiên bản/metadata được đối chiếu trước purge. Bỏ lời gọi telemetry, SSO và nút gửi chẩn đoán trong Settings; cài cả `libukcc3` đã vá. SDK `libkysdk-datacollect` được rebuild thành lớp tương thích ABI chỉ cấp phát/giải phóng bộ nhớ, không đọc định danh, lưu sự kiện, gọi D-Bus hoặc kết nối mạng. Giữ lớp tương thích vì các ứng dụng desktop vẫn liên kết SONAME này; không sửa ép Depends hay gỡ desktop để loại thư viện. Build kiểm tra ABI và chạy SDK dưới seccomp cấm truy cập file/mạng/tạo tiến trình. Kiểm tra cuối ở cả Live root và OSTree chặn gói/dịch vụ kích hoạt còn sót. Các kiểm tra Linux này chưa chạy trong môi trường Windows hiện tại.
- About dùng NTP quốc tế `time.cloudflare.com` qua UDP/123, vẫn có thời hạn 2 giây và dự phòng giờ cục bộ khi offline. Không còn sử dụng danh sách NTP Trung Quốc trong đường gọi About. Chỉ thay nguồn ngày giờ của About, không thay cấu hình đồng bộ giờ toàn hệ thống.
- Nếu có SDK telemetry cũ `libkysdk-diagnostics 3.0.1.0-ok0.1`, thay riêng file thực thi `libkydiagnostics.so.3.0.1` bằng triển khai không làm gì của API `kdk_buried_point`; giữ các module khác của kysdk-base và metadata phụ thuộc. Đây là thay đổi file cục bộ có ghi SHA256 vào `privacy-local-patches.txt`. Dọn cache của daemon và SDK cũ; APT pin chặn cài lại các dịch vụ đã gỡ hoặc ghi đè thư viện/Settings đã vá bằng bản từ kho. `privacy-audit.txt` kiểm tra cả SDK mới và cũ.
- Giữ bản ISO chia phần trong draft Release. ISO #44 nguyên vẹn có dung lượng 3.956.604.928 byte, vượt giới hạn 2 GiB/tệp của Releases; ghép phần và xác minh checksum trước khi ghi USB.
- Sau lỗi dependency ở #47, SDK `libukui-quick-*` được ghim về `4.25.0.0-ok0.2` đúng bản trên ISO; kiểm tra SHA256 bốn gói build và giữ phiên bản qua APT pin. Trước upload, dependency sinh ra của control center được đối chiếu với snapshot phiên bản thư viện trên ISO gốc; gói đòi runtime mới hơn sẽ bị chặn tại job build. Không sửa ép dependency trong gói nhị phân.
- Các kiểm tra build không thay cho boot và cài thử ISO 30 GiB, hoặc tái hiện Properties/About trong desktop UKUI.

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

