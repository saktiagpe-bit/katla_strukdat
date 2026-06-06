import os
import random
import uuid
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response

# bagian terkecil linked list buat nyimpen data sama pointer ke node selanjutnya
class Node:
    def __init__(self, data):
        self.data = data  # isi tebakan sama feedback warna
        self.next = None  # lanjutannya ke mana

# linked list buat nyimpen riwayat tebakan biar dinamis
class LinkedList:
    def __init__(self):
        self.head = None  # mulai dari kosong dulu
        self.size = 0     # ketahuan udah berapa kali nebak

    # fungsi buat nambahin tebakan baru di baris paling belakang
    def append(self, data):
        new_node = Node(data)
        if not self.head:
            self.head = new_node  # kalau masih kosong langsung jadi yang pertama
        else:
            # jalan dari depan sampai nemu ujungnya
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node  # sambungin node baru di paling ujung
        self.size += 1

    # convert linked list ke list biasa biar bisa dibaca sama json backend
    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append(current.data)  # masukin datanya satu-satu
            current = current.next       # geser ke node depan
        return result

active_games = {}

class GameState:
    def __init__(self, target_word, hint=""):
        # mecah string kata rahasia jadi array huruf biar gampang dicek per indeks
        self.target_word = list(target_word.upper())
        self.hint = hint
        self.guesses = LinkedList() # simpan riwayat tebakan pake linked list di atas
        self.max_attempts = 6
        self.is_finished = False
        self.is_won = False

    def get_attempts_count(self):
        return self.guesses.size

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
    "NANAS": "Buah bersisik kuning yang menyegarkan",
    "PUASA": "Menahan makan dan minum",
    "SABAR": "Tahan menghadapi cobaan",
    "SEHAT": "Bebas dari penyakit",
    "UTAMA": "Paling penting",
    "WAKTU": "Sesuatu yang terus berjalan dan tidak bisa kembali",
    "WARNA": "Corak rupa (seperti merah, biru)",
    "ZAMAN": "Jangka waktu panjang",
    "MAKAN": "Kalau lapar kita harus apa?"
}

# pakai hash set biar proses nyari katanya instan dan ga bikin server lemot
KAMUS_LOKAL_SET = set()
NAMA_FILE_KAMUS = "kamus.csv"

print(f"Sedang memuat database kamus dari file {NAMA_FILE_KAMUS}...")

if os.path.exists(NAMA_FILE_KAMUS):
    with open(NAMA_FILE_KAMUS, "r", encoding="utf-8") as file:
        for baris in file:
            # bersihin spasi bawaan atau koma formatting csv biar murni teks aja
            kata_bersih = baris.strip().replace(",", "").lower()
            if kata_bersih:
                KAMUS_LOKAL_SET.add(kata_bersih) # masukin ke set ram
    print(f"Sukses! Memuat {len(KAMUS_LOKAL_SET)} kata ke dalam sistem.")
else:
    print(f"Peringatan: File '{NAMA_FILE_KAMUS}' tidak ditemukan! Game hanya mendeteksi TARGET_WORDS.")

def validasi_kamus(kata):
    kata = kata.lower().strip()
    
    # amanin dulu kalau tebakannya ternyata ada di daftar kata rahasia utama
    if kata.upper() in TARGET_WORDS:
        return True
        
    # langsung cocokin ke set database kamus csv offline yang ada di ram
    if kata in KAMUS_LOKAL_SET:
        return True
        
    # kalau beneran ga ketemu di mana-mana langsung tolak tebakannya
    return False

def calculate_feedback(target_word_arr, guess_str):
    guess_arr = list(guess_str.upper())
    feedback = ["gray"] * 5
    
    if len(guess_arr) != 5 or len(target_word_arr) != 5:
        return ["gray", "gray", "gray", "gray", "gray"]
    
    # pake dictionary hash map buat ngitung jumlah huruf biar ga ngebug kalau ada huruf kembar
    target_counts = {}
    for char in target_word_arr:
        target_counts[char] = target_counts.get(char, 0) + 1
        
    # step 1: cek dulu huruf yang posisinya udah pas banget (kasih warna ijo)
    for i in range(5):
        if guess_arr[i] == target_word_arr[i]:
            feedback[i] = "green"
            target_counts[guess_arr[i]] -= 1  # jatah huruf ijo dikurangin
            
    # step 2: baru cek huruf yang ada di kata target tapi salah posisi (kasih warna kuning)
    for i in range(5):
        if feedback[i] == "green":
            continue
        char = guess_arr[i]
        # sisa jatah hurufnya dicek lewat dictionary target_counts
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
        
    if guess not in TARGET_WORDS and not validasi_kamus(guess):
        return jsonify({"success": False, "error": "Kata tidak terdaftar dalam Kamus."}), 400
        
    feedback = calculate_feedback(game_state.target_word, guess)
    
    guess_record = {
        "guess": guess,
        "feedback": feedback
    }
    
    # simpan record hasil tebakan barusan ke dalam struktur data linked list
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
        # lempar riwayat data linked list yang udah di-convert ke list biasa
        "history": game_state.guesses.to_list()
    }
    
    if game_state.is_finished:
        response_data["target_word"] = "".join(game_state.target_word)
        
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)