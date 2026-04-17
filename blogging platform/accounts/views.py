from django.shortcuts import render, redirect
from blog_platform.db import get_connection
from django.views.decorators.cache import cache_control
from django.contrib.auth.hashers import make_password, check_password

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
        confirm_password = request.POST.get('confirm_password')
        sec_question = request.POST.get('security_question')
        sec_answer = request.POST.get('security_answer')
        selected_categories = request.POST.getlist('categories')

        # ── NEW: Check if passwords match ──
        if password != confirm_password:
            cur.close()
            conn.close()
            return render(request, "register.html", {
                "categories": categories, 
                "error": "Passwords do not match. Please try again."
            })
        
        # ── NEW: Hash the password and the security answer ──
        # We lowercase the answer before hashing so it's case-insensitive for the user later
        hashed_password = make_password(password)
        hashed_answer = make_password(sec_answer.strip().lower())
        
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
                INSERT INTO users (first_name, last_name, email_id, password, avatar_id, security_question, security_answer)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (fname, lname, email, hashed_password, avatar_val, sec_question, hashed_answer))

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

        # ❌ Email not registered
        if not user:
            return render(request, "login.html", {
                "flash": "You need to create an account first."
            })

        # ❌ Wrong password
        if not check_password(password, user[1]):
            cur.close(); conn.close()
            return render(request, "login.html", {
                "error": "Invalid password"
            })

        # ── NEW: Check if the user is also an Admin ──
        cur.execute("SELECT admin_id FROM admins WHERE admin_id = %s", (user[0],))
        admin_data = cur.fetchone()

        # ✅ Success
        request.session['user_id'] = user[0]
        request.session['is_admin'] = bool(admin_data)
        
        cur.close()
        conn.close()

        if request.session['is_admin']:
            return redirect('/admin-dashboard/')

        next_url = request.GET.get('next', '/home')
        return redirect(next_url)

    return render(request, "login.html")

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    from blog_platform.db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    # 1. Get basic user info
    cur.execute("""
        SELECT first_name, last_name, email_id, avatar_id
        FROM users WHERE user_id=%s
    """, (user_id,))
    user = cur.fetchone()

    # 2. Get Authors the user follows (MODIFIED to include u.avatar_id)
    cur.execute("""
        SELECT u.first_name, u.last_name, af.author_id, u.avatar_id
        FROM author_followers af
        JOIN users u ON af.author_id = u.user_id
        WHERE af.user_id=%s
    """, (user_id,))
    following = cur.fetchall()

    # 3. Get Publications the user follows
    cur.execute("""
        SELECT p.publi_id, p.publi_name
        FROM publication_followers pf
        JOIN publications p ON pf.publi_id = p.publi_id
        WHERE pf.user_id=%s
    """, (user_id,))
    publi_following = cur.fetchall()

    # 4. Categories logic
    cur.execute("SELECT category_id, category_name FROM categories")
    all_categories = cur.fetchall()

    cur.execute("""
        SELECT category_id FROM interested_categories
        WHERE user_id=%s
    """, (user_id,))
    selected = [x[0] for x in cur.fetchall()]

    # 5. Status Checks (Author/Owner)
    cur.execute("SELECT 1 FROM authors WHERE author_id=%s", (user_id,))
    is_author = cur.fetchone() is not None

    cur.execute("SELECT 1 FROM publications WHERE owner_id=%s", (user_id,))
    is_owner = cur.fetchone() is not None

    # 6. Fetch Publications details
    own_publication = None
    if is_owner:
        cur.execute("""
            SELECT p.publi_id, p.publi_name
            FROM publications p
            WHERE p.owner_id = %s
        """, (user_id,))
        own_publication = cur.fetchone()

    cur.execute("""
        SELECT p.publi_id, p.publi_name
        FROM authors a
        JOIN publications p ON a.publi_id = p.publi_id
        WHERE a.author_id = %s
    """, (user_id,))
    publication = cur.fetchone()
    
    is_member = publication is not None

    # 7. Follower Count (only if author)
    followers_count = 0
    if is_author:
        cur.execute("SELECT COUNT(*) FROM author_followers WHERE author_id = %s", (user_id,))
        followers_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render(request, "profile.html", {
        "user": user,
        "following": following,
        "categories": all_categories,
        "selected": selected,
        "is_author": is_author,
        "is_owner": is_owner,
        "publication": publication,
        "own_publication": own_publication,
        "publi_following": publi_following,
        "is_member": is_member,
        "is_admin": request.session.get('is_admin', False),
        "followers_count": followers_count 
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
    
def edit_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT first_name, last_name, avatar_id, security_question FROM users WHERE user_id=%s", (user_id,))
    user = cur.fetchone()

    # categories
    cur.execute("SELECT category_id, category_name FROM categories")
    categories = cur.fetchall()

    cur.execute("SELECT category_id FROM interested_categories WHERE user_id=%s", (user_id,))
    selected = [row[0] for row in cur.fetchall()]

    if request.method == "POST":
        first = request.POST['first_name']
        last = request.POST['last_name']
        password = request.POST.get('password')
        avatar = request.POST.get('avatar_id')

        # 1. Safely handle empty avatar to prevent DataError
        avatar_val = int(avatar) if avatar and avatar.strip() != "" else None

        # update basic info
        if password:
            sec_answer = request.POST.get('security_answer', '').strip().lower()
            
            # Fetch the hashed answer to verify
            cur.execute("SELECT security_answer FROM users WHERE user_id = %s", (user_id,))
            db_answer_hash = cur.fetchone()[0]

            if check_password(sec_answer, db_answer_hash):
                hashed_pw = make_password(password)
                cur.execute("""
                    UPDATE users 
                    SET first_name=%s, last_name=%s, password=%s, avatar_id=%s
                    WHERE user_id=%s
                """, (first, last, hashed_pw, avatar_val, user_id))
            else:
                return render(request, "edit_profile.html", {"user": user, "categories": categories, "selected": selected, "error": "Incorrect security answer. Password not changed."})
        else:
            cur.execute("""
                UPDATE users 
                SET first_name=%s, last_name=%s, avatar_id=%s
                WHERE user_id=%s
            """, (first, last, avatar_val, user_id))

        # update categories
        cur.execute("DELETE FROM interested_categories WHERE user_id=%s", (user_id,))
        selected_cats = request.POST.getlist('categories')

        for c in selected_cats:
            cur.execute("""
                INSERT INTO interested_categories (user_id, category_id)
                VALUES (%s, %s)
            """, (user_id, c))

        conn.commit()
        
        # Update session so navbar changes automatically!
        request.session['first_name'] = first
        request.session['last_name'] = last
        request.session['avatar_id'] = avatar_val

        cur.close()
        conn.close()
        return redirect('/profile/')

    cur.close()
    conn.close()

    return render(request, "edit_profile.html", {
        "user": user,
        "categories": categories,
        "selected": selected
    })

def forgot_password(request):
    if request.method == "POST":
        step = request.POST.get('step')
        email = request.POST.get('email')

        from blog_platform.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                
                # STEP 1: User submitted email, fetch their security question
                if step == "1":
                    cur.execute("SELECT security_question FROM users WHERE email_id = %s", (email,))
                    user = cur.fetchone()
                    if user:
                        return render(request, "forgot_password.html", {"step": 2, "email": email, "question": user[0]})
                    else:
                        return render(request, "forgot_password.html", {"error": "No account found with that email."})
                
                # STEP 2: User submitted security answer and new password
                elif step == "2":
                    answer = request.POST.get('security_answer').strip().lower()
                    new_password = request.POST.get('new_password')
                    
                    cur.execute("SELECT security_answer FROM users WHERE email_id = %s", (email,))
                    db_answer_hash = cur.fetchone()[0]

                    if check_password(answer, db_answer_hash):
                        hashed_pw = make_password(new_password)
                        cur.execute("UPDATE users SET password = %s WHERE email_id = %s", (hashed_pw, email))
                        conn.commit()
                        from django.contrib import messages
                        messages.success(request, "Password reset successfully! Please log in.")
                        return redirect('/login/')
                    else:
                        cur.execute("SELECT security_question FROM users WHERE email_id = %s", (email,))
                        question = cur.fetchone()[0]
                        return render(request, "forgot_password.html", {"step": 2, "email": email, "question": question, "error": "Incorrect security answer."})

    return render(request, "forgot_password.html", {"step": 1})