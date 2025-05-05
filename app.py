from PIL import Image
import sqlite3
import pytesseract
import cv2

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from flask import Flask, render_template, redirect, request

import re
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

img = Image.open('uploads/image.jpg')
text = pytesseract.image_to_string(img)
print(text)

def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    amount INTEGER NOT NULL,
    date TEXT NOT NULL)
    ''')
    conn.commit()
    conn.close()
@app.route('/')
def index():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM purchases ORDER BY date DESC")
    purchases = c.fetchall()

    c.execute("SELECT SUM(amount) FROM purchases")
    total = c.fetchone()[0] or 0.0

    conn.close()
    return render_template("index.html", purchases=purchases, total=total)


@app.route('/add', methods = ['GET', 'POST'])
def add():
    if request.method == 'POST':
        item = request.form['item']
        amount = request.form['amount']
        date = request.form['date']

        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("INSERT INTO purchases (item, amount, date) VALUES (?, ?, ?)", (item, amount, date))

        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('add.html')



@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        file = request.files['receipt']
        if not file:
            return redirect('/')

        path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(path)

        image = Image.open(path)
        text = pytesseract.image_to_string(image)

        lines = [line.strip() for line in text.split('\n') if line.strip()]
        item = "Unknown"

        # Try to find the first item-looking line (contains price, not "TOTAL")
        for line in lines:
            if re.search(r'\d+\.\d{2}', line) and "total" not in line.lower():
                # Optional: extract item name before price
                match = re.match(r'(.*?)(\d+\.\d{2})', line)
                if match:
                    item = match.group(1).strip()
                else:
                    item = line
                break

        # 2. Extract total amount – use the highest value with decimal
        amounts = [float(m.group()) for m in map(lambda l: re.search(r'\d+\.\d{2}', l), lines) if m]
        amount = max(amounts) if amounts else 0.0

        # 3. Extract date – multiple formats supported
        date = "Unknown"
        date_patterns = [
            r'\d{4}[-/]\d{2}[-/]\d{2}',  # 2025-05-05 or 2025/05/05
            r'\d{2}[-/]\d{2}[-/]\d{4}',  # 05-05-2025 or 05/05/2025
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date = match.group()
                break

        # Insert into DB
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("INSERT INTO purchases (item, amount, date) VALUES (?, ?, ?)", (item, amount, date))
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("scan.html")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)