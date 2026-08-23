import os
import json
import uuid

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai


# =========================
# ENVIRONMENT
# =========================

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)


# =========================
# CHAT FILE
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHAT_FILE = os.path.join(
    BASE_DIR,
    "chats.json"
)


def load_chats():

    try:
        with open(
            CHAT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):

        return {}


def save_chats(chats):

    with open(
        CHAT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chats,
            file,
            indent=4,
            ensure_ascii=False
        )


chats = load_chats()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================
# NEW CHAT
# =========================

@app.route(
    "/new-chat",
    methods=["POST"]
)
def new_chat():

    global chats

    chats = load_chats()

    chat_id = str(
        uuid.uuid4()
    )

    chats[chat_id] = {
        "title": "New conversation",
        "messages": []
    }

    save_chats(chats)

    return jsonify({
        "chat_id": chat_id,
        "title": "New conversation"
    })


# =========================
# SEND MESSAGE
# =========================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    global chats

    chats = load_chats()

    data = request.get_json()

    if not data:

        return jsonify({
            "reply": "No data received."
        }), 400


    user_message = (
        data
        .get("message", "")
        .strip()
    )

    chat_id = data.get(
        "chat_id"
    )


    if not user_message:

        return jsonify({
            "reply": "Please type a message."
        }), 400


    # Create chat automatically
    if (
        not chat_id
        or
        chat_id not in chats
    ):

        chat_id = str(
            uuid.uuid4()
        )

        chats[chat_id] = {
            "title": user_message[:40],
            "messages": []
        }


    current_chat = chats[
        chat_id
    ]


    # Save user message
    current_chat[
        "messages"
    ].append({
        "role": "user",
        "text": user_message
    })


    # First message becomes title
    if (
        current_chat["title"]
        ==
        "New conversation"
    ):

        current_chat[
            "title"
        ] = user_message[:40]


    save_chats(chats)


    # Build conversation memory
    conversation = ""

    for item in current_chat[
        "messages"
    ]:

        if item["role"] == "user":

            conversation += (
                "User: "
                + item["text"]
                + "\n"
            )

        else:

            conversation += (
                "Assistant: "
                + item["text"]
                + "\n"
            )


    conversation += "Assistant:"


    try:

        response = (
            client
            .models
            .generate_content(
                model="gemini-3.5-flash-lite",
                contents=conversation
            )
        )

        ai_reply = (
            response.text
            or
            "I could not generate a response."
        )


        # Save AI response
        current_chat[
            "messages"
        ].append({
            "role": "assistant",
            "text": ai_reply
        })

        save_chats(chats)


        return jsonify({
            "reply": ai_reply,
            "chat_id": chat_id,
            "title": current_chat["title"]
        })


    except Exception as error:

        print(
            "GEMINI ERROR:",
            repr(error)
        )

        return jsonify({
            "reply": "Sorry, AI response generate nahi ho paya."
        }), 500


# =========================
# GET ALL CHATS
# =========================

@app.route(
    "/chats",
    methods=["GET"]
)
def get_chats():

    saved_chats = load_chats()

    result = []

    for (
        chat_id,
        chat_data
    ) in saved_chats.items():

        result.append({
            "id": chat_id,
            "title": chat_data.get(
                "title",
                "New conversation"
            )
        })


    return jsonify(
        result
    )


# =========================
# OPEN CHAT
# =========================

@app.route(
    "/chat/<chat_id>",
    methods=["GET"]
)
def get_chat(chat_id):

    saved_chats = load_chats()

    if (
        chat_id
        not in saved_chats
    ):

        return jsonify({
            "error": "Chat not found"
        }), 404


    return jsonify(
        saved_chats[
            chat_id
        ]
    )


# =========================
# DELETE CHAT
# =========================

@app.route(
    "/chat/<chat_id>",
    methods=["DELETE"]
)
def delete_chat(chat_id):

    global chats

    chats = load_chats()

    if chat_id in chats:

        del chats[
            chat_id
        ]

        save_chats(
            chats
        )


    return jsonify({
        "success": True
    })


# =========================
# RENAME CHAT
# =========================

@app.route(
    "/rename-chat/<chat_id>",
    methods=["PUT"]
)
def rename_chat(chat_id):

    global chats

    data = request.get_json()

    new_title = (
        data
        .get("title", "")
        .strip()
    )


    if not new_title:

        return jsonify({
            "success": False,
            "error": "Title cannot be empty"
        }), 400


    chats = load_chats()


    if chat_id not in chats:

        return jsonify({
            "success": False,
            "error": "Chat not found"
        }), 404


    chats[
        chat_id
    ]["title"] = new_title[:60]


    save_chats(
        chats
    )


    return jsonify({
        "success": True,
        "title": chats[
            chat_id
        ]["title"]
    })


# =========================
# RUN
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )