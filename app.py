from flask import Flask, jsonify
from database import get_users
import config
import boto3
import json

app = Flask(__name__)


def get_secret():
    """Read secrets from AWS Secrets Manager at runtime"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId='capstone/app-secrets')
        return json.loads(response['SecretString'])
    except Exception:
        return {}


secrets = get_secret()


@app.route("/")
def home():
    return jsonify({
        "message": "Internal Utility Service Running",
        "environment": config.ENVIRONMENT,
        "db_host": config.DB_HOST
    })


@app.route("/health")
def health():
    return jsonify({"status": "UP"}), 200


@app.route("/users")
def users():
    return jsonify(get_users())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)