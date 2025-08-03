-- Subscription Plans
 
-- FAQ Categories
INSERT INTO "faq_categories" ("id", "name", "description", "order_index", "is_active", "created_at", "updated_at") VALUES
('a1b2c3d4-e5f6-4789-abcd-ef1234567890', 'Cơ Bản', 'Các câu hỏi thường gặp về dịch vụ và cách sử dụng cơ bản', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('b2c3d4e5-f6a7-4890-bcde-f12345678901', 'Tính Năng & Công Cụ', 'Thông tin về các tính năng và công cụ của dịch vụ', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('c3d4e5f6-a7b8-4901-cdef-123456789012', 'Gói Đăng Ký & Thanh Toán', 'Các vấn đề liên quan đến subscription và thanh toán', 3, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('d4e5f6a7-b8c9-4012-defa-234567890123', 'Bảo Mật & An Toàn', 'Thông tin về bảo mật và an toàn khi sử dụng dịch vụ', 4, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('e5f6a7b8-c9d0-4123-efab-345678901234', 'Hỗ Trợ Kỹ Thuật', 'Giải đáp các vấn đề kỹ thuật và hỗ trợ người dùng', 5, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('f6a7b8c9-d0e1-4234-fabc-456789012345', 'Tích Hợp & API', 'Hướng dẫn tích hợp và sử dụng API', 6, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Cơ Bản
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('11111111-1111-4111-a111-111111111111', 'Dịch vụ này là gì?', 'Đây là một nền tảng cung cấp các công cụ và tính năng để hỗ trợ doanh nghiệp trong việc quản lý và tối ưu hóa hoạt động kinh doanh.', 'Nền tảng được thiết kế để dễ sử dụng và phù hợp với mọi quy mô doanh nghiệp', 'a1b2c3d4-e5f6-4789-abcd-ef1234567890', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('11111111-2222-4111-a111-111111111111', 'Làm thế nào để bắt đầu sử dụng?', 'Để bắt đầu sử dụng, bạn chỉ cần: 1) Đăng ký tài khoản, 2) Chọn gói phù hợp, 3) Khám phá các tính năng, 4) Bắt đầu sử dụng ngay.', 'Chúng tôi cung cấp hướng dẫn chi tiết và video tutorial', 'a1b2c3d4-e5f6-4789-abcd-ef1234567890', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('11111111-3333-4111-a111-111111111111', 'Dịch vụ có hỗ trợ tiếng Việt không?', 'Có! Dịch vụ được thiết kế hoàn toàn bằng tiếng Việt với giao diện thân thiện và dễ sử dụng cho người Việt Nam.', 'Hỗ trợ khách hàng cũng có sẵn bằng tiếng Việt', 'a1b2c3d4-e5f6-4789-abcd-ef1234567890', 3, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Tính Năng & Công Cụ
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('22222222-1111-4111-a111-111111111111', 'Những tính năng chính nào được cung cấp?', 'Chúng tôi cung cấp nhiều tính năng: quản lý dự án, tạo nội dung, phân tích dữ liệu, tích hợp API, và nhiều công cụ hỗ trợ khác.', 'Mỗi tính năng được tối ưu để dễ sử dụng và hiệu quả', 'b2c3d4e5-f6a7-4890-bcde-f12345678901', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('22222222-2222-4111-a111-111111111111', 'Có thể tùy chỉnh giao diện không?', 'Có! Bạn có thể tùy chỉnh giao diện theo brand của mình, thay đổi màu sắc, logo, và layout để phù hợp với nhu cầu.', 'Tùy chỉnh giao diện có sẵn trong gói Pro và Business+', 'b2c3d4e5-f6a7-4890-bcde-f12345678901', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Gói Đăng Ký & Thanh Toán
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('33333333-1111-4111-a111-111111111111', 'Các gói đăng ký có những tính năng gì?', 'Gói Starter: Tính năng cơ bản, phù hợp cho cá nhân. Gói Pro: Tính năng nâng cao, thống kê chi tiết, tùy chỉnh. Gói Business+: Không giới hạn, API access, white-label, priority support.', 'Tất cả gói đều có thời gian dùng thử miễn phí 14 ngày', 'c3d4e5f6-a7b8-4901-cdef-123456789012', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('33333333-2222-4111-a111-111111111111', 'Có thể hủy đăng ký bất cứ lúc nào không?', 'Có! Bạn có thể hủy đăng ký bất cứ lúc nào từ trang Account Settings. Sau khi hủy, bạn vẫn có thể sử dụng dịch vụ đến hết chu kỳ thanh toán hiện tại.', 'Không có phí hủy dịch vụ', 'c3d4e5f6-a7b8-4901-cdef-123456789012', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Bảo Mật & An Toàn
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('44444444-1111-4111-a111-111111111111', 'Dữ liệu của tôi có được bảo mật không?', 'Có! Tất cả dữ liệu được mã hóa SSL/TLS 256-bit trong quá trình truyền tải và mã hóa AES-256 khi lưu trữ. Chỉ bạn mới có thể truy cập và chỉnh sửa dữ liệu của mình.', 'Chúng tôi tuân thủ các tiêu chuẩn bảo mật quốc tế', 'd4e5f6a7-b8c9-4012-defa-234567890123', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('44444444-2222-4111-a111-111111111111', 'Có thể thiết lập xác thực 2 lớp không?', 'Có! Chúng tôi hỗ trợ 2FA qua SMS, email, và authenticator apps. Bật 2FA để bảo vệ tài khoản khỏi truy cập trái phép.', '2FA là tính năng miễn phí cho tất cả người dùng', 'd4e5f6a7-b8c9-4012-defa-234567890123', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Hỗ Trợ Kỹ Thuật
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('55555555-1111-4111-a111-111111111111', 'Làm thế nào để liên hệ support?', 'Bạn có thể liên hệ qua: 1) Live chat trong website (24/7), 2) Email support@example.com, 3) Ticket system trong dashboard, 4) Hotline 1900-xxx-xxx (giờ hành chính).', 'Khách hàng Business+ có priority support với thời gian phản hồi < 1 giờ', 'e5f6a7b8-c9d0-4123-efab-345678901234', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('55555555-2222-4111-a111-111111111111', 'Tôi mất mật khẩu tài khoản, làm sao khôi phục?', 'Click "Forgot Password" ở trang đăng nhập, nhập email đăng ký, và làm theo hướng dẫn trong email nhận được. Nếu không nhận được email, kiểm tra spam folder.', 'Email reset password có hiệu lực trong 1 giờ', 'e5f6a7b8-c9d0-4123-efab-345678901234', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- FAQs for Tích Hợp & API
INSERT INTO "faqs" ("id", "question", "answer", "addition_info", "faq_category_id", "order_index", "is_active", "created_at", "updated_at") VALUES
('66666666-1111-4111-a111-111111111111', 'Có API để tích hợp với website/app của tôi không?', 'Có! Chúng tôi cung cấp RESTful API đầy đủ cho gói Business+. API cho phép tích hợp với hệ thống hiện tại của bạn.', 'API có rate limit 1000 requests/phút cho gói Business+', 'f6a7b8c9-d0e1-4234-fabc-456789012345', 1, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00'),
('66666666-2222-4111-a111-111111111111', 'Có thể white-label dịch vụ này không?', 'Có! Gói Business+ hỗ trợ complete white-label: domain riêng, branding riêng, ẩn logo của chúng tôi.', 'White-label bao gồm cả API documentation và support materials', 'f6a7b8c9-d0e1-4234-fabc-456789012345', 2, true, '2025-06-24 20:30:00', '2025-06-24 20:30:00');

-- Blog Categories
INSERT INTO "blogs_categories" ("id", "name", "slug", "description", "created_at", "updated_at") VALUES
('11111111-1111-1111-1111-111111111111', 'Hướng Dẫn Sử Dụng', 'huong-dan-su-dung', 'Các bài hướng dẫn chi tiết cách sử dụng dịch vụ và các tính năng', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-2222-2222-2222-222222222222', 'Marketing & Business', 'marketing-business', 'Chiến lược và tips marketing hiệu quả cho doanh nghiệp', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-3333-3333-3333-333333333333', 'Xu Hướng & Công Nghệ', 'xu-huong-cong-nghe', 'Những xu hướng mới và công nghệ trong ngành', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-4444-4444-4444-444444444444', 'Case Study', 'case-study', 'Những câu chuyện thành công và nghiên cứu trường hợp thực tế', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-5555-5555-5555-555555555555', 'Tips & Tricks', 'tips-tricks', 'Các mẹo hay và thủ thuật sử dụng hiệu quả', '2025-01-15 10:00:00', '2025-01-15 10:00:00');

-- Blog Tags
INSERT INTO "blogs_tags" ("id", "name", "slug", "created_at", "updated_at") VALUES
('11111111-1111-1111-1111-111111111111', 'Business Tools', 'business-tools', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-2222-2222-2222-222222222222', 'Marketing Digital', 'marketing-digital', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-3333-3333-3333-333333333333', 'Business Strategy', 'business-strategy', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-4444-4444-4444-444444444444', 'Technology', 'technology', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-5555-5555-5555-555555555555', 'Productivity', 'productivity', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-6666-6666-6666-666666666666', 'Customer Experience', 'customer-experience', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-7777-7777-7777-777777777777', 'Analytics', 'analytics', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-8888-8888-8888-888888888888', 'API Integration', 'api-integration', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-9999-9999-9999-999999999999', 'E-commerce', 'e-commerce', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Startup', 'startup', '2025-01-15 10:00:00', '2025-01-15 10:00:00');

-- Blog Author Profiles
INSERT INTO "blogs_user_author_profiles" ("id", "user_id", "display_name", "bio", "avatar_url", "is_active", "created_at", "updated_at") VALUES
('11111111-1111-1111-1111-111111111111', '64b8a5db-83b1-4d84-b279-3324e090ec04', 'Minh Lê Expert', 'Chuyên gia về Business và Marketing Digital với hơn 5 năm kinh nghiệm. Đã giúp hàng trăm doanh nghiệp tối ưu hóa hoạt động kinh doanh.', '/blog-assets/avatars/minh-le-expert.jpg', true, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-2222-2222-2222-222222222222', '64b8a5db-83b1-4d84-b279-3324e090ec04', 'Anna Nguyễn', 'Marketing Manager và Content Creator. Chuyên viết về trends công nghệ và customer experience trong kỷ nguyên số.', '/blog-assets/avatars/anna-nguyen.jpg', true, '2025-01-15 10:00:00', '2025-01-15 10:00:00');

-- Blog Posts
INSERT INTO "blogs_posts" ("id", "author_profile_id", "title", "slug", "summary", "content", "thumbnail_url", "thumbnail_compressed_url", "is_featured", "is_hot", "status", "published_at", "view_count", "seo_title", "seo_description", "created_at", "updated_at") VALUES
('11111111-1111-1111-1111-111111111111', '11111111-2222-2222-2222-222222222222', 'Hướng Dẫn Sử Dụng Dịch Vụ Hiệu Quả 2025', 'huong-dan-su-dung-dich-vu-hieu-qua-2025', 'Khám phá cách sử dụng dịch vụ một cách hiệu quả nhất, tối ưu hóa quy trình làm việc và tăng năng suất cho doanh nghiệp.', '# Hướng Dẫn Sử Dụng Dịch Vụ Hiệu Quả 2025', '/blog-assets/thumbnails/guide-service.jpg', '/blog-assets/thumbnails/guide-service-compressed.jpg', true, true, 'published', '2025-01-15 10:00:00', 1250, 'Hướng Dẫn Sử Dụng Dịch Vụ Hiệu Quả 2025 | Business Platform', 'Hướng dẫn sử dụng dịch vụ hiệu quả, tối ưu hóa quy trình làm việc và tăng năng suất cho doanh nghiệp.', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),

('11111111-1111-1111-1111-111111111112', '11111111-2222-2222-2222-222222222222', '10 Chiến Lược Marketing Tăng Doanh Thu 300%', '10-chien-luoc-marketing-tang-doanh-thu', 'Khám phá 10 chiến lược marketing được chứng minh hiệu quả, giúp doanh nghiệp tăng doanh thu lên đến 300% trong 6 tháng.', '# 10 Chiến Lược Marketing Tăng Doanh Thu 300%', '/blog-assets/thumbnails/marketing-strategies.jpg', '/blog-assets/thumbnails/marketing-strategies-compressed.jpg', true, false, 'published', '2025-01-16 10:00:00', 890, '10 Chiến Lược Marketing Tăng Doanh Thu 300% | Business Platform', 'Khám phá 10 chiến lược marketing hiệu quả giúp doanh nghiệp tăng doanh thu lên đến 300% trong 6 tháng.', '2025-01-16 10:00:00', '2025-01-16 10:00:00');

-- Blog Post Categories
INSERT INTO "blogs_post_categories" ("post_id", "category_id", "created_at") VALUES
('11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', '2025-01-15 10:00:00'),
('11111111-1111-1111-1111-111111111112', '11111111-2222-2222-2222-222222222222', '2025-01-16 10:00:00');

-- Blog Post Tags
INSERT INTO "blogs_post_tags" ("post_id", "tag_id", "created_at") VALUES
('11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', '2025-01-15 10:00:00'),
('11111111-1111-1111-1111-111111111111', '11111111-5555-5555-5555-555555555555', '2025-01-15 10:00:00'),
('11111111-1111-1111-1111-111111111112', '11111111-2222-2222-2222-222222222222', '2025-01-16 10:00:00'),
('11111111-1111-1111-1111-111111111112', '11111111-3333-3333-3333-333333333333', '2025-01-16 10:00:00');

-- Support Ticket Categories
INSERT INTO "support_ticket_categories" ("id", "name", "description", "is_active", "is_internal", "created_at", "updated_at") VALUES
('11111111-1111-1111-1111-111111111111', 'Kỹ Thuật', 'Các vấn đề kỹ thuật và lỗi hệ thống', true, false, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-2222-2222-2222-222222222222', 'Tài Khoản', 'Vấn đề về tài khoản và đăng nhập', true, false, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-3333-3333-3333-333333333333', 'Thanh Toán', 'Vấn đề về thanh toán và gói dịch vụ', true, false, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-4444-4444-4444-444444444444', 'Tính Năng', 'Hỏi đáp về tính năng và cách sử dụng', true, false, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-5555-5555-5555-555555555555', 'Khác', 'Các vấn đề khác không thuộc danh mục trên', true, false, '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('11111111-6666-6666-6666-666666666666', 'Nội Bộ', 'Các vấn đề nội bộ cho staff', true, true, '2025-01-15 10:00:00', '2025-01-15 10:00:00');
