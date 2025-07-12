# Firebase Phone Authentication Integration

## Tổng quan

Dự án đã được tích hợp Firebase Phone authentication như một social provider trong hệ thống social login hiện có. Người dùng có thể đăng nhập bằng số điện thoại thông qua Firebase, tương tự như đăng nhập bằng Facebook/Google.

## Cấu hình

### 1. Firebase Service Account

Tạo file `firebase-service-account.json` trong thư mục gốc của dự án với thông tin service account từ Firebase Console:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40your-project-id.iam.gserviceaccount.com"
}
```

### 2. Environment Variables

Thêm cấu hình Firebase vào file `.env`:

```env
FIREBASE_SERVICE_ACCOUNT_FILE=firebase-service-account.json
```

## API Endpoints

### Social Login với Firebase Phone

**Endpoint:** `POST /api/v1/users/auth/social/login`

**Request Body:**
```json
{
  "provider": "firebase_phone",
  "access_token": "firebase_id_token_from_client"
}
```

**Response:**
```json
{
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token"
}
```

## Cách hoạt động

1. **Client Side (Frontend):**
   - Sử dụng Firebase SDK để gửi OTP đến số điện thoại
   - Verify OTP và nhận Firebase ID token
   - Gửi ID token lên backend

2. **Server Side (Backend):**
   - Verify Firebase ID token
   - Extract phone number từ token
   - Tìm hoặc tạo user với phone number
   - Tạo social account link
   - Trả về JWT access/refresh token

## Luồng xử lý

1. Client gửi request với `provider: "firebase_phone"` và `access_token` (Firebase ID token)
2. Backend verify Firebase token
3. Extract phone number từ token
4. Kiểm tra social account đã tồn tại chưa
5. Nếu chưa có:
   - Tìm user theo phone number
   - Nếu không tìm thấy, tạo user mới
   - Tạo social account link
6. Trả về JWT tokens

## Lưu ý

- Firebase xử lý toàn bộ OTP verification ở client
- Backend chỉ verify Firebase ID token
- Phone number được lưu trong user profile
- Social account được tạo với provider "firebase_phone"
- User có thể link/unlink Firebase Phone account như các social provider khác

## Dependencies

Đã thêm `firebase-admin` vào `pyproject.toml`:

```toml
"firebase-admin<7.0.0,>=6.4.0"
```

## Testing

Để test Firebase Phone authentication:

1. Setup Firebase project với Phone Authentication enabled
2. Tạo service account và download JSON file
3. Đặt file JSON vào thư mục gốc dự án
4. Test API endpoint với Firebase ID token hợp lệ 