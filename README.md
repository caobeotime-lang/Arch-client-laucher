# Arch Client Launcher — Windows

Launcher Minecraft Fabric, chỉ cần **1 file `.exe` duy nhất**, không cần
cài Python, không cần cài Java thủ công, không cần `pip install` gì cả.
Double-click là chạy.

![Arch Client icon](img/icon.png)

---

## Tính năng

- **Tự tải Java 21** khi thiếu — launcher tự phát hiện và tải thẳng
  Eclipse Temurin (Adoptium) về, giải nén, dùng luôn, không cần cài đặt
  thủ công.
- **Tự dựng cấu trúc thư mục `.minecraft`** — tạo mới hoàn toàn nếu chưa
  có, hoặc tự bổ sung phần thiếu nếu đã có sẵn từ trước.
- **Cài/cập nhật Fabric** cho đúng phiên bản Minecraft chỉ với 1 lần bấm.
- **Tối ưu FPS 1 chạm** — tự ghi `options.txt` đã tinh chỉnh sẵn và tải
  bộ mod tối ưu hiệu năng phổ biến (Sodium, Lithium, Starlight,
  FerriteCore, Krypton, LazyDFU, Iris, ModernFix, EntityCulling,
  ImmediatelyFast) từ Modrinth, khớp đúng phiên bản Minecraft + Fabric.
- **Đăng nhập Microsoft** để chơi online.
- **Discord Rich Presence** (tuỳ chọn) — hiện đang chơi gì / đang ở tab
  nào ngay trên Discord.
- **Console tích hợp sẵn** — xem log game trực tiếp trong app, lưu log ra
  file `.txt` khi cần báo lỗi.
- **Tự ghi log lỗi** — mọi lỗi không mong muốn đều được ghi lại kèm
  traceback đầy đủ vào `%USERPROFILE%\.config\arch-client-launcher\error_logs\`,
  không bao giờ crash âm thầm.
- **Đa ngôn ngữ (VI/EN)** — tự chọn theo vị trí IP, nếu mất mạng thì dùng
  theo ngôn ngữ hệ thống.
- **Tự thêm client mod đi kèm** — nếu có sẵn file `.jar` trong thư mục
  `client/` cạnh `.exe`, launcher tự copy vào `mods/` khi thiếu hoặc
  chưa cập nhật.

## Yêu cầu

- Windows 10/11.
- Có mạng ở lần chạy đầu tiên (để tải Java, tải Fabric, xác định ngôn
  ngữ theo IP). Sau đó vẫn dùng được offline, trừ các tính năng cần
  mạng (tải mod, đăng nhập).

## Cài đặt & chạy

Không cần cài đặt gì trước — chỉ cần tải `ArchClient.exe` rồi chạy:

1. Tải file `ArchClient.exe`.
2. Double-click để mở.
3. Nếu Windows hiện cảnh báo **"Windows protected your PC"** (SmartScreen) —
   đây là bình thường với file `.exe` chưa ký số (code signing), không
   phải virus. Bấm **More info → Run anyway** để mở.
4. Lần chạy đầu tiên sẽ lâu hơn một chút vì launcher đang tự tải Java 21
   và dựng cấu trúc thư mục `.minecraft`. Các lần sau sẽ nhanh hơn nhiều.

## Hướng dẫn sử dụng

Cửa sổ chính chia làm 4 tab:

| Tab | Dùng để làm gì |
|---|---|
| 📊 Overview | Chọn thư mục `.minecraft`, xem danh sách mod/resourcepack/shaderpack/schematic đang cài. |
| ⚙️ Settings | Tự kiểm tra/cài Java, đăng nhập Microsoft, chỉnh RAM cấp cho game. |
| 🚀 Optimize FPS | 1 chạm để ghi cấu hình FPS tối ưu + tải bộ mod hiệu năng đã chọn. |
| 🖥️ Console | Xem log trực tiếp khi game chạy, xoá console, lưu log ra file. |

Ở dưới cùng luôn có 2 nút cố định: **⬇ Install / Update Fabric** (bấm
trước khi chơi lần đầu hoặc sau khi đổi phiên bản) và **▶ PLAY NOW**. Quy
trình chuẩn cho lần chơi đầu tiên: cài Fabric → kiểm tra Java ở tab
Settings → đăng nhập Microsoft (nếu chơi online) → bấm Play Now.

## Xử lý lỗi thường gặp

**Windows chặn/xoá file khi tải về hoặc khi mở**
File `.exe` chưa được ký số nên Windows Defender/SmartScreen đôi khi
báo nhầm. Bấm **More info → Run anyway**, hoặc thêm ngoại lệ trong
Windows Security nếu cần.

**Mở app không lên, hoặc nháy 1 cái console đen rồi tắt ngay**
Kiểm tra kết nối mạng — lần chạy đầu launcher cần mạng để tải Java và dò
ngôn ngữ. Nếu vẫn lỗi, tìm file log lỗi mới nhất trong
`%USERPROFILE%\.config\arch-client-launcher\error_logs\` để xem traceback
chi tiết.

**Game crash ngay khi mở, log Java báo lỗi liên quan đến
`MessageFormat` / `Mod resolution failed`**
Thường là do 2 mod trong `mods/` xung đột nhau. Tìm dòng
`Mod resolution failed` và `Immediate reason:` ngay phía trên đoạn crash
trong `latest.log` (hoặc trong file log ở `error_logs/`) để biết chính
xác mod nào đang xung đột, rồi gỡ hoặc đổi mod đó.

**Discord Rich Presence không hiện**
Tính năng tuỳ chọn, không bắt buộc — không ảnh hưởng gì đến việc chơi
game nếu không có.

## Giấy phép

Phần mềm này **miễn phí cho mục đích cá nhân, phi thương mại**. Được
phép tải về, chỉnh sửa, chia sẻ lại miễn phí. **Không được** bán, cho
thuê, đóng gói lại để kiếm lời, hoặc dùng cho mục đích thương mại dưới
bất kỳ hình thức nào nếu chưa được tác giả đồng ý bằng văn bản. Xem chi
tiết trong file [`LICENSE`](LICENSE).

## Credits

Cảm ơn các dự án mã nguồn mở mà Arch Client sử dụng:
[Fabric](https://fabricmc.net/),
[minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib),
[ttkbootstrap](https://ttkbootstrap.readthedocs.io/), cùng các tác giả bộ
mod tối ưu FPS liệt kê ở trên trên [Modrinth](https://modrinth.com/).

---

🌐 [archclient.netlify.app](https://archclient.netlify.app)
