# Arch Client

Launcher Minecraft Fabric viết bằng Python, ban đầu làm cho CachyOS/KDE Plasma
của mình nhưng giờ chạy được trên cả Windows lẫn các distro Linux dựa trên
Arch hoặc Debian. Mục tiêu ban đầu chỉ đơn giản là: bấm một phát là chơi được,
không phải tự mò cài Java, cài Fabric, hay lo launcher gốc không đọc được thư
mục mod linh tinh mình để lung tung.

Giao diện dùng `ttkbootstrap` (theme *flatly*), có console kiểu terminal thật
ngay trong app để theo dõi log, và launcher tự lo gần như mọi thứ ở bước cài
đặt ban đầu.

![Arch Client banner](img/banner.png)

---

## Vì sao lại có cái này

Launcher chính thức của Mojang không hỗ trợ Fabric, còn các launcher bên thứ
ba (MultiMC, Prism...) thì tốt nhưng hơi cồng kềnh nếu chỉ cần một bộ mod cố
định, tối ưu FPS sẵn, không cần chỉnh tay nhiều. Arch Client được viết ra để
tự động hoá phần đó: mở lên, launcher tự phát hiện thiếu gì thì cài đó, tự
tạo cấu trúc `.minecraft`, và có sẵn nút "Tối ưu FPS" để tải một bộ mod đã
chọn lọc từ Modrinth.

## Tính năng

- **Tự nhận diện hệ điều hành** — Windows 10/11, Arch Linux và các distro dựa
  trên Arch (Manjaro, EndeavourOS, Garuda, CachyOS...), Debian/Ubuntu và các
  distro dựa trên Debian (Mint, Pop!_OS, Zorin...).
- **Tự cài thư viện Python còn thiếu** ngay khi chạy (`ttkbootstrap`,
  `minecraft-launcher-lib`, `requests`, `Pillow`...), tự xử lý luôn lỗi
  `externally-managed-environment` hay gặp trên các distro mới bằng cách
  fallback sang `--break-system-packages`.
- **Tự cài gói hệ thống** nếu thiếu `tkinter`, qua `pacman` hoặc `apt` tuỳ
  distro.
- **Tự dò và cài Java** đúng phiên bản Minecraft yêu cầu (Java 21+ cho
  1.20.5 trở lên), tải trực tiếp từ Adoptium nếu máy chưa có, hoặc thử qua
  trình quản lý gói của hệ thống trước.
- **Tự tạo cấu trúc `.minecraft`** — tạo mới hoàn toàn nếu chưa có gì, hoặc
  chỉ tạo bù đúng phần thư mục con đang thiếu nếu đã có sẵn thư mục cũ.
- **Cài/cập nhật Fabric** cho đúng phiên bản Minecraft đang target, không
  cần thao tác gì thêm ngoài bấm nút.
- **Tối ưu FPS một chạm** — ghi sẵn bộ `options.txt` đã tinh chỉnh, kèm tải
  tự động các mod tối ưu phổ biến (Sodium, Lithium, Starlight, FerriteCore,
  Krypton, LazyDFU, Iris, ModernFix, EntityCulling, ImmediatelyFast) từ
  Modrinth, khớp đúng phiên bản Minecraft + Fabric.
- **Đăng nhập Microsoft** để chơi online.
- **Discord Rich Presence** (tuỳ chọn) — hiện đang chơi gì / đang ở tab nào
  ngay trên Discord, tắt được nếu không cài `pypresence`.
- **Console tích hợp** — xem log game trực tiếp trong app, lưu log ra file
  `.txt` khi cần báo lỗi.
- **Tự ghi log lỗi** — mọi exception chưa xử lý (ở luồng chính, luồng nền,
  hay callback giao diện) đều được bắt và ghi thành file `.txt` có timestamp
  trong `~/.config/arch-client-launcher/error_logs/`, kèm traceback đầy đủ,
  không bao giờ crash âm thầm.
- **Đa ngôn ngữ (VI/EN)** — tự chọn theo vị trí máy qua IP, fallback theo
  locale hệ thống nếu không có mạng.
- **Tự thêm mod client riêng** — nếu launcher đi kèm thư mục `client/` chứa
  sẵn file `.jar`, sẽ tự copy vào `mods/` nếu đang thiếu hoặc là bản cũ hơn.

## Cấu trúc thư mục

```
Arch client laucher/
├── arch_client.py      # toàn bộ launcher, chạy file này
├── client/              # (tuỳ chọn) mod client đi kèm sẵn, tự copy vào mods/
│   └── arch-client-1.21.11.jar
└── img/
    ├── icon.png          # icon cửa sổ / taskbar
    └── banner.png        # banner hiện ở tab Tổng quan và splash screen
```

Nếu thiếu `img/icon.png` hoặc `img/banner.png`, launcher vẫn chạy bình
thường, chỉ là hiện chữ thay cho ảnh. Thư mục `client/` cũng không bắt buộc —
không có thì launcher bỏ qua bước copy mod, không báo lỗi.

## Yêu cầu

- Python 3.9 trở lên (dùng `sys.getwindowsversion`, type hint kiểu mới nên
  cần bản khá mới).
- Kết nối mạng ở lần chạy đầu (để cài thư viện, tải Fabric, tải Java, dò
  ngôn ngữ theo IP). Chạy offline vẫn được sau khi mọi thứ đã cài xong, chỉ
  mất tính năng cần mạng (tải mod, đăng nhập).
- Trên Linux cần `sudo` hoạt động được nếu launcher cần cài gói hệ thống
  (`tk`, `jdk-openjdk`...) — launcher tự thêm `sudo` vào lệnh khi cần.

## Cài đặt & chạy

Không cần cài gì trước — clone hoặc tải repo về rồi chạy thẳng:

```bash
python3 arch_client.py
```

Lần đầu chạy sẽ hơi lâu vì launcher phải cài xong các thư viện Python còn
thiếu, dò Java, tạo cấu trúc `.minecraft`. Các lần sau sẽ nhanh vì mọi thứ
đã có sẵn.

Nếu muốn cài tay trước cho chắc:

```bash
pip install minecraft-launcher-lib requests ttkbootstrap pillow --break-system-packages
```

## Hướng dẫn sử dụng

Cửa sổ chính chia làm 4 tab:

| Tab | Dùng để làm gì |
|---|---|
| 📊 Tổng quan | Chọn thư mục `.minecraft`, xem danh sách file mod/resourcepack/shaderpack/schematic đang có. |
| ⚙️ Cài đặt | Kiểm tra/cài Java tự động, đăng nhập Microsoft, chỉnh RAM cấp cho game. |
| 🚀 Tối ưu FPS | Bấm một nút để ghi cấu hình FPS tối ưu + tải bộ mod hiệu năng đã chọn. |
| 🖥️ Console | Xem log trực tiếp lúc chạy game, xoá console, lưu log ra file. |

Ở footer luôn có 2 nút cố định: **⬇ Cài / Cập nhật Fabric** (bấm trước khi
chơi lần đầu hoặc sau khi đổi phiên bản) và **▶ CHƠI NGAY**. Trình tự chuẩn
cho lần đầu chạy: bấm cài Fabric → kiểm tra Java ở tab Cài đặt → đăng nhập
Microsoft (nếu chơi online) → bấm Chơi ngay.

## Xử lý sự cố thường gặp

**Launcher không mở lên, báo thiếu `tkinter`**
Distro của bạn tách `tkinter` ra khỏi Python gốc. Cài `sudo pacman -S tk`
(Arch) hoặc `sudo apt install python3-tk` (Debian/Ubuntu) rồi chạy lại —
launcher cũng tự làm việc này nếu có quyền sudo, nhưng nếu môi trường không
cho chạy sudo tự động thì phải làm tay.

**Game crash ngay lúc mở, log Java báo lỗi liên quan `MessageFormat` /
`Mod resolution failed`**
Đây là 2 mod trong `mods/` đang xung đột nhau (một mod cần mod khác mà bạn
chưa cài, hoặc hai mod tuyên bố không tương thích với nhau) — bản thân
Fabric Loader có bug khiến thông báo lỗi thật bị che mất bởi một exception
khác trông như lỗi định dạng ngày giờ. Tìm 2 dòng `Mod resolution failed` và
`Immediate reason:` ngay phía trên đoạn crash trong `latest.log` (hoặc trong
file log mà launcher tự ghi ở `error_logs/`) để biết chính xác mod nào đang
đụng mod nào, rồi gỡ bớt/thay bản khác.

**Cài thư viện Python tự động thất bại**
Thường do máy không có mạng lúc chạy lần đầu, hoặc pip bị chặn bởi tường
lửa/proxy công ty. Cài tay bằng lệnh launcher in ra trong console (có sẵn cờ
`--break-system-packages`), hoặc kiểm tra kết nối mạng trước.

**Discord Rich Presence không hiện**
Thiếu `pypresence` — không bắt buộc, launcher vẫn chạy được, chỉ mất tính
năng hiện trạng thái trên Discord. Cài `pip install pypresence
--break-system-packages` nếu muốn bật lại.

## Đóng góp

Repo cá nhân, chưa có quy trình đóng góp chính thức. Nếu tìm thấy bug hoặc
có ý tưởng cải thiện, cứ mở issue mô tả rõ: hệ điều hành, bản Python, và
log/traceback nếu có crash — dễ tra hơn nhiều so với chỉ mô tả bằng lời.

## Giấy phép

Phần mềm này **miễn phí cho mục đích cá nhân, phi thương mại**. Được phép
tải về, sửa đổi, và chia sẻ lại miễn phí. **Không được phép** bán, cho thuê,
đóng gói lại để kiếm tiền, hoặc dùng vào bất kỳ mục đích thương mại nào dưới
mọi hình thức mà không có sự đồng ý trước bằng văn bản của tác giả. Xem chi
tiết trong file [`LICENSE`](LICENSE).

Lưu ý: giấy phép này chỉ áp dụng cho code của launcher (`arch_client.py`).
Các mod bên thứ ba mà launcher tải về (Sodium, Lithium, Iris, Fabric API...)
giữ nguyên giấy phép gốc của tác giả từng mod — launcher không sở hữu và
không cấp quyền gì thêm đối với các file đó.

## Ghi công

Cảm ơn các dự án mã nguồn mở mà Arch Client dựa vào để hoạt động:
[Fabric](https://fabricmc.net/), [minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib),
[ttkbootstrap](https://ttkbootstrap.readthedocs.io/), và toàn bộ tác giả các
mod tối ưu FPS được liệt kê ở trên trên [Modrinth](https://modrinth.com/).

---

🌐 [archclient.netlify.app](https://archclient.netlify.app)
