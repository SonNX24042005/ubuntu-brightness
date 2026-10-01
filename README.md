# Độ sáng màn hình cho Ubuntu

Ứng dụng desktop tiếng Việt dành cho Ubuntu 24.04 LTS. Chọn một màn hình trong danh sách rồi kéo thanh trượt để điều chỉnh độ sáng riêng cho màn hình đó. Trên X11, ứng dụng mặc định làm tối hình ảnh bằng `xrandr`: mức 0% tương ứng `--brightness 0`, mức 100% tương ứng `--brightness 1`.

- Làm tối từng đầu ra X11 bằng `xrandr`, với tên kết nối chính xác từ phiên desktop.
- Chế độ phần cứng điều khiển đèn nền laptop bằng `brightnessctl` và màn hình rời hỗ trợ DDC/CI bằng `ddcutil`.
- Thanh trượt 0–100%, các mức nhanh 0/25/50/75/100% và khôi phục mức sáng khi mở ứng dụng.
- Phím `Ctrl+0` đưa màn hình đang chọn về 100% khi cửa sổ ứng dụng đang được chọn.
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
2. Kéo thanh trượt hoặc nhấn một mức có sẵn. Ứng dụng áp dụng sau khoảng 350 ms kể từ lần kéo cuối cùng.
3. Dùng **Khôi phục mức ban đầu** để trở lại mức sáng được đọc khi mở ứng dụng. Mức khôi phục được giữ nguyên khi quét lại.
4. Nhấn `Ctrl+0` để đưa màn hình đã chọn về 100%; phím này dùng được khi ảnh đang đen nếu cửa sổ ứng dụng vẫn được chọn.
5. Nhấn nút quét lại hoặc `Ctrl+R` sau khi thay đổi kết nối màn hình.
6. Đóng bằng `Ctrl+Q` hoặc nút đóng cửa sổ. Ứng dụng hoàn tất thay đổi đang chờ trước khi thoát.

Ứng dụng đọc độ sáng hiện tại khi mở hoặc quét lại, rồi đọc kết quả sau mỗi lần điều chỉnh. Mở ứng dụng không tự áp dụng mức sáng. Trong chế độ phần cứng, nhấn quét lại sau khi thay đổi bằng phím laptop hoặc menu màn hình để cập nhật.

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
| `ubuntu_brightness/backends.py` | Dò màn hình, đọc đèn nền, chạy `ddcutil`/`brightnessctl` và giả lập |
| `ubuntu_brightness/xrandr.py` | Đọc đầu ra X11, nhận diện màn hình và làm tối bằng `xrandr` |
| `ubuntu_brightness/controller.py` | Hàng đợi tuần tự, gộp yêu cầu và trả kết quả về giao diện |
| `ubuntu_brightness/models.py` | Thiết bị, độ sáng và xác thực giá trị |
| `ubuntu_brightness/style.css` | Giao diện theo theme GTK và màu nhấn Ubuntu |
| `scripts/install.sh` | Cài phụ thuộc, module và biểu tượng ứng dụng |

## Gỡ mục ứng dụng

```bash
rm -- "${XDG_DATA_HOME:-$HOME/.local/share}/applications/io.github.ubuntubrightness.desktop"
```

Lệnh này gỡ biểu tượng trong menu ứng dụng; mã nguồn và các gói hệ thống vẫn được giữ lại.
