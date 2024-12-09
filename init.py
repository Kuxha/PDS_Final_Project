from flask import Flask, render_template, request, session, redirect, url_for, flash
import pymysql.cursors
import os
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = 'FlaskDemoPhotos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure MySQL for WelcomeHome database
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='lazarus42',
                       db='WelcomeHome',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

###################################
# Basic Routes for Login/Index/Home
###################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    # Fetch available roles from Role table for the dropdown
    cursor = conn.cursor()
    cursor.execute("SELECT roleID, rDescription FROM Role")
    roles = cursor.fetchall()
    cursor.close()
    return render_template('register.html', roles=roles)

@app.route('/loginAuth', methods=['POST'])
def loginAuth():
    username = request.form['username']
    password = request.form['password']

    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE userName = %s'
    cursor.execute(query, (username,))
    user_data = cursor.fetchone()

    if user_data and check_password_hash(user_data['password'], password):
        session['username'] = user_data['userName']
        # Check roles:
        q = 'SELECT roleID FROM Act WHERE userName=%s'
        cursor.execute(q, (username,))
        roles = cursor.fetchall()
        session['is_staff'] = any(r['roleID'] == 'staff' for r in roles)
        session['is_volunteer'] = any(r['roleID'] == 'volunteer' for r in roles)
        
        cursor.close()
        return redirect(url_for('home'))
    else:
        cursor.close()
        error = 'Invalid login or password'
        return render_template('login.html', error=error)

@app.route('/registerAuth', methods=['POST'])
def registerAuth():
    username = request.form['username']
    password = request.form['password']
    fname = request.form['fname']
    lname = request.form['lname']
    email = request.form['email']
    chosen_role = request.form['role']  # The selected role from dropdown

    # Hash the password using Werkzeug
    password_hash = generate_password_hash(password)

    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE userName = %s'
    cursor.execute(query, (username,))
    data = cursor.fetchone()

    if data:
        cursor.close()
        error = "This user already exists"
        return render_template('register.html', error=error)
    else:
        ins = 'INSERT INTO Person (userName, password, fname, lname, email) VALUES (%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, password_hash, fname, lname, email))
        conn.commit()

        # Insert the role into Act table
        ins_role = 'INSERT INTO Act (userName, roleID) VALUES (%s, %s)'
        cursor.execute(ins_role, (username, chosen_role))
        conn.commit()

        cursor.close()
        return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', 
                           username=session['username'], 
                           is_staff=session.get('is_staff', False))

@app.route('/upload_form')
def upload_form():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('File successfully uploaded')
        return redirect(url_for('upload_form'))
    else:
        flash('Allowed file types are png, jpg, jpeg, gif')
        return redirect(request.url)

############################################################
# 5. Start an Order
############################################################
@app.route('/start_order', methods=['GET', 'POST'])
def start_order():
    if 'username' not in session or not session.get('is_staff'):
        return "Not authorized"
    if request.method == 'POST':
        client = request.form['clientName']
        # Verify client exists
        cursor = conn.cursor()
        query = "SELECT * FROM Person WHERE userName=%s"
        cursor.execute(query, (client,))
        person = cursor.fetchone()
        if not person:
            cursor.close()
            return "Invalid client username"
        # Create new order
        query = "INSERT INTO Ordered (orderDate, orderNotes, supervisor, client) VALUES (%s,%s,%s,%s)"
        cursor.execute(query, (date.today(), 'New Order', session['username'], client))
        orderID = cursor.lastrowid
        conn.commit()
        cursor.close()
        # Save orderID in session
        session['current_order'] = orderID
        return redirect(url_for('add_to_order'))
    return render_template('start_order.html')

############################################################
# 6. Add to Current Order
############################################################
@app.route('/add_to_order', methods=['GET', 'POST'])
def add_to_order():
    if 'username' not in session or not session.get('is_staff'):
        return "Not authorized"
    if 'current_order' not in session:
        return "No current order. Please start an order first."

    cursor = conn.cursor()
    
    # Fetch order details
    cursor.execute("SELECT * FROM Ordered WHERE orderID = %s", (session['current_order'],))
    order = cursor.fetchone()

    # Get list of categories/subcategories for the dropdown
    cursor.execute("SELECT DISTINCT mainCategory, subCategory FROM Category")
    categories = cursor.fetchall()

    selected_category = None
    selected_subcategory = None
    items = []

    if request.method == 'POST':
        if 'category_submit' in request.form:
            selected_category = request.form['mainCategory']
            selected_subcategory = request.form['subCategory']
            query = """
            SELECT i.ItemID, i.iDescription, p.pieceNum 
            FROM Item i
            JOIN Piece p ON i.ItemID = p.ItemID
            WHERE i.mainCategory = %s AND i.subCategory = %s
            AND NOT EXISTS (
                SELECT 1 FROM ItemIn ii WHERE ii.ItemID = p.ItemID AND ii.pieceNum = p.pieceNum
            )
            """
            cursor.execute(query, (selected_category, selected_subcategory))
            items = cursor.fetchall()
        elif 'add_item' in request.form:
            selected_item = request.form['selected_item']
            itemID, pieceNum = selected_item.split('_')
            orderID = session['current_order']
            query = "INSERT INTO ItemIn (ItemID, pieceNum, orderID) VALUES (%s, %s, %s)"
            cursor.execute(query, (itemID, pieceNum, orderID))
            conn.commit()
            flash("Item added to order")
    cursor.close()

    return render_template('add_to_order.html', 
                           categories=categories,
                           selected_category=selected_category,
                           selected_subcategory=selected_subcategory,
                           items=items,
                           order=order)


############################################################
# 7. Prepare Order
############################################################
@app.route('/prepare_order', methods=['GET', 'POST'])
def prepare_order():
    if 'username' not in session or not session.get('is_staff'):
        return "Not authorized"
    cursor = conn.cursor()

    if request.method == 'POST':
        order_identifier = request.form['order_identifier']
        if order_identifier.isdigit():
            orderID = int(order_identifier)
        else:
            q = "SELECT orderID FROM Ordered WHERE client=%s ORDER BY orderID DESC LIMIT 1"
            cursor.execute(q, (order_identifier,))
            o = cursor.fetchone()
            if not o:
                cursor.close()
                return "No order found for that client."
            orderID = o['orderID']

        q = """
        UPDATE Piece p
        JOIN ItemIn ii ON p.ItemID = ii.ItemID AND p.pieceNum = ii.pieceNum
        SET p.roomNum = 999, p.shelfNum = 999
        WHERE ii.orderID = %s
        """
        cursor.execute(q, (orderID,))
        conn.commit()
        cursor.close()
        return "Order prepared for delivery."
    cursor.close()
    return render_template('prepare_order.html')

############################################################
# 8. User's Tasks (My Orders)
############################################################
@app.route('/my_orders')
def my_orders():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = session['username']
    cursor = conn.cursor()

    query = """
    SELECT o.orderID, o.orderDate, o.orderNotes, o.supervisor, o.client, d.status, d.date AS deliveryDate
    FROM Ordered o
    LEFT JOIN Delivered d ON o.orderID=d.orderID
    WHERE o.client=%s OR o.supervisor=%s OR d.userName=%s
    """
    cursor.execute(query, (user, user, user))
    orders = cursor.fetchall()
    cursor.close()

    return render_template('my_orders.html', orders=orders)

############################################################
# 9. Rank System (Volunteers)
############################################################
@app.route('/rank_volunteers')
def rank_volunteers():
    if 'username' not in session or not session.get('is_staff'):
        return "Not authorized"
    cursor = conn.cursor()

    q = """
    SELECT d.userName, COUNT(*) as delivered_count
    FROM Delivered d
    WHERE d.date >= CURDATE() - INTERVAL 30 DAY
    GROUP BY d.userName
    ORDER BY delivered_count DESC
    """
    cursor.execute(q)
    ranks = cursor.fetchall()
    cursor.close()
    return render_template('rank_volunteers.html', ranks=ranks)

############################################################
# 10. Update Order Status
############################################################
@app.route('/update_order_status', methods=['GET','POST'])
def update_order_status():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = session['username']

    if request.method == 'POST':
        orderID = request.form['orderID']
        new_status = request.form['status']

        cursor = conn.cursor()
        q = "SELECT * FROM Ordered WHERE orderID=%s AND (supervisor=%s OR client=%s)"
        cursor.execute(q, (orderID, user, user))
        data_order = cursor.fetchone()

        q2 = "SELECT * FROM Delivered WHERE orderID=%s AND userName=%s"
        cursor.execute(q2, (orderID, user))
        data_del = cursor.fetchone()

        if data_order or data_del:
            q = "SELECT * FROM Delivered WHERE orderID=%s AND userName=%s"
            cursor.execute(q, (orderID, user))
            dcheck = cursor.fetchone()
            if not dcheck:
                qi = "INSERT INTO Delivered (userName, orderID, status, date) VALUES (%s,%s,%s,%s)"
                cursor.execute(qi, (user, orderID, new_status, date.today()))
            else:
                qu = "UPDATE Delivered SET status=%s, date=%s WHERE orderID=%s AND userName=%s"
                cursor.execute(qu, (new_status, date.today(), orderID, user))
            conn.commit()
            cursor.close()
            return "Order status updated."
        else:
            cursor.close()
            return "You are not authorized to update this order."
    return render_template('update_order_status.html')

############################################################
# 11. Year-End Report
############################################################
@app.route('/year_end_report')
def year_end_report():
    if 'username' not in session or not session.get('is_staff'):
        return "Not authorized"
    cursor = conn.cursor()

    q = "SELECT COUNT(DISTINCT client) as clients_served FROM Ordered"
    cursor.execute(q)
    clients_served = cursor.fetchone()['clients_served']

    q = """
    SELECT i.mainCategory, i.subCategory, COUNT(*) as count_items
    FROM DonatedBy db
    JOIN Item i ON db.ItemID = i.ItemID
    GROUP BY i.mainCategory, i.subCategory
    """
    cursor.execute(q)
    category_data = cursor.fetchall()

    q = "SELECT COUNT(*) as total_orders FROM Ordered"
    cursor.execute(q)
    total_orders = cursor.fetchone()['total_orders']

    cursor.close()
    return render_template('year_end_report.html', 
                           clients_served=clients_served, 
                           category_data=category_data, 
                           total_orders=total_orders)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_staff', None)
    return redirect('/')

@app.route('/find_single_item', methods=['GET', 'POST'])
def find_single_item():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        itemID = request.form['itemID']
        cursor = conn.cursor()

  
        query = '''
        SELECT p.pieceNum, l.shelfDescription AS address
        FROM Piece p
        JOIN Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum
        WHERE p.ItemID = %s
        '''
        cursor.execute(query, (itemID,))
        pieces = cursor.fetchall()
        cursor.close()
        
        # Render results or an appropriate message
        if pieces:
            return render_template('item_locations.html', pieces=pieces)
        else:
            return "No pieces found for the given item ID."
    
    # If GET request, show the form
    return render_template('find_item.html')


@app.route('/find_order_items', methods=['GET', 'POST'])
def find_order_items():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        orderID = request.form['orderID']
        cursor = conn.cursor()
        # Updated query to match the schema changes
        query = """
        SELECT i.ItemID, i.iDescription AS itemName, l.shelfDescription AS address, p.pieceNum
        FROM ItemIn ii
        JOIN Piece p ON ii.ItemID = p.ItemID AND ii.pieceNum = p.pieceNum
        JOIN Item i ON p.ItemID = i.ItemID
        JOIN Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum
        WHERE ii.orderID = %s
        """
        cursor.execute(query, (orderID,))
        items = cursor.fetchall()
        cursor.close()
        return render_template('order_items.html', items=items)
    else:
        return render_template('find_order.html')



# // Latest 
@app.route('/accept_donation', methods=['GET', 'POST'])


@app.route('/accept_donation', methods=['GET', 'POST'])
def accept_donation():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not session.get('is_staff', False):
        return "You are not authorized to accept donations."

    cursor = conn.cursor()
    # Fetch all categories and subcategories
    cat_query = "SELECT mainCategory, subCategory FROM Category"
    cursor.execute(cat_query)
    categories = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        donorID = request.form['donorID']
        itemName = request.form['itemName']
        selected_main_cat = request.form['mainCategory']
        selected_sub_cat = request.form['subCategory']
        selected_location = request.form['location']
        roomNum, shelfNum = selected_location.split('_')

        cursor = conn.cursor()
        query = 'SELECT * FROM Person WHERE userName = %s'
        cursor.execute(query, (donorID,))
        donor = cursor.fetchone()
        if not donor:
            cursor.close()
            return "Invalid Donor ID"

        verify_cat_query = "SELECT * FROM Category WHERE mainCategory=%s AND subCategory=%s"
        cursor.execute(verify_cat_query, (selected_main_cat, selected_sub_cat))
        cat_check = cursor.fetchone()
        if not cat_check:
            cursor.close()
            return "Invalid category or subcategory chosen."

        # Insert item
        ins_item = 'INSERT INTO Item (iDescription, mainCategory, subCategory) VALUES (%s,%s,%s)'
        cursor.execute(ins_item, (itemName, selected_main_cat, selected_sub_cat))
        itemID = cursor.lastrowid

        from datetime import date
        ins_donated = 'INSERT INTO DonatedBy (ItemID, userName, donateDate) VALUES (%s,%s,%s)'
        cursor.execute(ins_donated, (itemID, donorID, date.today()))

        # Updated query for Piece
        ins_piece = '''
        INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        '''
        pieceNum = 1  # Default to single piece
        cursor.execute(ins_piece, (itemID, pieceNum, 'Item piece', 10, 10, 10, roomNum, shelfNum))

        conn.commit()
        cursor.close()
        return "Donation Accepted"
    
    cursor = conn.cursor()
    loc_query = "SELECT roomNum, shelfNum, shelfDescription FROM Location"
    cursor.execute(loc_query)
    locations = cursor.fetchall()
    cursor.close()

    return render_template('accept_donation.html', categories=categories, locations=locations)

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
