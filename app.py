"""
خدمة فحص صحي بسيطة (Health Check) لإبقاء الاستضافة تعتبر التطبيق حياً.
تُستخدم فقط في وضع Long Polling، لأن وضع Webhook يستخدم المنفذ نفسه.
"""

import logging
from threading import Thread

from flask import Flask, jsonify

from config.settings import PORT

app = Flask("saudi_jobs_bot_health")

# تقليل ضجيج سجلات Flask
logging.getLogger("werkzeug").setLevel(logging.WARNING)


@app.route("/")
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "saudi-jobs-telegram-bot"})


def run():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


def server():
    """تشغيل خدمة الفحص في خيط خلفي لا يمنع إيقاف البوت."""
    thread = Thread(target=run, daemon=True, name="health-server")
    thread.start()
    return thread
