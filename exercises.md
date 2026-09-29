# Phiếu Phản Ánh — K4 Level 3B, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng mẫu placeholder bằng câu trả lời của bạn.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Nguyễn Thành Nam  Mã học viên: 2A202602694

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Tình huống: Khi deploy service lên môi trường cloud (Railway/Render), nhà phát triển quên thiết lập biến môi trường `AGENT_API_KEY` trong dashboard.
- Nếu để giá trị mặc định như `"changeme"`: Service vẫn khởi động thành công và mở cổng ra Internet. Kẻ tấn công hoặc bot quét tự động có thể đoán hoặc dùng chính key mặc định `"changeme"` để gọi API `/ask`, làm tiêu hao ngân sách LLM và gây thất thoát chi phí mà bạn không hề hay biết cho đến khi nhận hóa đơn.
- Với nguyên tắc "fail fast" (không đặt default): Ứng dụng sẽ gặp lỗi `ValidationError` và crash ngay lập tức trong quá trình khởi động (startup). Triển khai trên cloud sẽ báo lỗi đỏ ngay lúc deploy, buộc lập trình viên phải cấu hình secret hợp lệ trước khi service có thể tiếp nhận bất kỳ request nào từ bên ngoài.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thu được:
`{"event": "ask_completed", "level": "info", "timestamp": "2026-09-29T10:42:00.123456+00:00", "user_id": "sv-test", "tokens_in": 12, "tokens_out": 45, "cost_usd": 0.000045}`

Hai việc làm được với log cấu trúc JSON mà `print("đã trả lời xong")` không làm được:
1. **Truy vấn, lọc và tổng hợp số liệu tự động (Query & Aggregation):** Các hệ thống thu thập log tập trung (Datadog, Grafana Loki, CloudWatch) có thể tự động phân tích cú pháp các trường dữ liệu để trả lời các câu hỏi quản trị như: *"Người dùng nào tiêu tốn nhiều chi phí nhất hôm nay?"* hoặc *"Tính tổng token tiêu thụ của user sv-test trong 24 giờ qua"*. Log chuỗi văn bản thuần túy của `print()` không thể bóc tách số liệu có cấu trúc chính xác.
2. **Thiết lập cảnh báo tự động theo ngưỡng (Automated Alerting):** Có thể cấu hình cảnh báo tự động gửi thông báo về Slack/PagerDuty khi trường `cost_usd` trong một request vượt quá ngưỡng cho phép (ví dụ > $1.0) hoặc khi tỷ lệ log có `level: error` tăng đột biến, giúp phát hiện sự cố và hành vi bất thường ngay lập tức.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | ~1.02 GB |
| Multi-stage | ~271 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng giảm được (~750 MB) bao gồm:
1. **Base image tối giản:** Bản đầu dùng image đầy đủ `python:3.11` chứa cả hệ điều hành Debian hoàn chỉnh với nhiều công cụ build, tiện ích đồ họa và tài liệu hệ thống không cần thiết; trong khi bản multi-stage dùng `python:3.11-slim` chỉ giữ lại các thư viện runtime tối thiểu để chạy Python.
2. **Tách biệt môi trường build và runtime:** Stage `builder` chứa toàn bộ cache của pip, file tạm thời, công cụ biên dịch package C/C++. Khi đóng gói stage `runtime`, ta chỉ copy sản phẩm thư viện cuối cùng từ `/install` sang `/usr/local` với cờ `--no-cache-dir`, loại bỏ hoàn toàn các file rác và bộ công cụ build khỏi image production.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- Với Dockerfile hiện tại:
  - Do `requirements.txt` không đổi, các layer trước đó gồm `FROM`, `WORKDIR`, `COPY requirements.txt .`, `RUN pip install...` ở stage builder và layer copy dependencies ở runtime đều được tái sử dụng nguyên vẹn từ bộ nhớ đệm (`CACHED`).
  - Chỉ các layer từ `COPY app ./app` trở về sau mới bị thực thi lại. Thời gian build lại chỉ mất 1-2 giây.
- Nếu đặt `COPY . .` lên trước `RUN pip install`:
  - Mỗi lần sửa dù chỉ 1 ký tự trong mã nguồn, Docker sẽ phát hiện mã hash của context thay đổi và hủy toàn bộ cache từ lệnh `COPY . .` trở đi.
  - Hậu quả là lệnh `RUN pip install` bắt buộc phải chạy lại từ đầu: Docker phải tải lại toàn bộ dependencies từ Internet và cài đặt lại, khiến thời gian build kéo dài từ vài giây lên vài phút mỗi lần cập nhật code.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

- Chuỗi sự kiện khi container chạy với quyền root:
  1. Kẻ tấn công phát hiện lỗ hổng thực thi mã từ xa (RCE) hoặc Command Injection trong ứng dụng Python.
  2. Kẻ tấn công tiêm mã độc và chiếm quyền điều khiển shell bên trong container.
  3. Do container chạy mặc định bằng root, tiến trình shell này có quyền root (UID 0) trong container.
  4. Nếu kẻ tấn công kết hợp thêm lỗ hổng vượt rào container (container escape) như khai thác lỗ hổng Linux kernel, cấu hình sai Linux capabilities, hoặc volume mount nhầm Docker socket (`docker.sock`), tiến trình thoát ra ngoài máy host vẫn mang đặc quyền root (UID 0) của hệ điều hành host, chiếm toàn quyền kiểm soát máy chủ vật lý.
- Lệnh `USER appuser` cắt đứt chuỗi tại bước 3:
  - Tiến trình ứng dụng bị giới hạn ở quyền người dùng thông thường không có đặc quyền (UID 10001). Ngay cả khi chiếm được quyền thực thi mã trong container, kẻ tấn công chỉ có quyền hạn tối thiểu, không thể chỉnh sửa file hệ thống và nếu có thoát được ra ngoài host thì cũng chỉ là một unprivileged user, ngăn chặn nguy cơ leo thang đặc quyền chiếm máy host.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

- Số request tối đa có thể gửi trong 2 giây liên tiếp: **20 request** (gấp đôi hạn mức cho phép).
- Giải thích:
  - Với cơ chế đếm theo phút đồng hồ (fixed window reset tại giây 00), người dùng gửi 10 request vào thời điểm `10:00:59` (tiêu thụ hết hạn mức của phút 10:00).
  - Ngay ở giây tiếp theo `10:01:00`, đồng hồ bước sang phút mới và bộ đếm tự động reset về 0. Người dùng lập tức gửi tiếp 10 request nữa trong giây `10:01:00`.
  - Kết quả là chỉ trong khoảng thời gian vỏn vẹn 2 giây (từ 10:00:59 đến 10:01:00), hệ thống phải tiếp nhận tới 20 request mà không hề bị chặn.
  - Thuật toán Sliding Window khắc phục lỗ hổng này bằng cách luôn tính toán số lượng request trong đúng 60 giây gần nhất tính từ thời điểm gọi (`now - 60s`), đảm bảo bất kỳ khoảng thời gian 60 giây liên tục nào cũng không bao giờ vượt quá 10 request.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

- Khác biệt cốt lõi:
  - **Rate Limit:** Giới hạn **tần suất số lượng request** trong một khoảng thời gian ngắn (ví dụ: tối đa 10 request / 60 giây) nhằm bảo vệ hạ tầng máy chủ khỏi bị quá tải tài nguyên CPU/RAM và chống nghẽn mạng.
  - **Cost Guard:** Giới hạn **tổng chi phí tài chính tiêu lũy kế** trong chu kỳ dài (ví dụ: tối đa $10.0 / tháng) nhằm bảo vệ ngân sách chi trả cho các API bên ngoài (LLM) không bị cạn kiệt hoặc phát sinh chi phí ngoài ý muốn.
- Tình huống Rate limit cho qua nhưng Cost guard chặn:
  - Người dùng chỉ gửi duy nhất 1 request trong ngày (tần suất hoàn toàn hợp lệ đối với Rate limit). Tuy nhiên, request này chứa prompt tài liệu cực lớn khiến chi phí ước tính vượt quá hạn mức còn lại, hoặc người dùng đã sử dụng hết ngân sách $10.0 của tháng đó. Cost guard sẽ chặn ngay với mã `402 Payment Required`.
- Tình huống Cost guard cho qua nhưng Rate limit chặn:
  - Vào ngày đầu tháng, người dùng mới chi tiêu $0.05 / ngân sách $10.0 (còn dư rất nhiều tiền). Tuy nhiên người dùng chạy script gửi dồn dập 20 request chỉ trong 3 giây. Dù ngân sách hoàn toàn đủ chi trả, Rate limit sẽ lập tức can thiệp và trả về mã `429 Too Many Requests` từ request thứ 11 để ngăn chặn hành vi spam làm sập server.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Thứ tự chuỗi sự kiện sập dây chuyền (cascading failure):
1. Redis gặp sự cố tạm thời hoặc restart mạng, không thể kết nối trong 30 giây.
2. Endpoint gộp chung (đảm nhiệm cả vai trò liveness probe) kiểm tra kết nối Redis thất bại và trả về mã lỗi 503/500.
3. Bộ điều phối (Orchestrator như Docker Swarm / Kubernetes / Railway) nhận thấy liveness probe thất bại liên tục và kết luận toàn bộ 3 container agent đều đã bị treo/hỏng tiến trình.
4. Orchestrator đồng loạt phát lệnh tiêu diệt và restart lại cả 3 container agent cùng lúc.
5. Mọi request của người dùng đang được xử lý dở trên cả 3 container đều bị ngắt đột ngột, gây ra hàng loạt lỗi 502 Bad Gateway.
6. Khi Redis kết nối trở lại sau 30 giây, cả 3 container vẫn đang phải khởi động lại từ đầu (CrashLoop), kéo dài thời gian gián đoạn dịch vụ thay vì tự phục hồi ngay lập tức.
- Tách riêng `/health` (chỉ kiểm tra process FastAPI) giúp container không bị restart oan uổng; trong khi `/ready` báo 503 để load balancer tạm ngừng điều hướng traffic đến khi Redis hoạt động lại.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

- Nếu lịch sử được lưu trong biến dict/RAM cục bộ của từng process:
  - Load balancer phân bổ các request luân phiên qua 3 container A, B và C theo cơ chế Round-Robin:
    - Request 1 đến container A: A lưu vào RAM của A → `history_length` = 0.
    - Request 2 đến container B: RAM của B hoàn toàn rỗng → `history_length` = 0 (agent phản hồi như người lạ).
    - Request 3 đến container C: RAM của C cũng chưa có gì → `history_length` = 0.
    - Request 4 quay lại container A: A tìm thấy tin nhắn cũ → `history_length` = 2.
    - Request 5 quay lại container B: B tìm thấy tin nhắn cũ của B → `history_length` = 2.
  - Kết quả là `history_length` nhảy chập chờn, ngữ cảnh bị phân mảnh và agent liên tục bị "mất trí nhớ".
- Khi chuyển sang Redis tập trung: Cả 3 container đều truy xuất chung một nguồn dữ liệu trên Redis, giúp `history_length` tăng tuần tự và nhất quán: 0 → 2 → 4 → 6... bất kể request được xử lý bởi container nào.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- **Thông báo lỗi gặp phải:** Khi deploy lên Railway và gọi thử API, ban đầu gặp lỗi `404 Application not found`, sau đó khi sinh domain công khai thì endpoint `/ready` và `/ask` trả về `500 Internal Server Error`.
- **Cách tìm nguyên nhân:**
  1. Với lỗi 404: Nhận thấy URL điền vào tài liệu là đường dẫn giao diện quản trị (`railway.com/project/...`) thay vì Public domain có đuôi `.up.railway.app` được sinh ra từ mục Networking của service.
  2. Với lỗi 500: Xem xét luồng khởi chạy của FastAPI, các endpoint `/ready` và `/ask` đều tiêm dependency `get_settings()`. Trong Pydantic Settings của bài, trường `AGENT_API_KEY` là bắt buộc và không có giá trị mặc định theo thiết kế fail-fast. Do chưa thêm biến môi trường trên dashboard của Railway, hàm khởi tạo cấu hình ném ngoại lệ `ValidationError`, khiến server trả về mã lỗi 500.
- **Cách khắc phục:**
  1. Vào Railway Dashboard → Service Agent → Tab Settings → Networking → Chọn **Generate Domain** để nhận Public URL chính xác.
  2. Vào tab **Variables** của Service Agent trên Railway, khai báo đầy đủ các biến môi trường: `AGENT_API_KEY` (khóa bí mật), `REDIS_URL` (trỏ tới service Redis `day12-redis`), `RATE_LIMIT_PER_MINUTE=10`, `MONTHLY_BUDGET_USD=10.0`, `LOG_LEVEL=INFO`. Sau khi lưu, Railway tự động redeploy và service hoạt động bình thường, trả về `200 OK` cho cả `/health` và `/ready`.
