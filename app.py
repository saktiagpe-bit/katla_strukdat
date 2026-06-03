import random
import uuid
from flask import Flask, jsonify, render_template, request
from kbbi import KBBI, TidakDitemukan  # Menggunakan KBBI Lokal Offline

app = Flask(__name__)

# ==========================================
# STRUCTURE DATA (Node & Linked List)
# ==========================================
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    def __init__(self):
        self.head = None
        self.size = 0

    def append(self, data):
        new_node = Node(data)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node
        self.size += 1

    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append(current.data)
            current = current.next
        return result

# ==========================================
# GAME STATE
# ==========================================
active_games = {}

class GameState:
    def __init__(self, target_word):
        self.target_word = list(target_word.upper())
        self.guesses = LinkedList()
        self.max_attempts = 6
        self.is_finished = False
        self.is_won = False

    def get_attempts_count(self):
        return self.guesses.size

# ==========================================
# OFFLINE KBBI VALIDATION
# ==========================================
def cek_kata_di_kbbi(kata):
    """Mengecek kevalidan kata secara offline menggunakan library kbbi."""
    try:
        KBBI(kata.lower())
        return True
    except TidakDitemukan:
        return False
    except Exception as e:
        print(f"Error KBBI: {e}")
        return True 

# Daftar sampel kata target umum
TARGET_WORDS = ["ABADI", "ABSEN", "AGUNG", "AKHIR", "AKRAB", "AKTIF", "ALAMI", "BEBAS", "BENAR", "BESAR", "DUNIA", "MUTU", "PUASA", "SABAR", "SEHAT", "UTAMA", "WARNA", "ZAMAN"]

# ==========================================
# FEEDBACK LOGIC
# ==========================================
def calculate_feedback(target_word_arr, guess_str):
    guess_arr = list(guess_str.upper())
    feedback = ["gray"] * 5
    
    target_counts = {}
    for char in target_word_arr:
        target_counts[char] = target_counts.get(char, 0) + 1
        
    for i in range(5):
        if guess_arr[i] == target_word_arr[i]:
            feedback[i] = "green"
            target_counts[guess_arr[i]] -= 1
            
    for i in range(5):
        if feedback[i] == "green":
            continue
        char = guess_arr[i]
        if char in target_counts and target_counts[char] > 0:
            feedback[i] = "yellow"
            target_counts[char] -= 1
            
    return feedback

# ==========================================
# API ENDPOINTS
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-game', methods=['POST'])
def start_game():
    target_word = random.choice(TARGET_WORDS)
    game_id = str(uuid.uuid4())
    active_games[game_id] = GameState(target_word)
    return jsonify({
        "success": True,
        "game_id": game_id,
        "max_attempts": 6
    })

@app.route('/api/guess', methods=['POST'])
def submit_guess():
    data = request.get_json() or {}
    game_id = data.get("game_id")
    guess = data.get("guess", "").strip().upper()
    
    if not game_id or game_id not in active_games:
        return jsonify({"success": False, "error": "Sesi game tidak valid."}), 400
        
    game_state = active_games[game_id]
    if game_state.is_finished:
        return jsonify({"success": False, "error": "Game ini sudah selesai."}), 400
    if len(guess) != 5:
        return jsonify({"success": False, "error": "Tebakan harus terdiri dari 5 huruf."}), 400
        
    # Validasi kata via library KBBI offline
    if not cek_kata_di_kbbi(guess):
        return jsonify({"success": False, "error": "Kata tidak terdaftar dalam KBBI."}), 400
        
    feedback = calculate_feedback(game_state.target_word, guess)
    
    guess_record = {
        "guess": guess,
        "feedback": feedback
    }
    game_state.guesses.append(guess_record)
    
    is_won = all(color == "green" for color in feedback)
    attempts_count = game_state.get_attempts_count()
    
    if is_won:
        game_state.is_finished = True
        game_state.is_won = True
    elif attempts_count >= game_state.max_attempts:
        game_state.is_finished = True
        game_state.is_won = False
        
    response_data = {
        "success": True,
        "guess": guess,
        "feedback": feedback,
        "attempts": attempts_count,
        "is_finished": game_state.is_finished,
        "is_won": game_state.is_won,
        "history": game_state.guesses.to_list()
    }
    
    if game_state.is_finished:
        response_data["target_word"] = "".join(game_state.target_word)
        
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)