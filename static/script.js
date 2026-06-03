/**
 * LOGIKA FRONTEND KATLA (WORDLE INDONESIA)
 * Menggunakan Vanilla JavaScript & Integrasi REST API Flask
 */
document.addEventListener("DOMContentLoaded", () => {
    // State Permainan
    let gameId = null;
    let currentRow = 0;
    let currentCol = 0;
    let currentGuess = [];
    let isGameOver = false;
    let isWaitingForAPI = false;
    
    // Elements DOM
    const boardGrid = document.getElementById("board-grid");
    const keyboardContainer = document.querySelector(".keyboard-container");
    const toastContainer = document.getElementById("toast-container");
    
    // Modals & Buttons
    const helpBtn = document.getElementById("help-btn");
    const helpModal = document.getElementById("help-modal");
    const gameOverModal = document.getElementById("game-over-modal");
    const closeHelpBtn = document.getElementById("close-help");
    const playAgainBtn = document.getElementById("play-again-btn");
    
    // Stats Elements
    const gameOverTitle = document.getElementById("game-over-title");
    const gameOverMessage = document.getElementById("game-over-message");
    const statAttempts = document.getElementById("stat-attempts");
    const statWord = document.getElementById("stat-word");
    const visualHistory = document.getElementById("visual-history");
    const statsHistoryContainer = document.getElementById("stats-history-container");

    // ==========================================
    // INISIALISASI & API CALLS
    // ==========================================
    async function startNewGame() {
        try {
            // 1. Reset board UI total (Menghapus total sisa text dan warna visual)
            const tiles = document.querySelectorAll(".tile");
            tiles.forEach(tile => {
                tile.textContent = "";
                tile.className = "tile"; // Kembalikan ke class dasar agar warna lama lenyap
                tile.removeAttribute("style"); // Menghapus delay animasi lama
            });

            // 2. Reset keyboard UI (Mencopot paksa status 'correct', 'present', 'absent')
            const keys = document.querySelectorAll(".key");
            keys.forEach(key => {
                key.className = key.classList.contains("wide-key") ? "key wide-key" : "key";
            });

            // 3. Reset state logika global permainan
            currentRow = 0;
            currentCol = 0;
            currentGuess = [];
            isGameOver = false;
            isWaitingForAPI = false;
            
            // 4. Sembunyikan semua Pop-up Modal
            gameOverModal.classList.add("hidden");
            helpModal.classList.add("hidden");

            // 5. Ambil game_id baru dari Flask Backend
            const response = await fetch("/api/start-game", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            });
            const data = await response.json();
            
            if (data.success) {
                gameId = data.game_id;
                showToast("Katla baru dimulai! Tebak kata 5 huruf.", "info");
            } else {
                showToast("Gagal memulai permainan baru. Coba lagi.", "error");
            }
        } catch (error) {
            console.error("Error starting game:", error);
            showToast("Koneksi ke backend gagal.", "error");
        }
    }

    async function submitGuessAPI(guessWord) {
        isWaitingForAPI = true;
        try {
            const response = await fetch("/api/guess", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    game_id: gameId,
                    guess: guessWord
                })
            });
            const data = await response.json();
            if (!data.success) {
                showToast(data.error || "Kata tidak valid.", "error");
                shakeActiveRow();
                isWaitingForAPI = false;
                return;
            }
            
            // Tebakan valid, lakukan reveal warna per huruf
            revealColors(data.feedback, data.history);
            
            // Beri jeda waktu tunggu sampai animasi flip selesai berputar seluruhnya
            setTimeout(() => {
                if (data.is_finished) {
                    endGame(data.is_won, data.attempts, data.target_word, data.history);
                } else {
                    currentRow++;
                    currentCol = 0;
                    currentGuess = [];
                    isWaitingForAPI = false;
                }
            }, 500 + (5 * 100)); 
        } catch (error) {
            console.error("Error submitting guess:", error);
            showToast("Gagal memproses tebakan.", "error");
            isWaitingForAPI = false;
        }
    }

    // ==========================================
    // LOGIKA PERMAINAN & INPUT KATA
    // ==========================================
    function handleKeyPress(key) {
        if (isGameOver || isWaitingForAPI || !gameId) return;
        const uppercaseKey = key.toUpperCase();
        
        if (uppercaseKey === "ENTER") {
            if (currentGuess.length === 5) {
                const guessWord = currentGuess.join("");
                submitGuessAPI(guessWord);
            } else {
                showToast("Huruf belum lengkap! Harap isi 5 huruf.", "error");
                shakeActiveRow();
            }
        } else if (uppercaseKey === "BACKSPACE" || uppercaseKey === "BACK") {
            if (currentCol > 0) {
                currentCol--;
                currentGuess.pop();
                const tile = getTile(currentRow, currentCol);
                tile.textContent = "";
                tile.classList.remove("active-input", "pop-in");
            }
        } else if (/^[A-Z]$/.test(uppercaseKey)) {
            if (currentCol < 5) {
                currentGuess.push(uppercaseKey);
                const tile = getTile(currentRow, currentCol);
                tile.textContent = uppercaseKey;
                tile.classList.add("active-input", "pop-in");
                currentCol++;
            }
        }
    }

    function getTile(row, col) {
        return boardGrid.querySelector(`.board-row[data-row="${row}"] .tile[data-col="${col}"]`);
    }

    function shakeActiveRow() {
        const activeRow = boardGrid.querySelector(`.board-row[data-row="${currentRow}"]`);
        activeRow.classList.add("shake");
        setTimeout(() => {
            activeRow.classList.remove("shake");
        }, 500);
    }

    function revealColors(feedback, history) {
        const rowTiles = boardGrid.querySelectorAll(`.board-row[data-row="${currentRow}"] .tile`);
        
        rowTiles.forEach((tile, index) => {
            const colorState = feedback[index];
            tile.style.animationDelay = `${index * 100}ms`;
            
            if (colorState === "green") {
                tile.classList.add("reveal-correct");
            } else if (colorState === "yellow") {
                tile.classList.add("reveal-present");
            } else {
                tile.classList.add("reveal-absent");
            }
        });
        
        setTimeout(() => {
            updateKeyboardColors(history);
        }, 500 + (4 * 100));
    }

    function updateKeyboardColors(history) {
        const keyStates = {};
        history.forEach(round => {
            const guess = round.guess;
            const feedback = round.feedback;
            for (let i = 0; i < guess.length; i++) {
                const letter = guess[i];
                const state = feedback[i];
                if (!keyStates[letter]) {
                    keyStates[letter] = state;
                } else {
                    const currentState = keyStates[letter];
                    if (state === "green") {
                        keyStates[letter] = "green";
                    } else if (state === "yellow" && currentState !== "green") {
                        keyStates[letter] = "yellow";
                    } else if (state === "gray" && currentState !== "green" && currentState !== "yellow") {
                        keyStates[letter] = "gray";
                    }
                }
            }
        });

        for (const [letter, state] of Object.entries(keyStates)) {
            const keyButton = keyboardContainer.querySelector(`.key[data-key="${letter}"]`);
            if (keyButton) {
                keyButton.classList.remove("correct", "present", "absent");
                if (state === "green") {
                    keyButton.classList.add("correct");
                } else if (state === "yellow") {
                    keyButton.classList.add("present");
                } else if (state === "gray") {
                    keyButton.classList.add("absent");
                }
            }
        }
    }

    // ==========================================
    // AKHIR GAME & STATISTIK
    // ==========================================
    function endGame(isWon, attempts, targetWord, history) {
        isGameOver = true;
        
        gameOverTitle.textContent = isWon ? "Luar Biasa! 🎉" : "Sayang Sekali... 😢";
        gameOverMessage.textContent = isWon 
            ? `Anda berhasil menebak kata rahasia dalam ${attempts} percobaan.` 
            : "Percobaan Anda habis. Jangan menyerah!";
        
        statAttempts.textContent = isWon ? attempts : "X";
        statWord.textContent = targetWord;

        let visualGrid = `Katla ${isWon ? attempts : 'X'}/6\n\n`;
        history.forEach(round => {
            const emojiRow = round.feedback.map(color => {
                if (color === "green") return "🟩";
                if (color === "yellow") return "🟨";
                return "⬛";
            }).join("");
            visualGrid += emojiRow + "\n";
        });
        
        visualHistory.innerHTML = visualGrid.replace(/\n/g, "<br>");
        statsHistoryContainer.classList.remove("hidden");
        
        setTimeout(() => {
            gameOverModal.classList.remove("hidden");
        }, 1200);
    }

    // ==========================================
    // TOAST SYSTEM (NOTIFIKASI)
    // ==========================================
    function showToast(message, type = "error") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 2000);
    }

    // ==========================================
    // EVENT LISTENERS
    // ==========================================
    
    // 1. Deteksi Keyboard Fisik Laptop/PC
    document.addEventListener("keydown", (e) => {
        if (e.altKey || e.ctrlKey || e.metaKey) return;
        let key = e.key;
        if (key === "Delete") key = "Backspace";
        handleKeyPress(key);
    });

    // 2. Deteksi Klik Keyboard Virtual Layar
    keyboardContainer.addEventListener("click", (e) => {
        const keyBtn = e.target.closest(".key");
        if (!keyBtn) return;
        const keyValue = keyBtn.getAttribute("data-key");
        handleKeyPress(keyValue);
    });

    // 3. Tombol Buka Tutup Modal Bantuan
    helpBtn.addEventListener("click", () => {
        helpModal.classList.remove("hidden");
    });
    closeHelpBtn.addEventListener("click", () => {
        helpModal.classList.add("hidden");
    });
    window.addEventListener("click", (e) => {
        if (e.target === helpModal) {
            helpModal.classList.add("hidden");
        }
    });

    // 4. Reset Ulang ketika Tombol Main Lagi di-klik
    playAgainBtn.addEventListener("click", () => {
        startNewGame();
    });

    // Jalankan inisialisasi game awal
    startNewGame();
});