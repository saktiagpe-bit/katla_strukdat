import urllib.request
import urllib.error
import random
import uuid
from flask import Flask, jsonify, render_template, request
from kbbi import KBBI, TidakDitemukan  

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response

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

active_games = {}

class GameState:
    def __init__(self, target_word, hint=""):
        self.target_word = list(target_word.upper())
        self.hint = hint
        self.guesses = LinkedList()
        self.max_attempts = 6
        self.is_finished = False
        self.is_won = False

    def get_attempts_count(self):
        return self.guesses.size

def validasi_kbbi(kata):
    kata = kata.lower()
    vokal = 'aiueo'
    
    if not any(v in kata for v in vokal):
        return False
        
    try:
        KBBI(kata)
        return True
    except TidakDitemukan:
        return False
    except Exception:
        pass

    try:
        url = f"https://kbbi.kemdikbud.go.id/entri/{kata}"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        response = urllib.request.urlopen(req, timeout=3)
        html = response.read().decode('utf-8')
        
        if "Entri tidak ditemukan" in html or "Pencarian Anda belum ditemukan" in html:
            return False
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return False
    except Exception:
        return False

TARGET_WORDS = {
    "ABADI": "Tidak ada akhirnya",
    "ABSEN": "Tidak hadir",
    "AGUNG": "Sangat besar dan mulia",
    "AKHIR": "Penghabisan",
    "AKRAB": "Sangat dekat",
    "AKTIF": "Giat bekerja",
    "ALAMI": "Bersifat alam",
    "BEBAS": "Lepas dari ikatan",
    "BENAR": "Sesuai dengan fakta",
    "BESAR": "Tidak kecil",
    "BUMBU": "Penyedap makanan",
    "CINTA": "Perasaan kasih sayang",
    "DUNIA": "Bumi dan segala isinya",
    "INDAH": "Enak dipandang mata",
    "KAMUS": "Buku referensi arti kata",
    "PUASA": "Menahan makan dan minum",
    "SABAR": "Tahan menghadapi cobaan",
    "SEHAT": "Bebas dari penyakit",
    "UTAMA": "Paling penting",
    "WAKTU": "Sesuatu yang terus berjalan dan tidak bisa kembali",
    "WARNA": "Corak rupa (seperti merah, biru)",
    "ZAMAN": "Jangka waktu panjang",
    "MAKAN": "Kalau lapar kita harus apa?"
}

def calculate_feedback(target_word_arr, guess_str):
    guess_arr = list(guess_str.upper())
    feedback = ["gray"] * 5
    
    if len(guess_arr) != 5 or len(target_word_arr) != 5:
        return ["gray", "gray", "gray", "gray", "gray"]
    
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-game', methods=['POST', 'OPTIONS'])
def start_game():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    target_word = random.choice(list(TARGET_WORDS.keys()))
    hint = TARGET_WORDS[target_word]
    
    game_id = str(uuid.uuid4())
    active_games[game_id] = GameState(target_word, hint)
    
    return jsonify({
        "success": True,
        "game_id": game_id,
        "max_attempts": 6,
        "hint": hint 
    })

@app.route('/api/guess', methods=['POST', 'OPTIONS'])
def submit_guess():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
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
        
    if guess not in TARGET_WORDS and not validasi_kbbi(guess):
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