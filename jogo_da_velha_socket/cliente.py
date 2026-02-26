import socket
import ssl
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

PORT = 5000
DISCOVERY_PORT = 5001

nickname = ""
my_symbol = "-"
current_opponent = "-"
board_buttons = []

# ================= DESCOBERTA AUTOMÁTICA (NOVO) =================

def discover_server_ip():
    """Escuta o sinal de broadcast do servidor para obter o IP automaticamente.
    A mensagem pode vir no formato "TIC_TAC_TOE_SERVER_HERE <ip>" ou apenas a tag.
    """
    print("A procurar servidor na rede local...")
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Permite que várias instâncias escutem a mesma porta se necessário
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discovery_socket.bind(('', DISCOVERY_PORT))
    
    while True:
        try:
            data, addr = discovery_socket.recvfrom(1024)
            text = data.decode()
            if text.startswith("TIC_TAC_TOE_SERVER_HERE"):
                parts = text.split()
                if len(parts) >= 2:
                    ip = parts[1]
                else:
                    ip = addr[0]
                print(f"Servidor encontrado no IP: {ip}")
                discovery_socket.close()
                return ip
        except Exception as e:
            print(f"Erro na descoberta: {e}")

# Obtém o HOST dinamicamente antes de prosseguir
HOST = discover_server_ip()

# ================= SOCKET =================

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client = context.wrap_socket(raw, server_hostname=HOST)
client.connect((HOST, PORT))

def send(msg):
    client.send((msg + "\n").encode())

# ================= LOGIN =================

while True:
    nickname = simpledialog.askstring("Login", "Digite seu nickname:")
    if not nickname:
        exit()
    send(f"REGISTER {nickname}")
    response = client.recv(1024).decode().strip()
    if response == "OK":
        break
    else:
        messagebox.showerror("Erro", "Nickname já está em uso")

# ================= GUI =================

root = tk.Tk()
root.title("Jogo da Velha Online")
root.geometry("1000x600")
root.configure(bg="#1e1e1e")

# ===== Painel lateral =====

side_frame = tk.Frame(root, bg="#2b2b2b", width=250)
side_frame.pack(side="left", fill="y")

tk.Label(side_frame, text="Usuário conectado",
         bg="#2b2b2b", fg="white",
         font=("Segoe UI", 11, "bold")).pack(pady=(20,5))

tk.Label(side_frame, text=nickname,
         bg="#2b2b2b", fg="#4CAF50",
         font=("Segoe UI", 12)).pack()

tk.Label(side_frame, text="Usuários online",
         bg="#2b2b2b", fg="white",
         font=("Segoe UI", 11, "bold")).pack(pady=(30,5))

users_listbox = tk.Listbox(side_frame,
                           bg="#3a3a3a",
                           fg="white",
                           selectbackground="#4CAF50",
                           relief="flat")
users_listbox.pack(padx=20, pady=10, fill="both")

def prevent_self_selection(event):
    selection = users_listbox.curselection()
    if selection:
        # Se o item clicado for o próprio nickname, remove a seleção
        if users_listbox.get(selection[0]) == nickname:
            users_listbox.selection_clear(selection[0])

users_listbox.bind("<<ListboxSelect>>", prevent_self_selection)

def challenge():
    selection = users_listbox.curselection()
    if selection:
        opponent = users_listbox.get(selection[0])
        if opponent != nickname:
            send(f"INVITE {opponent}")

challenge_btn = tk.Button(side_frame,
                          text="Desafiar",
                          bg="#4CAF50",
                          fg="white",
                          relief="flat",
                          command=challenge)
challenge_btn.pack(pady=10)

# ===== Área do jogo =====

main_frame = tk.Frame(root, bg="#1e1e1e")
main_frame.pack(side="right", expand=True, fill="both")

info_frame = tk.Frame(main_frame, bg="#1e1e1e")
info_frame.pack(pady=20)

opponent_label = tk.Label(info_frame,
                          text="Oponente: -",
                          bg="#1e1e1e",
                          fg="white",
                          font=("Segoe UI", 12))
opponent_label.pack()

symbol_label = tk.Label(info_frame,
                        text="Símbolo: -",
                        bg="#1e1e1e",
                        fg="white",
                        font=("Segoe UI", 12))
symbol_label.pack()

status_label = tk.Label(info_frame,
                        text="Aguardando...",
                        bg="#1e1e1e",
                        fg="#bbbbbb",
                        font=("Segoe UI", 11))
status_label.pack()

countdown_label = tk.Label(info_frame,
                           text="",
                           bg="#1e1e1e",
                           fg="#4CAF50",
                           font=("Segoe UI", 16))
countdown_label.pack()

# ===== Tabuleiro =====

board_frame = tk.Frame(main_frame, bg="#1e1e1e")
board_frame.pack(pady=30)

def send_move(i):
    send(f"MOVE {i}")

def reset_board():
    for btn in board_buttons:
        btn.config(text="", state="normal", bg="#3a3a3a")

def disable_board():
    for btn in board_buttons:
        btn.config(state="disabled")

for i in range(9):
    btn = tk.Button(board_frame,
                    text="",
                    font=("Segoe UI", 22, "bold"),
                    width=4,
                    height=2,
                    bg="#3a3a3a",
                    fg="white",
                    relief="flat",
                    state="disabled",
                    command=lambda i=i: send_move(i))
    btn.grid(row=i//3, column=i%3, padx=8, pady=8)
    board_buttons.append(btn)

# ================= RECEBER =================

def receive():
    global my_symbol, current_opponent

    while True:
        try:
            msg = client.recv(1024).decode().strip()
            if not msg:
                break
            
            parts = msg.split()

            if parts[0] == "USER_LIST":
                users_listbox.delete(0, tk.END)
                if len(parts) > 1:
                    for u in parts[1].split(","):
                        users_listbox.insert(tk.END, u)

            elif parts[0] == "INVITE_FROM":
                if messagebox.askyesno("Convite",
                                       f"{parts[1]} quer jogar. Aceitar?"):
                    current_opponent = parts[1]
                    send(f"ACCEPT {parts[1]}")

            elif parts[0] == "COUNTDOWN":
                countdown_label.config(text=f"Iniciando em {parts[1]}")

            elif parts[0] == "START":
                countdown_label.config(text="")
                my_symbol = parts[1]
                symbol_label.config(text=f"Símbolo: {my_symbol}")
                opponent_label.config(text=f"Oponente: {current_opponent}")
                reset_board()

            elif parts[0] == "UPDATE":
                pos = int(parts[1])
                board_buttons[pos].config(text=parts[2])

            elif parts[0] == "YOUR_TURN":
                status_label.config(text="Sua vez")

            elif parts[0] == "WAIT":
                status_label.config(text="Aguardando jogada do oponente")

            elif parts[0] in ["VICTORY", "DEFEAT", "DRAW", "TIMEOUT"]:
                reset_board()   
                disable_board() 
                symbol_label.config(text="Símbolo: -")
                opponent_label.config(text="Oponente: -")
                status_label.config(text="Partida finalizada")
                messagebox.showinfo("Resultado", parts[0])
                reset_board()

        except:
            break

threading.Thread(target=receive, daemon=True).start()

root.mainloop()