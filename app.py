from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid

app = Flask(__name__)
CORS(app)

# Use environment variables for API key
API_KEY = os.getenv("API_KEY", str(uuid.uuid4()))
print(f"当前 API Key: {API_KEY}")

@app.route('/get-api-key', methods=['GET'])
def get_api_key():
    return jsonify({"api_key": API_KEY})

@app.route('/')
def home():
    return jsonify({"status": "API is running", "endpoints": ["/get-api-key", "/scrape"]})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
