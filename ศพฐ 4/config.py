import os

# Server Configuration
PORT = int(os.environ.get("PORT", 5000))
HOST = os.environ.get("HOST", "0.0.0.0")

# Security Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "spb4-secret-key-chatbot-2026")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

# Database Configuration
DATABASE_NAME = os.environ.get("DATABASE_NAME", "chatbot.db")

# Option for Gemini API
# If GEMINI_API_KEY is provided, we can use it to reply when the bot cannot match any FAQ
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDk-xYL-0-U00VX2RzDSXv_dq94-EQ_Blk")
