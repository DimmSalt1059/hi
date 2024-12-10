from flask import Flask, request, jsonify, session
import requests
import logging
import os
from flask_cors import CORS
from dotenv import load_dotenv
import uuid

# 載入 .env 中的環境變數
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 必须设置以支持 session
CORS(app)

# 設置日志功能
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return "Hello, World!"

# 從環境變數中讀取 xai API 的 URL 和 API 金钥
XAI_API_URL = os.getenv("XAI_API_URL", "https://api.x.ai/v1/chat/completions")
XAI_API_KEY = os.getenv("XAI_API_KEY")

# 確認 API 金鑰是否已成功讀取
if not XAI_API_KEY:
    raise ValueError("xai API 金钥未设置，请在 .env 文件中设置 XAI_API_KEY")

# 開發時可檢查
print("XAI_API_KEY 已讀取成功:", XAI_API_KEY)

# 角色对应的系统提示
character_prompts = {
    "石化女": "你是一个具有神秘能力的石化女，回答问题时需要保持神秘和冷静。",
    "女巫婆婆": "你是一位智慧而慈祥的女巫婆婆，回答问题时需要展现智慧与温暖。"
}

# 初始化对话存储
conversation_memory = {}

@app.route('/chat', methods=['POST'])
def chat():
    # 获取当前用户的 session_id
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    user_id = session['session_id']

    logging.info(f"当前用户 session_id: {user_id}")

    data = request.get_json()
    user_message = data.get("message", "")
    character_name = data.get("character", "")

    logging.info(f"用户 {user_id} - 角色: {character_name}, 讯息: {user_message}")

    if user_message.strip() == "":
        logging.warning("空讯息，请求中未包含有效的讯息")
        return jsonify({"message": "空讯息，请输入内容。"})

    conversation_key = f"{user_id}-{character_name}"
    if conversation_key not in conversation_memory:
        logging.info(f"初始化新对话上下文: {conversation_key}")
        conversation_memory[conversation_key] = [
            {"role": "system", "content": character_prompts.get(character_name, "")}
        ]

    # 增加用户的讯息到聊天记录
    conversation_memory[conversation_key].append({"role": "user", "content": user_message})

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}"
        }

        logging.info("发送请求到 xai API")
        xai_response = requests.post(
            XAI_API_URL,
            json={
                "messages": conversation_memory[conversation_key],
                "model": "grok-beta",
                "stream": False,
                "temperature": 0
            },
            headers=headers
        )

        if xai_response.status_code == 200:
            xai_data = xai_response.json()
            ai_message = xai_data['choices'][0]['message']['content']

            conversation_memory[conversation_key].append({"role": "assistant", "content": ai_message})

            logging.info(f"xai 回应成功 - 回应内容: {ai_message}")
            return jsonify({"message": ai_message})
        else:
            logging.error(f"xai 回应失败 - 状态码: {xai_response.status_code}, 错误讯息: {xai_response.text}")
            return jsonify({"message": "xai 回应失败，请稍后再试。"}), 500

    except Exception as e:
        logging.error(f"处理请求时发生错误: {str(e)}")
        return jsonify({"message": f"发生错误：{str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
