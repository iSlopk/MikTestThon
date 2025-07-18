import os
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Mikthon</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-image: url('https://files.catbox.moe/lcyvdn.jpg'); /* رابط الصورة */
                    background-size: cover;
                    background-position: center;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    overflow: hidden;
                }

                .overlay {
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    backdrop-filter: blur(8px); /* تأثير البلور */
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    color: white;
                    font-family: 'Arial', sans-serif;
                }

                .wings {
                    display: flex;
                    gap: 100px;
                    align-items: center;
                    margin-bottom: 20px;
                }

                .wing {
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .wing img {
                    width: 120px;
                    transform: rotate(15deg);
                    transition: transform 0.3s ease-in-out;
                }

                .wing.left img {
                    transform: rotate(-15deg);
                }

                .wing span {
                    position: absolute;
                    top: -25px;
                    font-size: 32px;
                    font-weight: bold;
                    color: white;
                    text-shadow: 2px 2px 4px black;
                }

                h2 {
                    font-size: 32px;
                    margin-top: 10px;
                    text-shadow: 2px 2px 8px black;
                }
            </style>
        </head>
        <body>
            <div class="overlay">
                <div class="wings">
                    <div class="wing left">
                        <span>S</span>
                        <img src="https://flagcdn.com/w320/sy.png" alt="Syria Flag">
                    </div>
                    <div class="wing right">
                        <span>A</span>
                        <img src="https://flagcdn.com/w320/sa.png" alt="Saudi Flag">
                    </div>
                </div>
                <h2>Mikthon is running</h2>
            </div>
        </body>
        </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)