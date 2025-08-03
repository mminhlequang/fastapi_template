# Hướng dẫn Setup CI/CD với GitHub Actions

## Tổng quan
Hướng dẫn triển khai CI/CD tự động deploy từ GitHub repo lên VPS sử dụng Docker và GitHub Actions.

## Các bước thực hiện

### 1. Tạo SSH Key cho GitHub Actions
```bash
ssh-keygen -t rsa -b 4096 -C "github-ci" -f ~/.ssh/github_ci_key
```

**Kết quả:**
- `github_ci_key`: Private key (add vào GitHub Secret)
- `github_ci_key.pub`: Public key (add vào VPS)

### 2. Cấu hình VPS
```bash
mkdir -p ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Lưu ý:** Copy nội dung từ file `github_ci_key.pub` và paste vào thay cho `PASTE_PUBLIC_KEY_HERE`

### 3. Thêm GitHub Secrets
Vào GitHub → Settings → Secrets → Actions → New repository secret

| Name | Value |
|------|-------|
| `VPS_HOST` | IP hoặc domain VPS |
| `VPS_USER` | Tài khoản SSH (ví dụ: root) |
| `SSH_PRIVATE_KEY` | Nội dung của file `github_ci_key` |

### 4. Tạo GitHub Actions Workflow
File: `.github/workflows/deploy.yml`


**Lưu ý quan trọng:** 
- Thay đổi `/path/to/your/app` thành đường dẫn thực tế đến thư mục chứa docker project trên VPS
- Đảm bảo VPS đã clone repo về trước khi chạy workflow

## Kiểm tra
Sau khi setup xong:
1. Push code lên branch `main`
2. Kiểm tra GitHub Actions tab để xem workflow chạy
3. Kiểm tra ứng dụng trên VPS đã được deploy thành công

## Troubleshooting
- Kiểm tra SSH connection: `ssh -i ~/.ssh/github_ci_key user@vps_ip`
- Kiểm tra quyền file: `chmod 600 ~/.ssh/authorized_keys`
- Kiểm tra logs GitHub Actions để debug lỗi
