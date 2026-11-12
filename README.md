# Độ sáng màn hình cho Ubuntu

Ứng dụng desktop tiếng Việt dành cho Ubuntu 24.04 LTS. Chọn một màn hình trong danh sách rồi kéo thanh trượt để điều chỉnh độ sáng riêng cho màn hình đó. Trên X11, ứng dụng mặc định làm tối hình ảnh bằng `xrandr`: mức 0% tương ứng `--brightness 0`, mức 100% tương ứng `--brightness 1`.

- Làm tối từng đầu ra X11 bằng `xrandr`, với tên kết nối chính xác từ phiên desktop.
- Chế độ phần cứng điều khiển đèn nền laptop bằng `brightnessctl` và màn hình rời hỗ trợ DDC/CI bằng `ddcutil`.
- Thanh trượt 0–100%, các mức nhanh 0/25/50/75/100% và khôi phục mức sáng khi mở ứng dụng.
- Phím tắt toàn cục `Super+Alt+0` đưa tất cả màn hình về 100%, dùng được cả khi cửa sổ đã ẩn, đang dùng ứng dụng khác, đã thoát hẳn ứng dụng và ở màn hình khóa; đổi được phím trong cửa sổ để tránh trùng.
- Quét lại thiết bị khi cắm hoặc rút màn hình; hiển thị tên, kết nối và trạng thái hỗ trợ.
- Chạy lệnh điều chỉnh ngoài luồng giao diện; gộp các lần kéo liên tiếp và giữ đúng màn hình khi chuyển lựa chọn.
- Chế độ xem thử với ba màn hình giả lập và công cụ dòng lệnh để kiểm tra thiết bị.

## Cài đặt và chạy

Mở terminal trong thư mục dự án:

```bash
./scripts/install.sh
./run.sh
```

Script cài các gói hệ thống qua `apt`, nạp `i2c-dev`, cấu hình nạp module khi khởi động, áp dụng quy tắc `udev`, thêm tài khoản vào nhóm `video` khi cần và tạo mục **Độ sáng màn hình** trong menu ứng dụng của tài khoản hiện tại. Chạy script bằng tài khoản desktop thông thường; script dùng `sudo` cho bước thiết lập hệ thống. Không cần cài thư viện bằng `pip`.

Nếu script vừa thêm nhóm `video`, **đăng xuất rồi đăng nhập lại** trước khi điều chỉnh màn hình laptop.

Biểu tượng ứng dụng trỏ đến thư mục dự án hiện tại. Nếu di chuyển thư mục dự án, tạo lại biểu tượng bằng:

```bash
./scripts/install.sh --launcher-only
```

Xem thử giao diện mà không điều chỉnh phần cứng:

```bash
./run.sh --demo
```

Các gói được dùng: `python3`, `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-4.0`, `x11-xserver-utils`, `brightnessctl`, `brightness-udev` và `ddcutil`. Ubuntu 24.04 cung cấp `brightnessctl` 0.5.1 và `ddcutil` 1.4.1; ứng dụng dùng các lệnh tương thích với những phiên bản này. [Gói Ubuntu](https://packages.ubuntu.com/noble/ddcutil), [brightnessctl](https://packages.ubuntu.com/noble/brightnessctl), [hướng dẫn GTK](https://pygobject.gnome.org/getting_started.html).

## Sử dụng

1. Chọn màn hình ở danh sách bên trái.
2. Kéo thanh trượt hoặc nhấn một mức có sẵn. Ứng dụng áp dụng ngay khi nhấn mức có sẵn hoặc sau khoảng 350 ms kể từ lần kéo cuối cùng.
3. Dùng **Khôi phục mức ban đầu** để trở lại mức sáng được đọc khi mở ứng dụng. Mức khôi phục được giữ nguyên khi quét lại.
4. Nhấn `Super+Alt+0` để đưa tất cả màn hình về 100%, kể cả khi ảnh đang đen, cửa sổ không được chọn hoặc đang ở màn hình khóa. Xem mục phím tắt toàn cục bên dưới để đổi phím.
5. Nhấn nút quét lại hoặc `Ctrl+R` sau khi thay đổi kết nối màn hình.
6. Đóng cửa sổ bằng nút `×` hoặc `Ctrl+Q` để ẩn ứng dụng xuống biểu tượng trên thanh tác vụ. Ứng dụng tiếp tục chạy ngầm trong phiên đăng nhập hiện tại để giữ mức sáng đã chọn.
7. Mở lại cửa sổ hoặc chỉnh nhanh từng màn hình từ biểu tượng trên thanh tác vụ. Khi muốn dừng chạy ngầm hoàn toàn, nhấn **Thoát hẳn ứng dụng** trong cửa sổ, chọn trong menu khay hệ thống hoặc chạy `./run.sh --quit`.

Ứng dụng đọc độ sáng hiện tại khi mở hoặc quét lại, rồi đọc kết quả sau mỗi lần điều chỉnh. Mở ứng dụng không tự áp dụng mức sáng. Trong chế độ phần mềm trên X11, ứng dụng tự động áp dụng lại mức sáng bạn đã chọn kể cả khi đã đóng cửa sổ ẩn xuống khay hệ thống nếu hệ thống đặt lại bảng màu khi khóa, mở khóa hoặc bật lại màn hình. Màn hình khóa cũng giữ đúng mức sáng đã chọn, kể cả 0%; nếu không nhìn thấy ô mật khẩu, nhấn phím tắt toàn cục để về 100%. Nếu lần ghi bị lỗi vì hệ thống đang tắt hoặc cấu hình lại màn hình, ứng dụng tự thử lại sau 5 giây; khi khởi động lại máy hoặc đăng xuất, màn hình trở về mặc định 100%. Trong chế độ phần cứng, nhấn quét lại sau khi thay đổi bằng phím laptop hoặc menu màn hình để cập nhật.

## Phím tắt toàn cục

Phím mặc định là `Super+Alt+0` và chạy lệnh `./run.sh reset`:

- Nếu ứng dụng đang chạy, lệnh yêu cầu ứng dụng đưa tất cả màn hình về 100% để cơ chế giữ mức sáng không làm tối lại.
- Nếu ứng dụng không chạy, lệnh điều chỉnh trực tiếp tất cả màn hình hỗ trợ.

GNOME 46 chỉ cho phím tắt tùy chỉnh chạy ở desktop và màn tổng quan, không chạy ở màn hình khóa. Vì vậy ứng dụng đi kèm một extension GNOME Shell nhỏ trong thư mục `gnome-extension/` (`ubuntu-brightness@ubuntubrightness.github.io`), khai báo hỗ trợ màn hình khóa (`session-modes: user, unlock-dialog`). Khi mở ứng dụng hoặc chạy `./scripts/install.sh`:

1. Ứng dụng chép extension vào `~/.local/share/gnome-shell/extensions/`, biên dịch schema và bật extension.
2. Trong lúc GNOME Shell chưa nạp extension, ứng dụng tạo phím tắt tùy chỉnh của GNOME tên **Độ sáng màn hình: đưa tất cả về 100%** để phím vẫn dùng được ngoài màn hình khóa.
3. Khởi động lại GNOME Shell **một lần** để nạp extension: trên X11 nhấn `Alt+F2`, gõ `r` rồi `Enter` (các cửa sổ vẫn giữ nguyên); trên Wayland đăng xuất rồi đăng nhập lại.
4. Khi chạy, extension tự chuyển phím tắt tùy chỉnh ở bước 2 sang chính nó và giữ phím ở mọi chế độ, kể cả màn hình khóa. Mục trong **Cài đặt → Bàn phím → Phím tắt tùy chỉnh** được gỡ để hai nơi không tranh cùng một phím.

Nếu extension bị tắt hoặc lỗi, ứng dụng tự quay về phím tắt tùy chỉnh ở lần mở sau. Dòng trạng thái dưới phím tắt trong cửa sổ cho biết phím đã dùng được ở màn hình khóa hay chưa.

Đổi phím trong cửa sổ ứng dụng ở phần **Phím tắt đưa tất cả màn hình về 100%**: nhấn **Đổi phím tắt**, bấm tổ hợp mới rồi **Lưu**. Hộp thoại cảnh báo nếu tổ hợp trùng với phím tắt khác của GNOME. Phím tắt riêng trong từng ứng dụng, ví dụ `Ctrl+0` của trình duyệt, không được kiểm tra, nên hãy tránh các tổ hợp quen thuộc này.

```bash
./run.sh shortcut                        # xem phím hiện tại và trạng thái màn hình khóa
./run.sh shortcut --set '<Ctrl><Alt>b'   # đổi phím
./run.sh shortcut --default              # về Super+Alt+0
./run.sh shortcut --disable              # tắt phím tắt
```

Nếu di chuyển thư mục dự án, mở lại ứng dụng hoặc chạy `./run.sh shortcut --ensure` để cập nhật đường dẫn lệnh.

## Cách điều chỉnh

| Chế độ | Khi dùng | Ý nghĩa của 0% |
| --- | --- | --- |
| `auto` (mặc định) | Chọn `software` trên X11, `hardware` trên Wayland hoặc khi không có phiên X11 | Theo chế độ được chọn |
| `software` | Làm tối hình ảnh bằng `xrandr` trên X11 | Gửi `--brightness 0`, cho ảnh đen |
| `hardware` | Điều chỉnh đèn nền trên X11 hoặc Wayland | Gửi mức 0 tới thiết bị; mức sáng thấp nhất phụ thuộc màn hình |

```bash
# Làm tối hình ảnh giống xrandr --brightness
./run.sh --mode software

# Điều chỉnh độ sáng phần cứng
./run.sh --mode hardware
```

Trong chế độ `software`, 50% gửi `--brightness 0.50`, 100% gửi `--brightness 1.00`. Mức 100% bỏ hiệu ứng làm tối; độ sáng đèn nền vẫn giữ mức đang có. Cách này điều chỉnh bảng màu bằng phần mềm. [Tài liệu xrandr trên Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/man1/xrandr.1.html).

Nếu hai đầu ra dùng chung bộ điều khiển màu (CRTC), ứng dụng hiển thị lý do và yêu cầu chuyển sang chế độ mở rộng để điều chỉnh riêng. Màn hình đã kết nối nhưng đang tắt cũng được hiển thị cùng hướng dẫn bật lại.

Trên Wayland, chế độ mặc định điều chỉnh phần cứng. Để dùng `software`, chọn **Ubuntu on Xorg** ở màn hình đăng nhập.

## Màn hình và kết nối được hỗ trợ

| Loại màn hình | Điều kiện |
| --- | --- |
| Laptop hoặc màn hình rời, chế độ `software` | Phiên X11, đầu ra đang hoạt động và driver cung cấp điều khiển bảng màu |
| Laptop, chế độ `hardware` | Driver cung cấp thiết bị trong `/sys/class/backlight` và tài khoản có quyền điều khiển đèn nền |
| Màn hình rời, chế độ `hardware` | Hỗ trợ VCP 0x10, bật DDC/CI và đường kết nối cho phép truyền lệnh DDC |

Một số dock, bộ chuyển đổi, màn hình DisplayLink hoặc chế độ HDR/tương phản động có thể chặn điều khiển độ sáng phần cứng. Màn hình không cung cấp điều khiển phần cứng được hiển thị cùng lý do nếu Linux nhận diện được kết nối. [Tài liệu ddcutil](https://www.ddcutil.com/faq/).

Trong chế độ `hardware`, nếu driver cung cấp nhiều thiết bị đèn nền, danh sách giữ tên từng thiết bị để bạn nhận diện; chúng có thể cùng điều khiển một màn hình. Mức 0% gửi giá trị 0 tới bộ điều khiển độ sáng; đèn nền có thể tắt tùy thiết bị. Các mức lớn hơn 0% được làm tròn lên tối thiểu một đơn vị phần cứng; một số đèn nền chỉ có ít mức điều chỉnh.

## Quyền truy cập và xử lý lỗi

Chế độ `software` chạy bằng tài khoản đang đăng nhập vào phiên X11. Các thiết lập nhóm `video` và quyền I²C bên dưới áp dụng cho chế độ `hardware`.

### Màn hình laptop

Nếu ứng dụng báo thiếu quyền điều khiển đèn nền sau khi cài đặt, thêm tài khoản vào nhóm `video`:

```bash
sudo usermod -aG video "$(id -un)"
```

**Đăng xuất rồi đăng nhập lại**, sau đó mở ứng dụng. `brightness-udev` cung cấp quy tắc quyền truy cập đèn nền. [Cách brightnessctl cấp quyền](https://github.com/Hummer12007/brightnessctl#permissions).

### Màn hình rời

Bật **DDC/CI** trong menu vật lý của màn hình và kiểm tra:

```bash
ddcutil detect --brief
```

`ddcutil` cần quyền đọc/ghi thiết bị I²C. Nếu quy tắc `udev` của gói chưa cấp quyền cho phiên desktop, kiểm tra nhóm `i2c` do gói phụ thuộc `i2c-tools` cung cấp rồi thêm tài khoản:

```bash
getent group i2c
sudo usermod -aG i2c "$(id -un)"
```

Đăng xuất rồi đăng nhập lại. Nếu nhóm không tồn tại hoặc lỗi vẫn còn, xem [hướng dẫn quyền I²C chính thức](https://www.ddcutil.com/i2c_permissions_using_group_i2c/). Không cần chạy toàn bộ giao diện bằng `sudo`.

Nếu không tìm thấy màn hình rời, thử kết nối trực tiếp bằng HDMI/DisplayPort, kiểm tra module `i2c-dev` và tắt chế độ tương phản động khi cần. [Module cần thiết](https://www.ddcutil.com/kernel_module/), [điều khiển độ sáng](https://www.ddcutil.com/command_getvcp/).

### Thiếu giao diện GTK

Dùng `./run.sh` để chọn Python hệ thống `/usr/bin/python3`, nơi Ubuntu cài PyGObject. Python trong môi trường ảo riêng có thể không nhìn thấy thư viện GTK do `apt` cài.

## Công cụ dòng lệnh

```bash
# Liệt kê thiết bị và mã màn hình
./run.sh list
./run.sh list --json

# Thay mã bên dưới bằng mã thật trong danh sách của bạn
./run.sh --mode software set xrandr:HDMI-1 0
./run.sh --mode software set xrandr:HDMI-1 100

# Mã phần cứng được lấy từ danh sách của chế độ hardware
./run.sh --mode hardware list
./run.sh --mode hardware set ddc:i2c-7 60
./run.sh --mode hardware set backlight:intel_backlight 45

# Kiểm tra bằng dữ liệu giả lập
./run.sh --demo list --json
./run.sh --demo set demo:dell 50

# Đưa tất cả màn hình về 100% (lệnh của phím tắt toàn cục)
./run.sh reset

# Dừng hẳn ứng dụng đang chạy ngầm
./run.sh --quit
```

Mỗi lần chạy `--demo` khởi tạo lại ba màn hình giả lập. Tên đầu ra X11 và mã bus I²C có thể thay đổi sau khi cắm/rút hoặc khởi động lại; lấy lại mã từ `list` trước khi dùng trong script.

Để đưa hình ảnh về 100% từ terminal, lấy tên kết nối bằng `xrandr --query` rồi chạy, ví dụ:

```bash
xrandr --output HDMI-1 --brightness 1
```

## Cấu trúc dự án

| Tệp | Vai trò |
| --- | --- |
| `ubuntu_brightness/gui.py` | Cửa sổ GTK, lựa chọn màn hình, thanh trượt và trạng thái |
| `ubuntu_brightness/tray.py` | Biểu tượng khay hệ thống và menu điều khiển nhanh qua D-Bus |
| `ubuntu_brightness/backends.py` | Dò màn hình, đọc đèn nền, chạy `ddcutil`/`brightnessctl` và giả lập |
| `ubuntu_brightness/xrandr.py` | Đọc đầu ra X11, nhận diện màn hình và làm tối bằng `xrandr` |
| `ubuntu_brightness/controller.py` | Hàng đợi tuần tự, gộp yêu cầu và trả kết quả về giao diện |
| `ubuntu_brightness/models.py` | Thiết bị, độ sáng và xác thực giá trị |
| `ubuntu_brightness/style.css` | Giao diện theo theme GTK và màu nhấn Ubuntu |
| `ubuntu_brightness/shortcut.py` | Cài extension, tạo, đổi và kiểm tra trùng phím tắt toàn cục |
| `gnome-extension/` | Extension GNOME Shell giữ phím tắt ở mọi chế độ, kể cả màn hình khóa |
| `scripts/install.sh` | Cài phụ thuộc, module, biểu tượng ứng dụng và phím tắt toàn cục |

## Gỡ mục ứng dụng

```bash
rm -- "${XDG_DATA_HOME:-$HOME/.local/share}/applications/io.github.ubuntubrightness.desktop"
```

Lệnh này gỡ biểu tượng trong menu ứng dụng; mã nguồn và các gói hệ thống vẫn được giữ lại. Để gỡ phím tắt toàn cục, thoát hẳn ứng dụng rồi chạy:

```bash
gnome-extensions disable ubuntu-brightness@ubuntubrightness.github.io
rm -r -- "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/ubuntu-brightness@ubuntubrightness.github.io"
```

Sau đó xóa mục **Độ sáng màn hình: đưa tất cả về 100%** trong **Cài đặt → Bàn phím → Phím tắt tùy chỉnh** nếu còn. Lần mở ứng dụng sau sẽ cài lại phím mặc định. Muốn giữ ứng dụng nhưng tắt phím, dùng `./run.sh shortcut --disable`.
