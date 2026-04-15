from django.shortcuts import render, redirect
from blog_platform.db import get_connection
from datetime import datetime
import re
from django.contrib import messages
from datetime import datetime, timedelta, date
from django.views.decorators.cache import cache_control

STOPWORDS = {
    "is", "the", "a", "an", "of", "and", "or", "to",
    "in", "on", "at", "for", "with", "by", "this",
    "that", "it", "as", "are", "was", "were","be","been","what","how"
}

def extract_keywords(title):
    # lowercase
    title = title.lower()

    # remove punctuation
    title = re.sub(r'[^\w\s]', '', title)

    words = title.split()

    # remove stopwords
    keywords = [w for w in words if w not in STOPWORDS]
    keywords = list(set(keywords))  # remove duplicates

    return keywords

def home(request):
    if not request.session.get('user_id'):
        return redirect('/login')
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            b.blog_id,          -- 0
            b.title,            -- 1
            b.content,          -- 2
            u.first_name,       -- 3
            u.last_name,        -- 4
            b.update_datetime,  -- 5
            b.author_id,        -- 6
            COUNT(DISTINCT l.user_id) AS no_of_likes,       -- 7
            COUNT(DISTINCT c.comment_id) AS no_of_comments, -- 8
            b.is_premium,       -- 9
            p.publi_name,       -- 10
            p.publi_id,          -- 11 (NEW: For the clickable link)
            u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN likes l ON b.blog_id = l.blog_id
        LEFT JOIN comments c ON b.blog_id = c.blog_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE b.status = 1
        GROUP BY 
            b.blog_id, b.title, b.content,
            u.first_name, u.last_name,
            b.update_datetime, b.author_id,
            b.is_premium, p.publi_name, p.publi_id, u.avatar_id
        ORDER BY b.update_datetime DESC
    """)

    blogs = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "home.html", {"blogs": blogs})

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def blog_detail(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message
    

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT b.blog_id, b.title, b.content,
           b.author_id, u.first_name, u.last_name,
           b.update_datetime, p.publi_name, b.is_premium, u.avatar_id
    FROM blogs b
    JOIN users u ON b.author_id = u.user_id
    LEFT JOIN authors a ON b.author_id = a.author_id
    LEFT JOIN publications p ON a.publi_id = p.publi_id
    WHERE b.blog_id = %s
    """, (blog_id,))

    blog = cur.fetchone()

    blog_is_premium = blog[8]   

    # PROTECT PREMIUM BLOG
    from blog_platform.utils import is_premium_user

    is_user_premium=is_premium_user(user_id)

    cur.execute("""
        SELECT c.description, u.first_name, u.avatar_id
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.blog_id = %s
    """, (blog_id,))

    comments = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) FROM likes WHERE blog_id=%s
    """, (blog_id,))

    likes = cur.fetchone()[0]

    cur.execute("""
    SELECT c.category_name
    FROM blog_categories bc
    JOIN categories c ON bc.category_id = c.category_id
    WHERE bc.blog_id = %s
    """, (blog_id,))

    categories = cur.fetchall()

    # check like
    cur.execute("""
        SELECT 1 FROM likes
        WHERE user_id=%s AND blog_id=%s
    """, (user_id, blog_id))
    liked = cur.fetchone() is not None

    # check bookmark
    cur.execute("""
        SELECT 1 FROM booklist
        WHERE user_id=%s AND blog_id=%s
    """, (user_id, blog_id))
    bookmarked = cur.fetchone() is not None

    # check follow
    cur.execute("""
        SELECT 1 FROM author_followers
        WHERE user_id=%s AND author_id=%s
    """, (user_id, blog[3]))
    followed = cur.fetchone() is not None

    # not own blog
    show_donate = False
    if user_id and blog:
        if user_id != blog[3]:   
            show_donate = True

    cur.close()
    conn.close()

    content = blog[2]

    preview = content[:100]
    remaining = content[100:]

    return render(request, "blog_detail.html", {
        "blog": blog,
        "comments": comments,
        "likes": likes,
        "categories":categories,
        "liked": liked,
        "bookmarked": bookmarked,
        "followed": followed,
        "show_donate":show_donate,
        "user_id":user_id,
        "preview": preview,
        "remaining": remaining,
        "is_premium": blog_is_premium,  
        "is_subscribed": is_user_premium,
    })


def like_blog(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    # check if already liked
    cur.execute("""
        SELECT * FROM likes
        WHERE user_id=%s AND blog_id=%s
    """, (user_id, blog_id))

    exists = cur.fetchone()

    if exists:
        # unlike
        cur.execute("""
            DELETE FROM likes
            WHERE user_id=%s AND blog_id=%s
        """, (user_id, blog_id))
    else:
        # like
        cur.execute("""
            INSERT INTO likes (user_id, blog_id)
            VALUES (%s, %s)
        """, (user_id, blog_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f'/blog/{blog_id}/')


def add_comment(request, blog_id):
    if request.method == "POST":
        content = request.POST['content']
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login') # Or return an error message


        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO comments (description, blog_id, user_id, creation_datetime)
            VALUES (%s, %s, %s, NOW())
        """, (content, blog_id, user_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(f'/blog/{blog_id}/')

    return redirect(f'/blog/{blog_id}/')

def follow_author(request, author_id, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    if user_id == author_id:
        return redirect(f'/blog/{blog_id}')
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM author_followers
        WHERE user_id=%s AND author_id=%s
    """, (user_id, author_id))

    exists = cur.fetchone()

    if exists:
        # unfollow
        cur.execute("""
            DELETE FROM author_followers
            WHERE user_id=%s AND author_id=%s
        """, (user_id, author_id))
    else:
        # follow
        cur.execute("""
            INSERT INTO author_followers (author_id, user_id)
            VALUES (%s, %s)
        """, (author_id, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f'/blog/{blog_id}')

def follow_publication(request, publi_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM publication_followers
        WHERE user_id=%s AND publi_id=%s
    """, (user_id, publi_id))

    exists = cur.fetchone()

    if exists:
        cur.execute("""
            DELETE FROM publication_followers
            WHERE user_id=%s AND publi_id=%s
        """, (user_id, publi_id))
    else:
        cur.execute("""
            INSERT INTO publication_followers (user_id, publi_id)
            VALUES (%s, %s)
        """, (user_id, publi_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f'/publication/{publi_id}/')

def bookmark_blog(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM booklist
        WHERE user_id=%s AND blog_id=%s
    """, (user_id, blog_id))

    exists = cur.fetchone()

    if exists:
        # remove bookmark
        cur.execute("""
            DELETE FROM booklist
            WHERE user_id=%s AND blog_id=%s
        """, (user_id, blog_id))
    else:
        # add bookmark
        cur.execute("""
            INSERT INTO booklist (user_id, blog_id)
            VALUES (%s, %s)
        """, (user_id, blog_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f'/blog/{blog_id}/')

def library(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    # Bookmarks
    cur.execute("""
        SELECT b.blog_id, b.title
        FROM booklist bl
        JOIN blogs b ON bl.blog_id = b.blog_id
        WHERE bl.user_id=%s
    """, (user_id,))
    bookmarks = cur.fetchall()

    # Likes
    cur.execute("""
        SELECT b.blog_id, b.title
        FROM likes l
        JOIN blogs b ON l.blog_id = b.blog_id
        WHERE l.user_id=%s
    """, (user_id,))
    likes = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "library.html", {
        "bookmarks": bookmarks,
        "likes": likes
    })

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def write(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    #  check if author
    cur.execute("""
        SELECT * FROM authors WHERE author_id=%s
    """, (user_id,))
    is_author = cur.fetchone()

    if not is_author:
        cur.close()
        conn.close()
        return render(request, "not_author.html")

    #  get categories
    cur.execute("SELECT category_id, category_name FROM categories")
    categories = cur.fetchall()

    if request.method == "POST":
        title = request.POST['title']
        content = request.POST['content']
        action = request.POST['action']
        selected_categories = request.POST.getlist('categories')
        is_premium = request.POST.get('is_premium') == 'on'

        if action == "publish":
            cur.execute("""
                INSERT INTO blogs (title, content, author_id, update_datetime, status, is_premium)
                VALUES (%s, %s, %s, NOW(), %s, %s)
                RETURNING blog_id
            """, (title, content, user_id, 1, is_premium))
            
            blog_id = cur.fetchone()[0]

            # categories
            for cat in selected_categories:
                cur.execute("""
                    INSERT INTO blog_categories (blog_id, category_id)
                    VALUES (%s, %s)
                """, (blog_id, cat))

            # keywords
            keywords = extract_keywords(title)
            for kw in keywords:
                cur.execute("""
                    INSERT INTO blog_keywords (blog_id, keyword)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (blog_id, kw))

        else:
            cur.execute("""
                INSERT INTO blogs (title, content, author_id, update_datetime, status, is_premium)
                VALUES (%s, %s, %s, NOW(), %s, %s)
                RETURNING blog_id
            """, (title, content, user_id, 0, is_premium))

            blog_id = cur.fetchone()[0]

            for cat in selected_categories:
                cur.execute("""
                    INSERT INTO blog_categories (blog_id, category_id)
                    VALUES (%s, %s)
                """, (blog_id, cat))

        conn.commit()
        cur.close()
        conn.close()
        return redirect('/home')

    cur.close()
    conn.close()
    return render(request, "write.html", {"categories": categories})

def stories(request):
    if not request.session.get('user_id'):
        return redirect('/login')
        
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    # Drafts (status = 0)
    cur.execute("""
        SELECT 
            b.blog_id,          -- 0
            b.title,            -- 1
            b.content,          -- 2
            u.first_name,       -- 3
            u.last_name,        -- 4
            b.update_datetime,  -- 5
            b.author_id,        -- 6
            0,                  -- 7 (placeholder for likes)
            0,                  -- 8 (placeholder for comments)
            b.is_premium,       -- 9
            p.publi_name,       -- 10
            p.publi_id,          -- 11
            u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE b.author_id = %s AND b.status = 0
        ORDER BY b.update_datetime DESC
    """, (user_id,))
    drafts = cur.fetchall()

    # Published (status = 1) - UPDATED QUERY
    cur.execute("""
        SELECT 
            b.blog_id,          -- 0
            b.title,            -- 1
            b.content,          -- 2
            u.first_name,       -- 3
            u.last_name,        -- 4
            b.update_datetime,  -- 5
            b.author_id,        -- 6
            (SELECT COUNT(*) FROM likes WHERE blog_id = b.blog_id),    -- 7
            (SELECT COUNT(*) FROM comments WHERE blog_id = b.blog_id), -- 8
            b.is_premium,       -- 9
            p.publi_name,       -- 10
            p.publi_id,          -- 11
            u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE b.author_id = %s AND b.status = 1
        ORDER BY b.update_datetime DESC
    """, (user_id,))
    blogs = cur.fetchall()

    cur.close()
    conn.close()
    return render(request, "stories.html", {"drafts": drafts, "blogs": blogs})

def search(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return redirect('/home')

    words = query.lower().split()

    conn = get_connection()
    cur = conn.cursor()

    # MAIN SEARCH QUERY
    cur.execute("""
        SELECT DISTINCT 
            b.blog_id,          -- 0: ID
            b.title,            -- 1: Title
            b.content,          -- 2: Content (for the excerpt)
            u.first_name,       -- 3: Author First Name
            u.last_name,        -- 4: Author Last Name
            b.update_datetime,  -- 5: Date
            b.author_id,        -- 6: Author ID (for the link)
            (SELECT COUNT(*) FROM likes WHERE blog_id = b.blog_id),    -- 7: Likes Count
            (SELECT COUNT(*) FROM comments WHERE blog_id = b.blog_id), -- 8: Comments Count
            b.is_premium,       -- 9: Premium Status
            p.publi_name,        -- 10: Publication Name
            u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN blog_categories bc ON b.blog_id = bc.blog_id
        LEFT JOIN categories c ON bc.category_id = c.category_id
        LEFT JOIN blog_keywords bk ON b.blog_id = bk.blog_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE
            LOWER(b.title) LIKE ANY(%s)
            OR LOWER(u.first_name) LIKE ANY(%s)
            OR LOWER(u.last_name) LIKE ANY(%s)
            OR LOWER(c.category_name) LIKE ANY(%s)
            OR LOWER(bk.keyword) LIKE ANY(%s)
            OR LOWER(p.publi_name) LIKE ANY(%s)
    """, (
        [f"%{w}%" for w in words],
        [f"%{w}%" for w in words],
        [f"%{w}%" for w in words],
        [f"%{w}%" for w in words],
        [f"%{w}%" for w in words],
        [f"%{w}%" for w in words],
    ))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "search.html", {
        "results": results,
        "query": query
    })

def create_publication(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    # 1. CHECK IF AUTHOR
    cur.execute("""
        SELECT * FROM authors WHERE author_id=%s
    """, (user_id,))
    is_author = cur.fetchone()

    if not is_author:
        cur.close()
        conn.close()
        return render(request, "not_author.html")

    # 2. CHECK IF ALREADY OWNS PUBLICATION
    cur.execute("""
        SELECT * FROM publications WHERE owner_id=%s
    """, (user_id,))
    already_owner = cur.fetchone()

    if already_owner:
        cur.close()
        conn.close()
        return render(request, "create_publication.html", {
            "error": "You already own a publication"
        })

    # 3. HANDLE CREATION
    if request.method == "POST":
        name = request.POST['name']

        try:
            cur.execute("""
                INSERT INTO publications (publi_name, date_of_joining, owner_id)
                VALUES (%s, CURRENT_DATE, %s)
                RETURNING publi_id
            """, (name, user_id))

            publi_id = cur.fetchone()[0]

            # LINK AUTHOR TO PUBLICATION
            cur.execute("""
                UPDATE authors
                SET publi_id=%s
                WHERE author_id=%s
            """, (publi_id, user_id))

            conn.commit()

        except Exception:
            conn.rollback()
            return render(request, "create_publication.html", {
                "error": "Something went wrong"
            })

        finally:
            cur.close()
            conn.close()

        return redirect('/publications/')

    cur.close()
    conn.close()
    return render(request, "create_publication.html")

def publications_list(request):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT publi_id, publi_name FROM publications
    """)
    publications = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "publications.html", {
        "publications": publications
    })

def publication_detail(request, publi_id):
    conn = get_connection()
    cur = conn.cursor()

    # 1. Fetch Publication Info
    cur.execute("SELECT publi_id, publi_name FROM publications WHERE publi_id = %s", (publi_id,))
    publication = cur.fetchone()

    # 2. Fetch Authors (Added u.user_id for the link)
    cur.execute("""
        SELECT u.first_name, u.last_name, u.user_id, u.avatar_id 
        FROM authors a
        JOIN users u ON a.author_id = u.user_id
        WHERE a.publi_id = %s
    """, (publi_id,))
    authors = cur.fetchall()

    # 3. Fetch Blogs (Same as before)
    cur.execute("""
        SELECT 
            b.blog_id, b.title, b.content, u.first_name, u.last_name, 
            b.update_datetime, b.author_id,
            (SELECT COUNT(*) FROM likes WHERE blog_id = b.blog_id),
            (SELECT COUNT(*) FROM comments WHERE blog_id = b.blog_id),
            b.is_premium, p.publi_name, p.publi_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        JOIN authors a ON b.author_id = a.author_id
        JOIN publications p ON a.publi_id = p.publi_id
        WHERE p.publi_id = %s AND b.status = 1
        ORDER BY b.update_datetime DESC
    """, (publi_id,))
    blogs = cur.fetchall()

    cur.close()
    conn.close()
    return render(request, "publication_detail.html", {
        "publication": publication,
        "authors": authors,
        "blogs": blogs,
        # ... include other variables like followers, is_following, etc.
    })

def join_request(request, publi_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    # must be author
    cur.execute("SELECT publi_id FROM authors WHERE author_id=%s", (user_id,))
    author = cur.fetchone()

    if not author:
        messages.error(request, "You must be an author")
        return redirect(f'/publication/{publi_id}/')

    if author[0]:
        messages.error(request, "Already in a publication")
        return redirect(f'/publication/{publi_id}/')

    # existing request
    cur.execute("""
        SELECT status FROM publication_join_requests
        WHERE user_id=%s
    """, (user_id,))
    req = cur.fetchone()

    if req:
        messages.error(request, f"Request already {req[0]}")
        return redirect(f'/publication/{publi_id}/')

    cur.execute("""
        INSERT INTO publication_join_requests (user_id, publi_id)
        VALUES (%s, %s)
    """, (user_id, publi_id))

    conn.commit()
    cur.close()
    conn.close()

    messages.success(request, "Request sent")

    return redirect(f'/publication/{publi_id}/')

def owner_dashboard(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    # get publication
    cur.execute("""
        SELECT publi_id, publi_name FROM publications
        WHERE owner_id=%s
    """, (user_id,))
    pub = cur.fetchone()

    if not pub:
        return redirect('/profile')

    publi_id = pub[0]

    # followers
    cur.execute("""
        SELECT COUNT(*) FROM publication_followers
        WHERE publi_id=%s
    """, (publi_id,))
    followers = cur.fetchone()[0]

    # authors
    cur.execute("""
        SELECT u.first_name, u.last_name, a.author_id
        FROM authors a
        JOIN users u ON a.author_id=u.user_id
        WHERE a.publi_id=%s
    """, (publi_id,))
    authors = cur.fetchall()

    # blogs
    cur.execute("""
        SELECT blog_id, title FROM blogs
        WHERE author_id IN (
            SELECT author_id FROM authors WHERE publi_id=%s
        ) AND status=1
    """, (publi_id,))
    blogs = cur.fetchall()

    # requests
    cur.execute("""
        SELECT r.request_id, u.first_name, u.last_name
        FROM publication_join_requests r
        JOIN users u ON r.user_id=u.user_id
        WHERE r.publi_id=%s AND r.status='pending'
    """, (publi_id,))
    requests = cur.fetchall()

    # owner_id
    cur.execute("""
        SELECT owner_id FROM publications WHERE publi_id = %s
    """, (publi_id,))
    owner_id = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render(request, "owner_dashboard.html", {
        "pub": pub,
        "followers": followers,
        "authors": authors,
        "blogs": blogs,
        "requests": requests,
        "owner_id":owner_id,
        "user_id":user_id
    })

def handle_request(request, request_id, action):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, publi_id FROM publication_join_requests
        WHERE request_id=%s
    """, (request_id,))
    user_id, publi_id = cur.fetchone()

    if action == "accept":
        cur.execute("""
            UPDATE publication_join_requests
            SET status='accepted'
            WHERE request_id=%s
        """, (request_id,))

        cur.execute("""
            UPDATE authors
            SET publi_id=%s
            WHERE author_id=%s
        """, (publi_id, user_id))

    elif action == "reject":
        cur.execute("""
            UPDATE publication_join_requests
            SET status='rejected'
            WHERE request_id=%s
        """, (request_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/owner-dashboard/')

def author_blogs(request, author_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            b.blog_id,          -- 0
            b.title,            -- 1
            b.content,          -- 2
            b.update_datetime,  -- 3
            u.first_name,       -- 4
            u.last_name,        -- 5

            -- likes count
            (SELECT COUNT(*) FROM likes l WHERE l.blog_id = b.blog_id) AS likes_count,       -- 6

            -- comments count
            (SELECT COUNT(*) FROM comments c WHERE c.blog_id = b.blog_id) AS comments_count, -- 7

            p.publi_name,       -- 8 (Fetched for the HTML template)
            b.is_premium,        -- 9 (Fetched for the premium badge)
            u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE b.author_id = %s AND b.status = 1
        ORDER BY b.update_datetime DESC
    """, (author_id,))

    blogs = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "author_blogs.html", {
        "blogs": blogs
    })

def edit_draft(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT category_id, category_name FROM categories")
    categories = cur.fetchall()

    # get draft
    cur.execute("""
        SELECT title, content, is_premium
        FROM blogs
        WHERE blog_id=%s AND author_id=%s AND status=0
    """, (blog_id, user_id))

    draft = cur.fetchone()

    # get already selected categories for this draft
    cur.execute("""
        SELECT category_id FROM blog_categories WHERE blog_id=%s
    """, (blog_id,))
    selected = [row[0] for row in cur.fetchall()]

    if not draft:
        cur.close()
        conn.close()
        return redirect('/stories')

    if request.method == "POST":
        title = request.POST['title']
        content = request.POST['content']
        action = request.POST['action']
        selected_categories = request.POST.getlist('categories')
        is_premium = request.POST.get('is_premium') == 'on'

        if action == "save":
            cur.execute("""
                UPDATE blogs
                SET title=%s, content=%s, is_premium=%s, update_datetime=NOW()
                WHERE blog_id=%s
            """, (title, content, is_premium, blog_id))

            # update categories
            cur.execute("DELETE FROM blog_categories WHERE blog_id=%s", (blog_id,))

            for cat in selected_categories:
                cur.execute("""
                    INSERT INTO blog_categories (blog_id, category_id)
                    VALUES (%s, %s)
                """, (blog_id, cat))

        elif action == "publish":
            # update blog
            cur.execute("""
                UPDATE blogs
                SET title=%s, content=%s, status=1, is_premium=%s, update_datetime=NOW()
                WHERE blog_id=%s
            """, (title, content, is_premium, blog_id))

            # remove old categories
            cur.execute("""
                DELETE FROM blog_categories WHERE blog_id=%s
            """, (blog_id,))

            # insert new categories
            for cat in selected_categories:
                cur.execute("""
                    INSERT INTO blog_categories (blog_id, category_id)
                    VALUES (%s, %s)
                """, (blog_id, cat))

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/stories')

    cur.close()
    conn.close()

    return render(request, "edit_draft.html", {
        "draft": draft,
        "blog_id": blog_id,
        "categories": categories,
        "selected_categories": selected
    })

def delete_draft(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM blogs
        WHERE blog_id=%s AND author_id=%s AND status=0
    """, (blog_id, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/stories')

def donate(request, blog_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    if request.method == "POST":
        amount = request.POST['amount']

        conn = get_connection()
        cur = conn.cursor()

        # get author of blog
        cur.execute("""
            SELECT author_id FROM blogs WHERE blog_id=%s
        """, (blog_id,))
        author_id = cur.fetchone()[0]

        # insert donation
        cur.execute("""
            INSERT INTO donations (user_id, author_id, blog_id, amount)
            VALUES (%s, %s, %s, %s)
        """, (user_id, author_id, blog_id, amount))

        # prevent self-donation
        if user_id == author_id:
            messages.error(request, "You cannot donate to yourself")
            return redirect(f'/blog/{blog_id}/')

        conn.commit()
        cur.close()
        conn.close()

        messages.success(request, "Thank you for supporting the author ❤️")

    return redirect(f'/blog/{blog_id}/')

def author_donations(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT d.amount, u.first_name, b.title, d.donated_at, b.blog_id
        FROM donations d
        JOIN users u ON d.user_id = u.user_id
        JOIN blogs b ON d.blog_id = b.blog_id
        WHERE d.author_id=%s
        ORDER BY d.donated_at DESC
    """, (user_id,))

    donations = cur.fetchall()

    cur.close()
    conn.close()

    return render(request, "donations.html", {
        "donations": donations
    })

def subscribe(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    if request.method == "POST":
        plan = request.POST['plan']

        if plan == "monthly":
            amount = 199
            days = 30
        else:
            amount = 1999
            days = 365

        start = datetime.now()
        end = start + timedelta(days=days)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, plan, start, end, amount))

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/profile')

    return render(request, "subscribe.html")

def subscriptions(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    # 🔍 Check if user has active subscription
    cur.execute("""
        SELECT plan_type, start_date, end_date, amount
        FROM subscriptions
        WHERE user_id=%s
        ORDER BY end_date DESC
        LIMIT 1
    """, (user_id,))

    sub = cur.fetchone()

    #  CASE 1: Has subscription
    if sub:
        cur.close()
        conn.close()

        return render(request, "subscriptions.html", {
            "sub": sub
        })

    #  CASE 2: No subscription → show plans
    if request.method == "POST":
        plan = request.POST['plan']

        if plan == "monthly":
            amount = 199
            days = 30
        else:
            amount = 1999
            days = 365

        start = datetime.now()
        end = start + timedelta(days=days)

        cur.execute("""
            INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, plan, start, end, amount))

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/subscriptions/')

    cur.close()
    conn.close()

    return render(request, "subscriptions.html", {
        "sub": sub,
        "today":date.today()
    })

def delete_blog(request, blog_id):
    if request.method != "POST":
        return redirect('/home')
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    conn = get_connection()
    cur = conn.cursor()

    #  Check ownership
    cur.execute("""
        SELECT author_id FROM blogs WHERE blog_id=%s
    """, (blog_id,))
    blog = cur.fetchone()

    if not blog:
        cur.close()
        conn.close()
        return redirect('/home')

    if blog[0] != user_id:
        #  Not author → no permission
        cur.close()
        conn.close()
        return redirect('/home')

    #  Delete dependent data FIRST (important)
    cur.execute("DELETE FROM comments WHERE blog_id=%s", (blog_id,))
    cur.execute("DELETE FROM likes WHERE blog_id=%s", (blog_id,))
    cur.execute("DELETE FROM booklist WHERE blog_id=%s", (blog_id,))
    cur.execute("DELETE FROM blog_categories WHERE blog_id=%s", (blog_id,))
    cur.execute("DELETE FROM blog_keywords WHERE blog_id=%s", (blog_id,))
    cur.execute("DELETE FROM donations WHERE blog_id=%s", (blog_id,))

    #  Finally delete blog
    cur.execute("DELETE FROM blogs WHERE blog_id=%s", (blog_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/stories/')   # or '/home'

def transfer_ownership(request, publi_id):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    # 🔒 Check current owner
    cur.execute("""
        SELECT owner_id FROM publications WHERE publi_id = %s
    """, (publi_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        messages.error(request, "Publication not found")
        return redirect('/profile')

    owner_id = row[0]

    if owner_id != user_id:
        cur.close()
        conn.close()
        messages.error(request, "Only owner can transfer ownership")
        return redirect('/profile')

    # 🔁 Transfer logic
    if request.method == "POST":
        new_owner_id = request.POST.get("new_owner")

        # ✅ Check if selected user is author of this publication
        cur.execute("""
            SELECT * FROM authors
            WHERE author_id = %s AND publi_id = %s
        """, (new_owner_id, publi_id))

        valid = cur.fetchone()

        if not valid:
            messages.error(request, "Selected user is not an author")
        else:
            cur.execute("""
                UPDATE publications
                SET owner_id = %s
                WHERE publi_id = %s
            """, (new_owner_id, publi_id))

            conn.commit()
            messages.success(request, "Ownership transferred successfully")

    cur.close()
    conn.close()

    return redirect('/owner-dashboard/')