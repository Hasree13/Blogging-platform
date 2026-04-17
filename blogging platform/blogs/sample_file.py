-- ==============================================================================
-- 1. CLEANUP (Safely clear existing data to prevent conflicts during testing)
-- ==============================================================================
TRUNCATE TABLE users, categories, publications, blogs CASCADE;

-- ==============================================================================
-- 2. USERS (30 Users: 1 Admin, 15 Authors, 14 Readers)
-- ==============================================================================
INSERT INTO public.users (user_id, first_name, last_name, email_id, password, premium)
OVERRIDING SYSTEM VALUE VALUES
(1, 'System', 'Admin', 'admin@platform.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
-- Authors (2 to 16)
(2, 'Ada', 'Lovelace', 'ada@dev.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(3, 'Linus', 'Torvalds', 'linus@kernel.org', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(4, 'Grace', 'Hopper', 'grace@compiler.net', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(5, 'Alan', 'Turing', 'alan@ai.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(6, 'Margaret', 'Hamilton', 'margaret@apollo.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(7, 'Tim', 'Berners-Lee', 'tim@web.org', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(8, 'Guido', 'van Rossum', 'guido@python.org', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(9, 'Dennis', 'Ritchie', 'dennis@c.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(10, 'Ken', 'Thompson', 'ken@unix.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(11, 'Bjarne', 'Stroustrup', 'bjarne@cpp.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(12, 'James', 'Gosling', 'james@java.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(13, 'Brendan', 'Eich', 'brendan@js.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(14, 'John', 'Carmack', 'john@id.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(15, 'Satoshi', 'Nakamoto', 'satoshi@crypto.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(16, 'David', 'Patterson', 'david@riscv.org', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
-- Readers (17 to 30)
(17, 'Reader', 'One', 'reader1@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(18, 'Reader', 'Two', 'reader2@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(19, 'Reader', 'Three', 'reader3@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(20, 'Reader', 'Four', 'reader4@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(21, 'Reader', 'Five', 'reader5@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(22, 'Reader', 'Six', 'reader6@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(23, 'Reader', 'Seven', 'reader7@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(24, 'Reader', 'Eight', 'reader8@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(25, 'Reader', 'Nine', 'reader9@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(26, 'Reader', 'Ten', 'reader10@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 1),
(27, 'Reader', 'Eleven', 'reader11@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(28, 'Reader', 'Twelve', 'reader12@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(29, 'Reader', 'Thirteen', 'reader13@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0),
(30, 'Reader', 'Fourteen', 'reader14@test.com', 'pbkdf2_sha256$1200000$dH74b3bVkFvORK33czuGlT$iFyrrFDZ4b/vU0GMCVYOhgg1xEfyBL1tx9zf3P/ZGCA=', 0);

-- ==============================================================================
-- 3. ADMINS (1 Fixed Admin)
-- ==============================================================================
INSERT INTO public.admins (admin_id, role, salary) VALUES (1, 'super_admin', 75000);

-- ==============================================================================
-- 4. CATEGORIES
-- ==============================================================================
INSERT INTO public.categories (category_id, category_name)
OVERRIDING SYSTEM VALUE VALUES
(1, 'Web Development'),
(2, 'Computer Architecture'),
(3, 'Artificial Intelligence'),
(4, 'Personal Finance'),
(5, 'Campus & Events');

-- ==============================================================================
-- 5. SUBSCRIPTIONS (4 Monthly, 6 Yearly)
-- ==============================================================================
INSERT INTO public.subscriptions (sub_id, user_id, plan_type, start_date, end_date, amount)
OVERRIDING SYSTEM VALUE VALUES
-- 4 Monthly
(1, 17, 'monthly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 month', 199),
(2, 18, 'monthly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 month', 199),
(3, 19, 'monthly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 month', 199),
(4, 20, 'monthly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 month', 199),
-- 6 Yearly
(5, 21, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999),
(6, 22, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999),
(7, 23, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999),
(8, 24, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999),
(9, 25, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999),
(10, 26, 'yearly', CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 1999);

-- ==============================================================================
-- 6. AUTHORS & PUBLICATIONS
-- ==============================================================================
-- Step A: Insert 15 authors first (without publications to avoid FK cycle)
INSERT INTO public.authors (author_id, publi_id)
SELECT user_id, NULL FROM users WHERE user_id BETWEEN 2 AND 16;

-- Step B: Create 3 Publications owned by Authors 2, 3, and 4
INSERT INTO public.publications (publi_id, publi_name, date_of_joining, owner_id)
OVERRIDING SYSTEM VALUE VALUES
(1, 'The Full Stack Dev', CURRENT_DATE, 2),
(2, 'Silicon & Circuits', CURRENT_DATE, 3),
(3, 'Campus Chronicles', CURRENT_DATE, 4);

-- Step C: Assign authors to publications (~10 authors mapped)
UPDATE public.authors SET publi_id = 1 WHERE author_id IN (2, 5, 8, 13);
UPDATE public.authors SET publi_id = 2 WHERE author_id IN (3, 9, 10, 16);
UPDATE public.authors SET publi_id = 3 WHERE author_id IN (4, 6, 7);
-- Authors 11, 12, 14, 15 remain independent (publi_id is NULL)

-- ==============================================================================
-- 7. BLOGS (10 Specific handcrafted, 50 auto-generated = 60 Published, + 10 Drafts)
-- ==============================================================================
INSERT INTO public.blogs (blog_id, title, content, author_id, update_datetime, status, is_premium)
OVERRIDING SYSTEM VALUE VALUES
-- 10 Specific High-Quality Blogs
(1, 'Mastering Django ORM and Supabase Integration', 'A deep dive into connecting your Django backend with PostgreSQL on Supabase...', 8, CURRENT_TIMESTAMP - INTERVAL '1 day', 1, false),
(2, 'Understanding RISC-V Compressed Instructions (RVC)', 'How RVC improves code density and instruction fetch bandwidth in modern processors.', 16, CURRENT_TIMESTAMP - INTERVAL '2 days', 1, true),
(3, 'AI Defect Detection in Wafer Fabrication', 'Using convolutional neural networks to identify microscopic flaws during chip mass production.', 5, CURRENT_TIMESTAMP - INTERVAL '3 days', 1, true),
(4, 'Amdahl''s Law: Calculating True CPU Performance Gains', 'Why throwing more cores at a problem does not always result in linear speedups.', 9, CURRENT_TIMESTAMP - INTERVAL '4 days', 1, false),
(5, 'Top 5 Mutual Funds for Tech Professionals (5-Year Horizon)', 'Strategies for short-term stock trading and long-term wealth building.', 15, CURRENT_TIMESTAMP - INTERVAL '5 days', 1, true),
(6, 'Organizing "Aetervanza": Branding a College Fest', 'How to choose majestic names with Latin roots and secure sponsorships from tech companies.', 4, CURRENT_TIMESTAMP - INTERVAL '6 days', 1, false),
(7, 'MATLAB Custom Diagrams for Network Routing', 'Generating precise graph edges and complex topologies for research papers.', 6, CURRENT_TIMESTAMP - INTERVAL '7 days', 1, false),
(8, 'Optimizing NPU Hardware with LLVM', 'A look at high-level AI hardware programming frameworks.', 11, CURRENT_TIMESTAMP - INTERVAL '8 days', 1, true),
(9, 'Bangalore Groundwater Depletion: Urban Hydrology', 'An analysis of the dropping water tables and authoritative sources on the crisis.', 7, CURRENT_TIMESTAMP - INTERVAL '9 days', 1, false),
(10, 'Fixing Asus Vivobook 5 Touchpad Issues', 'Hardware maintenance tips and driver resets for common laptop problems.', 2, CURRENT_TIMESTAMP - INTERVAL '10 days', 1, false);

-- Generate 50 more published blogs dynamically to reach 60
INSERT INTO public.blogs (title, content, author_id, update_datetime, status, is_premium)
SELECT 
    'Generated Blog Title ' || i,
    'This is auto-generated content for testing the blog grid layout, pagination, and database scale. Blog number: ' || i,
    (i % 15) + 2, -- Loops through authors 2 to 16
    CURRENT_TIMESTAMP - (i || ' hours')::interval,
    1,
    (i % 4 = 0) -- Every 4th blog is premium
FROM generate_series(11, 60) AS i;

-- Generate 10 Drafts
INSERT INTO public.blogs (title, content, author_id, update_datetime, status, is_premium)
SELECT 
    'Draft Concept: ' || i, 'Still working on this...', (i % 15) + 2, CURRENT_TIMESTAMP, 0, false
FROM generate_series(61, 70) AS i;

-- ==============================================================================
-- 8. MAP CATEGORIES & KEYWORDS
-- ==============================================================================
-- Map the 10 specific blogs to categories
INSERT INTO public.blog_categories (blog_id, category_id) VALUES
(1, 1), (2, 2), (3, 3), (3, 2), (4, 2), (5, 4), (6, 5), (7, 1), (8, 3), (9, 5), (10, 1);

-- Dynamically map categories for the remaining 50 published blogs
INSERT INTO public.blog_categories (blog_id, category_id)
SELECT blog_id, (blog_id % 5) + 1 FROM blogs WHERE blog_id > 10 AND status = 1;

-- Some Keywords
INSERT INTO public.blog_keywords (blog_id, keyword) VALUES
(1, 'Django'), (1, 'SQL'), (2, 'RISC-V'), (3, 'Semiconductors'), (6, 'Sponsorships');

-- ==============================================================================
-- 9. USER INTERACTIONS (Likes, Bookmarks, Comments, Followers)
-- ==============================================================================
-- Interested Categories
INSERT INTO public.interested_categories (user_id, category_id)
SELECT u, c FROM generate_series(17, 30) u, generate_series(1, 3) c WHERE (u + c) % 2 = 0;

-- Author Followers (Readers following Authors)
INSERT INTO public.author_followers (user_id, author_id)
SELECT u, a FROM generate_series(17, 30) u, generate_series(2, 5) a WHERE (u + a) % 3 = 0;

-- Publication Followers
INSERT INTO public.publication_followers (user_id, publi_id)
SELECT u, p FROM generate_series(17, 30) u, generate_series(1, 3) p WHERE (u + p) % 2 = 0;

-- Likes (Randomized spread)
INSERT INTO public.likes (user_id, blog_id)
SELECT u, b FROM generate_series(2, 30) u, generate_series(1, 60) b WHERE (u * b) % 11 = 0;

-- Bookmarks
INSERT INTO public.booklist (user_id, blog_id)
SELECT u, b FROM generate_series(17, 30) u, generate_series(1, 20) b WHERE (u + b) % 7 = 0;

-- Comments
INSERT INTO public.comments (description, blog_id, user_id, creation_datetime)
SELECT 
    'Great insight! Thanks for sharing this.', b, u, CURRENT_TIMESTAMP
FROM generate_series(20, 30) u, generate_series(1, 10) b;

-- Donations (Readers donating to premium authors)
INSERT INTO public.donations (user_id, author_id, blog_id, amount)
VALUES 
(21, 16, 2, 500),
(22, 5, 3, 1000),
(25, 15, 5, 250);

-- Reports (A couple of test reports for the Admin Dashboard)
INSERT INTO public.reports (user_id, blog_id, type_of_report, description, status)
VALUES 
(28, 12, 'Spam', 'This auto-generated blog looks like spam.', 'new'),
(29, 15, 'Plagiarism', 'Copied from Wikipedia without citation.', 'new');

-- ==============================================================================
-- 10. CRITICAL: RESET SEQUENCES
-- ==============================================================================
-- Because we forced specific IDs using OVERRIDING SYSTEM VALUE, we MUST tell 
-- PostgreSQL to update its internal counters so your app doesn't crash on the next INSERT.
SELECT setval(pg_get_serial_sequence('users', 'user_id'), coalesce(max(user_id), 1), max(user_id) IS NOT null) FROM users;
SELECT setval(pg_get_serial_sequence('categories', 'category_id'), coalesce(max(category_id), 1), max(category_id) IS NOT null) FROM categories;
SELECT setval(pg_get_serial_sequence('subscriptions', 'sub_id'), coalesce(max(sub_id), 1), max(sub_id) IS NOT null) FROM subscriptions;
SELECT setval(pg_get_serial_sequence('publications', 'publi_id'), coalesce(max(publi_id), 1), max(publi_id) IS NOT null) FROM publications;
SELECT setval(pg_get_serial_sequence('publication_join_requests', 'request_id'), coalesce(max(request_id), 1), max(request_id) IS NOT null) FROM publication_join_requests;
SELECT setval(pg_get_serial_sequence('blogs', 'blog_id'), coalesce(max(blog_id), 1), max(blog_id) IS NOT null) FROM blogs;
SELECT setval(pg_get_serial_sequence('comments', 'comment_id'), coalesce(max(comment_id), 1), max(comment_id) IS NOT null) FROM comments;
SELECT setval(pg_get_serial_sequence('donations', 'donation_id'), coalesce(max(donation_id), 1), max(donation_id) IS NOT null) FROM donations;
SELECT setval(pg_get_serial_sequence('reports', 'report_id'), coalesce(max(report_id), 1), max(report_id) IS NOT null) FROM reports;