from django.shortcuts import render, redirect
from blog_platform.db import get_connection
from datetime import datetime
import re
from django.contrib import messages
from datetime import datetime, timedelta, date
from django.views.decorators.cache import cache_control
from blog_platform.db import DBConnection

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
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # We use DBConnection if you added the context manager, 
    # otherwise get_connection() works fine too.
    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # THE RECOMMENDATION ALGORITHM:
    # 1. Joins the blog's categories (bc) with the user's interests (ic)
    # 2. Counts the matches (match_score)
    # 3. Orders by highest match score first, then by newest date
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
            p.publi_id,         -- 11
            u.avatar_id,        -- 12
            COUNT(DISTINCT ic.category_id) AS match_score   -- 13 (NEW: For recommendations)
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN likes l ON b.blog_id = l.blog_id
        LEFT JOIN comments c ON b.blog_id = c.blog_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        
        -- NEW: Connect blogs to their categories, and check if the user likes them
        LEFT JOIN blog_categories bc ON b.blog_id = bc.blog_id
        LEFT JOIN interested_categories ic ON bc.category_id = ic.category_id AND ic.user_id = %s
        
        WHERE b.status = 1
        GROUP BY 
            b.blog_id, b.title, b.content,
            u.first_name, u.last_name,
            b.update_datetime, b.author_id,
            b.is_premium, p.publi_name, p.publi_id, u.avatar_id
        ORDER BY 
            match_score DESC,          -- Show user's favorite topics FIRST
            b.update_datetime DESC     -- Then sort by newest
    """, (user_id,)) # Pass the logged-in user's ID here

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
    is_author= (user_id==blog[3])
    is_user_premium=is_user_premium or is_author

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
        return redirect('/login')

    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # Query structure matching the Home page cards EXACTLY
    query_template = """
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
            p.publi_id,         -- 11
            u.avatar_id         -- 12
        FROM {table} t
        JOIN blogs b ON t.blog_id = b.blog_id
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        WHERE t.user_id = %s AND b.status = 1
        ORDER BY b.update_datetime DESC
    """

    # Fetch Bookmarks
    cur.execute(query_template.format(table="booklist"), (user_id,))
    bookmarks = cur.fetchall()

    # Fetch Likes
    cur.execute(query_template.format(table="likes"), (user_id,))
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

    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # Enable pg_trgm (safe to run even if already enabled)
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # THE FIX: Using word_similarity() to prevent Length Dilution
    cur.execute("""
        WITH BlogData AS (
            SELECT 
                b.blog_id, 
                b.title, 
                b.content,
                u.first_name, 
                u.last_name,
                b.update_datetime,
                b.author_id,
                b.is_premium,
                p.publi_name,
                u.avatar_id,
                
                -- Combine all text into one block
                CONCAT_WS(' ', 
                    b.title, 
                    u.first_name, 
                    u.last_name, 
                    p.publi_name,
                    string_agg(DISTINCT c.category_name, ' '),
                    string_agg(DISTINCT bk.keyword, ' ')
                ) AS searchable_text
                
            FROM blogs b
            JOIN users u ON b.author_id = u.user_id
            LEFT JOIN blog_categories bc ON b.blog_id = bc.blog_id
            LEFT JOIN categories c ON bc.category_id = c.category_id
            LEFT JOIN blog_keywords bk ON b.blog_id = bk.blog_id
            LEFT JOIN authors a ON b.author_id = a.author_id
            LEFT JOIN publications p ON a.publi_id = p.publi_id
            
            WHERE b.status = 1 
            
            GROUP BY 
                b.blog_id, b.title, b.content, u.first_name, u.last_name, 
                b.update_datetime, b.author_id, b.is_premium, p.publi_name, u.avatar_id
        )
        SELECT 
            blog_id,            -- 0: ID
            title,              -- 1: Title
            content,            -- 2: Content 
            first_name,         -- 3: First Name
            last_name,          -- 4: Last Name
            update_datetime,    -- 5: Date
            author_id,          -- 6: Author ID 
            (SELECT COUNT(*) FROM likes WHERE blog_id = BlogData.blog_id),    -- 7: Likes
            (SELECT COUNT(*) FROM comments WHERE blog_id = BlogData.blog_id), -- 8: Comments
            is_premium,         -- 9: Premium
            publi_name,         -- 10: Publication
            avatar_id,          -- 11: Avatar
            word_similarity(%s, searchable_text) AS score -- 12: The smart score
        FROM BlogData
        WHERE 
            searchable_text ILIKE %s 
            -- Using word_similarity instead of similarity!
            OR word_similarity(%s, searchable_text) > 0.15 
        ORDER BY 
            score DESC, update_datetime DESC
    """, (query, f"%{query}%", query))

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
    user_id = request.session.get('user_id')
    conn = get_connection()
    cur = conn.cursor()

    # 1. Fetch Publication Info
    cur.execute("SELECT publi_id, publi_name,owner_id FROM publications WHERE publi_id = %s", (publi_id,))
    publication = cur.fetchone()

    owner_id = publication[2] if publication else None

    # Check if current user is a member of THIS publication
    cur.execute("SELECT 1 FROM authors WHERE author_id = %s AND publi_id = %s", (user_id, publi_id))
    is_member = cur.fetchone() is not None

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
            b.is_premium, p.publi_name, p.publi_id, u.avatar_id
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        JOIN authors a ON b.author_id = a.author_id
        JOIN publications p ON a.publi_id = p.publi_id
        WHERE p.publi_id = %s AND b.status = 1
        ORDER BY b.update_datetime DESC
    """, (publi_id,))
    blogs = cur.fetchall()

    is_following = False
    if user_id:
        cur.execute("SELECT 1 FROM publication_followers WHERE user_id = %s AND publi_id = %s", (user_id, publi_id))
        is_following = cur.fetchone() is not None

    cur.execute("SELECT COUNT(*) FROM publication_followers WHERE publi_id = %s", (publi_id,))
    followers_count = cur.fetchone()[0]

    cur.close()
    conn.close()
    return render(request, "publication_detail.html", {
        "publication": publication,
        "authors": authors,
        "blogs": blogs,
        "user_id":user_id,
        "is_member":is_member,
        "owner_id":owner_id,
        "is_following":is_following,
        "followers": followers_count
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

    if author and author[0] is not None:
        messages.error(request, "You must be an author")
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
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute ("""
        SELECT u.first_name FROM authors a
        JOIN users u ON u.user_id=a.author_id 
        WHERE a.author_id=%s
    """,(author_id,))
    author_name=cur.fetchone()[0]

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
            p.publi_id,         -- 11
            u.avatar_id,        -- 12
            COUNT(DISTINCT ic.category_id) AS match_score   -- 13 (NEW: For recommendations)
        FROM blogs b
        JOIN users u ON b.author_id = u.user_id
        LEFT JOIN likes l ON b.blog_id = l.blog_id
        LEFT JOIN comments c ON b.blog_id = c.blog_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN publications p ON a.publi_id = p.publi_id
        
        -- NEW: Connect blogs to their categories, and check if the user likes them
        LEFT JOIN blog_categories bc ON b.blog_id = bc.blog_id
        LEFT JOIN interested_categories ic ON bc.category_id = ic.category_id AND ic.user_id = %s
        
        WHERE b.status = 1 and b.author_id = %s
        GROUP BY 
            b.blog_id, b.title, b.content,
            u.first_name, u.last_name,
            b.update_datetime, b.author_id,
            b.is_premium, p.publi_name, p.publi_id, u.avatar_id
        ORDER BY 
            match_score DESC,          -- Show user's favorite topics FIRST
            b.update_datetime DESC     -- Then sort by newest
    """, (user_id,author_id)) # Pass the logged-in user's ID here

    blogs = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM author_followers WHERE author_id = %s", (author_id,))
    followers = cur.fetchone()[0]

    is_following = False
    if user_id:
        # NOTE: Change 'author_followers' if your table has a different name!
        cur.execute("SELECT 1 FROM author_followers WHERE user_id = %s AND author_id = %s", (user_id, author_id))
        is_following = cur.fetchone() is not None

    cur.execute("""
        SELECT u.first_name, u.last_name, u.user_id, u.avatar_id
        FROM authors a
        JOIN users u ON a.author_id = u.user_id
        WHERE a.author_id = %s
    """, (author_id,))
    author = cur.fetchone()
    
    cur.close()
    conn.close()

    return render(request, "author_blogs.html", {
        "blogs": blogs,
        "author_name":author_name,
        "followers":followers,
        "user_id": user_id, 
        "is_following": is_following,
        "author":author
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

def leave_publication(request, publi_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    # 1. Check if the user is the owner
    cur.execute("SELECT owner_id FROM publications WHERE publi_id = %s", (publi_id,))
    pub = cur.fetchone()
    if pub and pub[0] == user_id:
        cur.close()
        conn.close()
        messages.error(request, "Owners cannot leave the publication.")
        return redirect(f'/publication/{publi_id}/')

    # 2. Leave the publication (Set to NULL)
    cur.execute("""
        UPDATE authors 
        SET publi_id = NULL 
        WHERE author_id = %s
    """, (user_id,))

    # 3. THE FIX: Delete the old join request so they can apply again!
    cur.execute("""
        DELETE FROM publication_join_requests 
        WHERE user_id = %s and status="accepted"
    """, (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    messages.success(request, "You have left the publication and can now join another.")
    return redirect('/publications/')

def delete_publication(request, publi_id):
    if request.method != "POST":
        return redirect('/profile/')

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # 1. Verify that the current user is the OWNER
    cur.execute("SELECT owner_id FROM publications WHERE publi_id = %s", (publi_id,))
    pub = cur.fetchone()

    if not pub or pub[0] != user_id:
        cur.close()
        conn.close()
        from django.contrib import messages
        messages.error(request, "You do not have permission to delete this publication.")
        return redirect('/profile/')

    try:
        # 2. Unlink all authors (Set their publi_id to NULL so they remain authors but leave the publication)
        cur.execute("UPDATE authors SET publi_id = NULL WHERE publi_id = %s", (publi_id,))

        # 3. Delete ALL join requests for this publication (Pending, Accepted, or Rejected)
        cur.execute("DELETE FROM publication_join_requests WHERE publi_id = %s", (publi_id,))

        # 4. Delete followers of this publication
        cur.execute("DELETE FROM publication_followers WHERE publi_id = %s", (publi_id,))

        # 5. Delete the actual publication
        cur.execute("DELETE FROM publications WHERE publi_id = %s", (publi_id,))

        conn.commit()
        from django.contrib import messages
        messages.success(request, "Publication has been permanently deleted.")
        
    except Exception as e:
        conn.rollback()
        from django.contrib import messages
        messages.error(request, "An error occurred while deleting the publication.")
        print(f"Delete Error: {e}")
        
    finally:
        cur.close()
        conn.close()

    # Redirect to profile since the owner dashboard for this publication no longer exists
    return redirect('/profile/')


def delete_account(request):
    if request.method != "POST":
        return redirect('/edit-profile/')

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1. CHECK IF USER IS A PUBLICATION OWNER
        cur.execute("SELECT publi_id, publi_name FROM publications WHERE owner_id = %s", (user_id,))
        pub = cur.fetchone()

        if pub:
            publi_id = pub[0]
            # Check how many authors are in this publication
            cur.execute("SELECT COUNT(*) FROM authors WHERE publi_id = %s", (publi_id,))
            author_count = cur.fetchone()[0]

            if author_count > 1:
                cur.close()
                conn.close()
                from django.contrib import messages
                messages.error(request, f"You must transfer ownership of '{pub[1]}' to another author before deleting your account.")
                return redirect('/owner-dashboard/')
            else:
                # Delete publication & dependencies since they are the ONLY author
                cur.execute("DELETE FROM publication_join_requests WHERE publi_id = %s", (publi_id,))
                cur.execute("DELETE FROM publication_followers WHERE publi_id = %s", (publi_id,))
                cur.execute("UPDATE authors SET publi_id = NULL WHERE publi_id = %s", (publi_id,))
                cur.execute("DELETE FROM publications WHERE publi_id = %s", (publi_id,))

        # 2. DELETE USER'S GENERAL INTERACTIONS
        cur.execute("DELETE FROM interested_categories WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM comments WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM likes WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM booklist WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM publication_followers WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM publication_join_requests WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM author_followers WHERE user_id = %s OR author_id = %s", (user_id, user_id))
        cur.execute("DELETE FROM donations WHERE user_id = %s OR author_id = %s", (user_id, user_id))

        # 3. DELETE USER'S BLOGS AND THEIR DEPENDENCIES (If they are an author)
        cur.execute("SELECT blog_id FROM blogs WHERE author_id = %s", (user_id,))
        blogs = cur.fetchall()
        for b in blogs:
            b_id = b[0]
            cur.execute("DELETE FROM comments WHERE blog_id = %s", (b_id,))
            cur.execute("DELETE FROM likes WHERE blog_id = %s", (b_id,))
            cur.execute("DELETE FROM booklist WHERE blog_id = %s", (b_id,))
            cur.execute("DELETE FROM blog_categories WHERE blog_id = %s", (b_id,))
            cur.execute("DELETE FROM blog_keywords WHERE blog_id = %s", (b_id,))
            cur.execute("DELETE FROM donations WHERE blog_id = %s", (b_id,))
        
        # Delete blogs & author profile
        cur.execute("DELETE FROM blogs WHERE author_id = %s", (user_id,))
        cur.execute("DELETE FROM authors WHERE author_id = %s", (user_id,))

        # 4. FINALLY, DELETE THE USER RECORD
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        conn.commit()
        request.session.flush()

    except Exception as e:
        conn.rollback()
        print("Delete Account Error:", e)
        from django.contrib import messages
        messages.error(request, "An error occurred while deleting your account.")
        return redirect('/edit-profile/')
    finally:
        cur.close()
        conn.close()

    from django.contrib import messages
    messages.success(request, "Your account has been permanently deleted.")
    return redirect('/register/')

# ── 1. SUBMIT REPORT ──
def report_blog(request, blog_id):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login')

        report_type = request.POST.get('report_type')
        description = request.POST.get('description', '').strip()

        from blog_platform.db import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reports (user_id, blog_id, type_of_report, description, status)
                VALUES (%s, %s, %s, %s, 'new')
            """, (user_id, blog_id, report_type, description))
            conn.commit()

        from django.contrib import messages
        messages.success(request, "Thank you. The report has been sent to the admin for review.")
    return redirect(f'/blog/{blog_id}/')

# ── 2. ADMIN DASHBOARD ──
def admin_dashboard(request):
    if not request.session.get('is_admin'):
        return redirect('/home')

    from blog_platform.db import get_connection
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Fetch Active Reports
        cur.execute("""
            SELECT r.report_id, b.title, u.first_name, u.last_name, r.type_of_report, r.description, r.reported_at, b.blog_id
            FROM reports r
            JOIN blogs b ON r.blog_id = b.blog_id
            JOIN users u ON r.user_id = u.user_id
            WHERE r.status = 'new'
            ORDER BY r.reported_at DESC
        """)
        reports = cur.fetchall()

        # Fetch Data for Moderation Tables
        cur.execute("SELECT user_id, first_name, last_name, email_id FROM users ORDER BY user_id DESC LIMIT 50")
        users = cur.fetchall()

        cur.execute("SELECT blog_id, title FROM blogs ORDER BY update_datetime DESC LIMIT 50")
        blogs = cur.fetchall()

        cur.execute("SELECT publi_id, publi_name FROM publications ORDER BY publi_id DESC LIMIT 50")
        pubs = cur.fetchall()

        cur.execute("""
            SELECT c.comment_id, c.description, u.first_name, b.title 
            FROM comments c JOIN users u ON c.user_id=u.user_id JOIN blogs b ON c.blog_id=b.blog_id 
            ORDER BY c.creation_datetime DESC LIMIT 50
        """)
        comments = cur.fetchall()

    return render(request, "admin_dashboard.html", {
        "reports": reports, "users": users, "blogs": blogs, "pubs": pubs, "comments": comments
    })

# ── 3. ADMIN ACTIONS ──
def admin_action(request, action_type, item_id):
    if not request.session.get('is_admin'):
        return redirect('/home')

    from blog_platform.db import get_connection
    with get_connection() as conn:
        cur = conn.cursor()

        try:
            if action_type == 'resolve_report':
                cur.execute("UPDATE reports SET status = 'solved' WHERE report_id = %s", (item_id,))
            
            elif action_type == 'delete_blog':
                cur.execute("DELETE FROM comments WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM likes WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM booklist WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM blog_categories WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM blog_keywords WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM reports WHERE blog_id = %s", (item_id,))
                cur.execute("DELETE FROM blogs WHERE blog_id = %s", (item_id,))
            
            elif action_type == 'delete_user':
                # Reusing your massive delete cascade logic here
                cur.execute("DELETE FROM comments WHERE user_id = %s", (item_id,))
                cur.execute("DELETE FROM likes WHERE user_id = %s", (item_id,))
                cur.execute("DELETE FROM booklist WHERE user_id = %s", (item_id,))
                cur.execute("DELETE FROM users WHERE user_id = %s", (item_id,))
            
            elif action_type == 'delete_pub':
                cur.execute("DELETE FROM publication_join_requests WHERE publi_id = %s", (item_id,))
                cur.execute("DELETE FROM publication_followers WHERE publi_id = %s", (item_id,))
                cur.execute("UPDATE authors SET publi_id = NULL WHERE publi_id = %s", (item_id,))
                cur.execute("DELETE FROM publications WHERE publi_id = %s", (item_id,))

            elif action_type == 'delete_comment':
                cur.execute("DELETE FROM comments WHERE comment_id = %s", (item_id,))

            conn.commit()
            from django.contrib import messages
            messages.success(request, "Action completed successfully.")
        except Exception as e:
            conn.rollback()
            print("Admin Action Error:", e)

    return redirect('/admin-dashboard/')

def follow_author(request, author_id):
    # 1. Ensure the user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    from blog_platform.db import get_connection # Use your actual import path
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 2. Check if they are already following this author
        cur.execute("SELECT 1 FROM author_followers WHERE user_id = %s AND author_id = %s", (user_id, author_id))
        is_following = cur.fetchone()

        if is_following:
            # 3a. If they are following, UNFOLLOW (Delete)
            cur.execute("DELETE FROM author_followers WHERE user_id = %s AND author_id = %s", (user_id, author_id))
        else:
            # 3b. If they are not following, FOLLOW (Insert)
            cur.execute("INSERT INTO author_followers (user_id, author_id) VALUES (%s, %s)", (user_id, author_id))
        
        conn.commit()

    except Exception as e:
        print(f"Error toggling author follow: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    # 4. Redirect them right back to the author's page they were just looking at!
    return redirect(f'/author/{author_id}/')