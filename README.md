# Directory Sync Tool

Directory Sync Tool là phần mềm đồng bộ hóa thư mục mạnh mẽ, hỗ trợ giao diện đồ họa hiện đại, giúp bạn dễ dàng đồng bộ dữ liệu giữa các thư mục cục bộ hoặc sử dụng Rclone cho các dịch vụ đám mây.

## Tính năng

- **Đồng bộ nhiều cặp thư mục**: Thêm, xóa, cấu hình nhiều cặp nguồn - đích.
- **Hỗ trợ Rclone**: Tùy chọn sử dụng Rclone để đồng bộ với các dịch vụ đám mây.
- **Đồng bộ bằng Robocopy**: Sử dụng Robocopy cho đồng bộ nhanh và an toàn trên Windows.
- **Tự động phát hiện dự án Rust**: Nếu thư mục nguồn là dự án Rust, tự động chạy `cargo clean` trước khi đồng bộ.
- **Cấu hình thời gian lặp**: Đặt khoảng thời gian lặp lại chu kỳ đồng bộ (tính bằng giây).
- **Lưu & tải cấu hình**: Lưu cấu hình các cặp thư mục và thời gian lặp vào file `config.json`.
- **Giao diện tối hiện đại**: Thiết kế giao diện thân thiện, dễ sử dụng, hỗ trợ kéo thả, chọn thư mục, xem log chi tiết.

## Yêu cầu

- Python 3.x
- Windows (yêu cầu Robocopy)
- [Rclone](https://rclone.org/) (nếu sử dụng đồng bộ đám mây)
- (Tùy chọn) Cargo (nếu đồng bộ dự án Rust)

## Cách sử dụng

1. **Cài đặt các phần mềm cần thiết** (Python, Rclone, Cargo nếu cần).
2. **Chạy phần mềm**:
   ```sh
   python main.py