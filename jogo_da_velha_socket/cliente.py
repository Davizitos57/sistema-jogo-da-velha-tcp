import socket
import ssl
import threading
import tkinter as tk

PORT = 5000
DISCOVERY_PORT = 5001

nickname = ""
my_symbol = "-"
current_opponent = "-"
board_buttons = []

def discover_server_ip():
    print("A procurar servidor na rede local...")
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discovery_socket.bind(('', DISCOVERY_PORT))

    while True:
        data, addr = discovery_socket.recvfrom(1024)
        text = data.decode()
        if text.startswith("TIC_TAC_TOE_SERVER_HERE"):
            parts = text.split()
            ip = parts[1] if len(parts) >= 2 else addr[0]
            discovery_socket.close()
            print(f"Servidor encontrado no IP: {ip}")
            return ip

HOST = discover_server_ip()

# ================= SSL =================

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client = context.wrap_socket(raw, server_hostname=HOST)
client.connect((HOST, PORT))

def send(msg):
    client.send((msg + "\n").encode())

# ================= MODAIS MODERNOS =================

def criar_modal(titulo, mensagem, tipo="info", botoes=("OK",)):
    modal = tk.Toplevel(root)
    modal.title(titulo)
    modal.geometry("350x200")
    modal.configure(bg="#1e1e1e")
    modal.resizable(False, False)
    modal.grab_set()

    frame = tk.Frame(modal, bg="#1e1e1e")
    frame.pack(expand=True)

    tk.Label(frame, text=mensagem,
             font=("Segoe UI", 12),
             bg="#1e1e1e",
             fg="white").pack(pady=5)

    resposta = {"valor": None}

    def clicar(valor):
        resposta["valor"] = valor
        modal.destroy()

    btn_frame = tk.Frame(frame, bg="#1e1e1e")
    btn_frame.pack(pady=15)

    for b in botoes:
        tk.Button(btn_frame,
                  text=b,
                  width=10,
                  bg="#4CAF50" if b in ("OK", "Sim") else "#444",
                  fg="white",
                  relief="flat",
                  command=lambda v=b: clicar(v)
                  ).pack(side="left", padx=10)

    root.wait_window(modal)
    return resposta["valor"]

def modal_login():
    modal = tk.Toplevel()
    modal.title("Login")
    modal.geometry("350x200")
    modal.configure(bg="#1e1e1e")
    modal.resizable(False, False)
    modal.grab_set()

    tk.Label(modal,
             text="Digite seu nickname",
             font=("Segoe UI", 12),
             bg="#1e1e1e",
             fg="white").pack(pady=20)

    entry = tk.Entry(modal,
                     font=("Segoe UI", 12),
                     bg="#2b2b2b",
                     fg="white",
                     insertbackground="white",
                     relief="flat")
    entry.pack(pady=5)

    resultado = {"valor": None}

    def confirmar():
        resultado["valor"] = entry.get()
        modal.destroy()

    tk.Button(modal,
              text="Entrar",
              bg="#4CAF50",
              fg="white",
              relief="flat",
              command=confirmar).pack(pady=15)

    modal.wait_window()
    return resultado["valor"]

while True:
    root = tk.Tk()
    root.withdraw()  # esconde temporariamente
    nickname = modal_login()
    root.destroy()

    if not nickname:
        exit()

    send(f"REGISTER {nickname}")
    response = client.recv(1024).decode().strip()

    if response == "OK":
        break
    else:
        root = tk.Tk()
        root.withdraw()
        criar_modal("Erro", "Nickname já está em uso", "erro")
        root.destroy()

# ================= GUI PRINCIPAL =================

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

def challenge():
    selection = users_listbox.curselection()
    if selection:
        opponent = users_listbox.get(selection[0])
        if opponent != nickname:
            send(f"INVITE {opponent}")

tk.Button(side_frame,
          text="Desafiar",
          bg="#4CAF50",
          fg="white",
          relief="flat",
          command=challenge).pack(pady=10)

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
                resposta = criar_modal("Convite",
                                       f"{parts[1]} quer jogar. Aceitar?",
                                       "pergunta",
                                       botoes=("Sim", "Não"))
                if resposta == "Sim":
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
                criar_modal("Resultado", parts[0], "sucesso")

        except:
            break

threading.Thread(target=receive, daemon=True).start()

root.mainloop()