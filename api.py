# /root/oper-kassa-bot/api.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('/root/oper-kassa-bot/.env')

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI не установлен в /root/oper-kassa-bot/.env")

client = MongoClient(MONGO_URI)
db = client["operkassa_db"]
rates_collection = db["rates"]

app = Flask(__name__)
# Разрешаем доступ с любого сайта (можно настроить конкретный домен)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route("/api/rates", methods=["GET"])
def get_rates():
    try:
        data = list(rates_collection.find({}, {"_id": 0}))
        return jsonify({"currencies": data}), 200 #MUST BE JSON
    except Exception as e:
        return jsonify({"error": "Не удалось получить курсы", "detail": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health():
    # Простая проверка работоспособности
    try:
        client.admin.command("ping")
        return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    # Для отладки; в продакшене systemd + gunicorn будет запускать приложение
    app.run(host="127.0.0.1", port=5000)
