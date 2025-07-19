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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                margin: 0;
                padding: 0;
                background-image: url('https://files.catbox.moe/4ayhwh.jpg');
                background-size: cover;
                background-position: center;
                height: 100vh;
                overflow: hidden;
                font-family: 'Arial', sans-serif;
            }

            .overlay {
                position: absolute;
                width: 100%;
                height: 100%;
                backdrop-filter: blur(8px);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                text-align: center;
                padding: 10px;
            }

            .sky {
                display: flex;
                align-items: flex-end;
                justify-content: center;
                gap: 30px;
                flex-wrap: wrap;
            }

            .wing {
                position: relative;
                display: flex;
                flex-direction: column;
                align-items: center;
                animation: flap 2s ease-in-out infinite;
            }

            .wing img {
                width: 100px;
                height: auto;
                border-radius: 6px;
                box-shadow: 0 0 10px rgba(0,0,0,0.4);
            }

            .wing span {
                position: absolute;
                top: -30px;
                font-size: 24px;
                font-weight: bold;
                color: white;
                text-shadow: 2px 2px 4px black;
            }

            .dove-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                position: relative;
                animation: flap 2.5s ease-in-out infinite;
            }

            .dove-container img {
                width: 70px;
                height: auto;
                filter: drop-shadow(0 0 10px white);
            }

            .heart {
                font-size: 24px;
                color: pink;
                margin-bottom: 5px;
                text-shadow: 2px 2px 6px red;
            }

            h2 {
                margin-top: 30px;
                font-size: 22px;
                text-shadow: 2px 2px 8px black;
            }

            @keyframes flap {
                0%, 100% {
                    transform: translateY(0) rotate(0deg);
                }
                50% {
                    transform: translateY(-5px) rotate(1deg);
                }
            }

            @media (max-width: 600px) {
                .sky {
                    gap: 15px;
                }

                .wing img,
                .dove-container img {
                    width: 70px;
                }

                .wing span {
                    font-size: 18px;
                    top: -20px;
                }

                .heart {
                    font-size: 18px;
                }

                h2 {
                    font-size: 18px;
                }
            }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="sky">
                <div class="wing left">
                    <span>S</span>
                    <img src="https://flagcdn.com/w320/sy.png" alt="Syria Flag">
                </div>
                <div class="dove-container">
                    <div class="heart">♡</div>
                    <img src="https://gallery.yopriceville.com/var/resizes/Free-Clipart-Pictures/Birds-PNG/White_Flying_Dove_PNG_Clipart.png?m=1507172112" alt="Dove">
                </div>
                <div class="wing right">
                    <span>A</span>
                    <img src="https://flagcdn.com/w320/sa.png" alt="Saudi Flag">
                </div>
            </div>
            <h2>Mikthon is running</h2>
        </div>

        <!-- 🇸🇦 نشيد المملكة -->
        <audio autoplay>
            <source src="https://ia800209.us.archive.org/33/items/SaudiNationalAnthem/النشيد_الوطني_السعودي.mp3" type="audio/mpeg">
            متصفحك لا يدعم الصوت.
        </audio>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)