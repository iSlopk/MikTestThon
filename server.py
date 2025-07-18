import os
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>SA</title>
            <style>
                body {
                    background: linear-gradient(to bottom, #1d3557, #457b9d); /* خلفية متدرجة */
                    color: white;
                    text-align: center;
                    font-family: 'Arial', sans-serif;
                    padding-top: 100px;
                }
                img {
                    width: 120px;
                    margin: 20px;
                    border: 2px solid white;
                    border-radius: 8px;
                }
                h1 {
                    font-size: 36px;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Mikthon is running</h1>
            <img src="https://flagcdn.com/w320/sa.png" alt="علم السعودية">
            <img src="https://flagcdn.com/w320/sy.png" alt="علم سوريا">
        </body>
        </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)