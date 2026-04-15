from django.shortcuts import render, redirect
from blog_platform.db import get_connection
from django.views.decorators.cache import cache_control

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def register(request):
    conn = get_connection()
    cur = conn.cursor()

    # Always fetch categories to re-render the page if there's an error
    cur.execute("SELECT category_id, category_name FROM categories")
    categories = cur.fetchall()

    if request.method == "POST":
        fname = request.POST.get('first_name')
        lname = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        selected_categories = request.POST.getlist('categories')
        
        # 1. Capture the avatar choice
        avatar_id = request.POST.get('avatar_id')
        
        # 2. Logic: If string is empty, use None (SQL NULL). Otherwise, use the INT.
        if avatar_id and avatar_id.strip() != "":
            avatar_val = int(avatar_id)
        else:
            avatar_val = None

        try:
            # 3. Insert user with RETURNING clause
            cur.execute("""
                INSERT INTO users (first_name, last_name, email_id, password, avatar_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
            """, (fname, lname, email, password, avatar_val))

            # 4. FIX: Safely fetch the result to avoid 'NoneType' error
            result = cur.fetchone()
            if result:
                user_id = result[0]
            else:
                # This handles cases where the INSERT didn't return an ID
                raise Exception("Database failed to return a user_id.")

            # 5. Insert interested categories
            for cat_id in selected_categories:
                cur.execute("""
                    INSERT INTO interested_categories (user_id, category_id)
                    VALUES (%s, %s)
                """, (user_id, cat_id))

            conn.commit()

            # 6. Set Session (Crucial for sidebar/profile to work immediately)
            request.session['user_id'] = user_id
            request.session['first_name'] = fname
            request.session['last_name'] = lname
            request.session['avatar_id'] = avatar_val 

            return redirect('/home')

        except Exception as e:
            conn.rollback()
            # Print the error to your terminal so you can see why the INSERT failed
            print(f"DATABASE ERROR: {e}") 
            return render(request, "register.html", {
                "categories": categories, 
                "error": "Registration failed. Please try again."
            })
        finally:
            cur.close()
            conn.close()

    return render(request, "register.html", {"categories": categories})

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def login_view(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        conn = get_connection()
        cur = conn.cursor()

        # 🔹 Check if email exists
        cur.execute("""
            SELECT user_id, password FROM users
            WHERE email_id=%s
        """, (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        # ❌ Email not registered
        if not user:
            return render(request, "login.html", {
                "flash": "You need to create an account first."
            })

        # ❌ Wrong password
        if user[1] != password:
            return render(request, "login.html", {
                "error": "Invalid password"
            })

        # ✅ Success
        request.session['user_id'] = user[0]
        next_url = request.GET.get('next', '/home')
        return redirect(next_url)

    return render(request, "login.html")

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT first_name, last_name, email_id, avatar_id
        FROM users WHERE user_id=%s
    """, (user_id,))
    user = cur.fetchone()

    cur.execute("""
        SELECT u.first_name,u.last_name,af.author_id
        FROM author_followers af
        JOIN users u ON af.author_id = u.user_id
        WHERE af.user_id=%s
    """, (user_id,))
    following = cur.fetchall()

    cur.execute("""
        SELECT p.publi_id, p.publi_name
        FROM publication_followers pf
        JOIN publications p ON pf.publi_id = p.publi_id
        WHERE pf.user_id=%s
    """, (user_id,))
    publi_following = cur.fetchall()

    #  all categories
    cur.execute("SELECT category_id, category_name FROM categories")
    all_categories = cur.fetchall()

    #  user selected categories
    cur.execute("""
        SELECT category_id FROM interested_categories
        WHERE user_id=%s
    """, (user_id,))
    selected = [x[0] for x in cur.fetchall()]

    # check if author
    cur.execute("""
        SELECT * FROM authors WHERE author_id=%s
    """, (user_id,))
    is_author = cur.fetchone()

    # check if owner
    cur.execute("""
        SELECT * FROM publications WHERE owner_id=%s
    """, (user_id,))
    is_owner = cur.fetchone()

    if is_owner:
        # get user's own publication (if any)
        cur.execute("""
            SELECT p.publi_id, p.publi_name
            FROM publications p
            WHERE p.owner_id = %s
        """, (user_id,))
    own_publication = cur.fetchone()

    # get user's publication (if any)
    cur.execute("""
        SELECT p.publi_id, p.publi_name
        FROM authors a
        JOIN publications p ON a.publi_id = p.publi_id
        WHERE a.author_id = %s
    """, (user_id,))
    publication = cur.fetchone()

    cur.close()
    conn.close()

    return render(request, "profile.html", {
        "user": user,
        "following": following,
        "categories": all_categories,
        "selected": selected,
        "is_author": is_author,
        "is_owner":is_owner,
        "publication":publication,
        "own_publication":own_publication,
        "publi_following":publi_following
    })

def logout_view(request):
    request.session.flush()
    return redirect('/login')

def update_categories(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message

    selected = request.POST.getlist('categories')

    conn = get_connection()
    cur = conn.cursor()

    # delete old
    cur.execute("""
        DELETE FROM interested_categories WHERE user_id=%s
    """, (user_id,))

    # insert new
    for cat in selected:
        cur.execute("""
            INSERT INTO interested_categories (user_id, category_id)
            VALUES (%s, %s)
        """, (user_id, cat))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/profile')

def toggle_author(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login') # Or return an error message


    conn = get_connection()
    cur = conn.cursor()

    # check if already author
    cur.execute("""
        SELECT * FROM authors WHERE author_id = %s
    """, (user_id,))
    exists = cur.fetchone()

    if not exists:
        # create author with NULL publication
        cur.execute("""
            INSERT INTO authors (author_id, publi_id)
            VALUES (%s, NULL)
        """, (user_id,))
        message = "You are now an author!"
    else:
        message = "You are already an author"

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/profile')

def update_avatar(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        avatar_id = request.POST.get('avatar_id')
        
        # Convert empty string back to NULL for database
        val = int(avatar_id) if avatar_id else None
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar_id = %s WHERE user_id = %s", (val, user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        from django.contrib import messages
        messages.success(request, "Avatar updated successfully!")
        return redirect('/profile/')