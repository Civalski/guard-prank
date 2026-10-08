# -*- coding: utf-8 -*-
"""
Guardião de Tela — bloqueio anti-bisbilhoteiro.

Como usar:
  1) pip install -r requirements.txt
  2) python guardiao.py   (de preferência como Administrador -> use iniciar.bat)

Atalho: Ctrl+Shift+T
  - PARADO  -> ARMA (a tela continua igual; nada aparece)
  - ARMADO  -> cancela (volta a PARADO)
  - TRAVADO -> abre o campo de senha para desbloquear

Enquanto ARMADO, qualquer toque no mouse/touchpad ou tecla (que não seja
Ctrl/Shift/T) tira uma foto pela webcam, salva em ./capturas e trava o PC.

Saída de emergência (sempre funciona): Ctrl+Alt+Del -> Gerenciador de Tarefas
-> encerrar o processo "python". O Windows nunca deixa bloquear essa combinação,
então é impossível ficar trancado para sempre.
"""

import os
import time
import random
import threading
import datetime
import ctypes
from ctypes import wintypes

import tkinter as tk

try:
    import keyboard
    import mouse
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "Faltam dependências. Rode:  python -m pip install -r requirements.txt\n"
        f"Detalhe: {e}"
    )

try:
    from PIL import Image, ImageTk
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "Falta a biblioteca Pillow. Rode:  python -m pip install -r requirements.txt\n"
        f"Detalhe: {e}"
    )

try:
    import cv2
except Exception:
    cv2 = None  # sem webcam/opencv: trava mesmo assim, só não mostra a foto


# --------------------------- Configuração ---------------------------------

# A "senha" para voltar é a própria senha da conta do Windows (tela de login).
HOTKEY = "ctrl+shift+t"
# Por quantos segundos a foto + mensagem ficam na tela antes de jogar para a
# tela de bloqueio do Windows (a partir daí só a senha do Windows abre).
SEGUNDOS_FLAGRANTE = 15
# Uma frase é sorteada a cada flagrante. Pode adicionar/editar à vontade.
FRASES = [
    "isso daria uma bela foto de perfil do Instagram, quem sabe até um banner, "
    "de repente um outdoor, já pensou em ser modelo?",
    "Sorria! Você acabou de entrar para o meu álbum de xeretas.",
    "Flagrante registrado. O Departamento de Fofoca já foi avisado.",
    "Essa pose ficou ótima para a capa de 'Pego no Flagra, Vol. 1'.",
    "Que curiosidade linda... digna de um documentário sobre intrometidos.",
    "Peraí que eu já estou revelando essa foto para a família toda ver.",
    "Mexeu no que não devia. Agora é só sorrir para a posteridade.",
]
# Fotos ficam FORA do OneDrive (não sincronizam): pasta local no perfil.
PASTA_FOTOS = os.path.join(os.path.expanduser("~"), "GuardiaoDeTela", "capturas")
GRACA_SEGUNDOS = 2.0  # tempo após armar antes de começar a vigiar

PARADO, ARMADO, TRAVADO = "PARADO", "ARMADO", "TRAVADO"

# Constantes do hook de mouse de baixo nível (ctypes)
WH_MOUSE_LL = 14
HC_ACTION = 0
LowLevelMouseProc = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


class Guardiao:
    def __init__(self):
        os.makedirs(PASTA_FOTOS, exist_ok=True)

        self.estado = PARADO
        self.vigiar_ativo = False

        self._h_press = None     # handler de detecção de teclado (ARMADO)
        self._h_mouse = None     # handler de detecção de mouse (ARMADO)
        self._supp = None        # hook de supressão de teclado (TRAVADO)
        self.pressed = set()     # teclas pressionadas (p/ detectar o atalho)

        self.lock_win = None
        self._imgtk = None
        self._timer_bloqueio = None

        # --- API do Windows para bloquear o mouse (ctypes) ---
        self.user32 = ctypes.windll.user32
        self.user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, LowLevelMouseProc, wintypes.HINSTANCE, wintypes.DWORD
        ]
        self.user32.CallNextHookEx.restype = wintypes.LPARAM
        self.user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        ]
        self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user32.OpenInputDesktop.restype = wintypes.HANDLE
        self.user32.OpenInputDesktop.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
        ]
        self.user32.CloseDesktop.argtypes = [wintypes.HANDLE]
        self._mouse_hook_id = None
        self._mouse_proc_ref = None
        self._mouse_blocking = False

        # Janela raiz escondida (o loop do tkinter roda na thread principal)
        self.root = tk.Tk()
        self.root.withdraw()

    # ------------------------------ Ciclo de vida -------------------------

    def iniciar(self):
        keyboard.add_hotkey(HOTKEY, self.ao_atalho)
        print("Guardião pronto. Pressione Ctrl+Shift+T para ARMAR.")
        print(f"Fotos serão salvas em: {PASTA_FOTOS}")
        print("Emergência: Ctrl+Alt+Del -> Gerenciador de Tarefas -> encerrar python.")
        self.root.mainloop()

    def ao_atalho(self):
        # Chamado pela thread do 'keyboard'. Marca a ação na thread do tkinter.
        if self.estado == PARADO:
            self.root.after(0, self.armar)
        elif self.estado == ARMADO:
            self.root.after(0, self.desarmar)
        # No estado TRAVADO o atalho não faz nada: a saída é a tela de
        # bloqueio do Windows (só a senha da conta abre).

    # ------------------------------ ARMADO --------------------------------

    def armar(self):
        if self.estado != PARADO:
            return
        self.estado = ARMADO
        self.vigiar_ativo = False
        self.pressed.clear()
        self._h_press = keyboard.on_press(self.detectou_tecla)
        self._h_mouse = mouse.hook(self.detectou_mouse)
        threading.Thread(target=self._graca, daemon=True).start()
        print("ARMADO. Qualquer toque no mouse/teclado vai travar o PC.")
        print("(Ctrl+Shift+T de novo cancela enquanto ninguém mexeu.)")

    def _graca(self):
        time.sleep(GRACA_SEGUNDOS)
        if self.estado == ARMADO:
            self.vigiar_ativo = True

    def desarmar(self):
        if self.estado != ARMADO:
            return
        self.estado = PARADO
        self.vigiar_ativo = False
        self._parar_deteccao()
        print("Cancelado. Guardião em espera (PARADO).")

    def _parar_deteccao(self):
        if self._h_press is not None:
            try:
                keyboard.unhook(self._h_press)
            except Exception:
                pass
            self._h_press = None
        if self._h_mouse is not None:
            try:
                mouse.unhook(self._h_mouse)
            except Exception:
                pass
            self._h_mouse = None

    def detectou_tecla(self, e):
        if not self.vigiar_ativo or self.estado != ARMADO:
            return
        if e.event_type != keyboard.KEY_DOWN:
            return
        n = (e.name or "")
        # Ignora as teclas do próprio atalho de cancelamento.
        if "ctrl" in n or "shift" in n or n == "t":
            return
        self.root.after(0, self.travar)

    def detectou_mouse(self, e):
        if self.vigiar_ativo and self.estado == ARMADO:
            self.root.after(0, self.travar)

    # ------------------------------ TRAVADO -------------------------------

    def travar(self):
        if self.estado == TRAVADO:
            return
        self.estado = TRAVADO
        self.vigiar_ativo = False
        self._parar_deteccao()
        try:
            keyboard.unhook_all()  # remove o hotkey e qualquer detecção
        except Exception:
            pass
        try:
            mouse.unhook_all()
        except Exception:
            pass

        print("TRAVADO! Capturando foto...")
        foto = self.capturar_foto()
        if foto:
            print(f"Foto salva em: {foto}")

        # Bloqueia teclado (lib keyboard) e mouse (hook ctypes)
        self.pressed.clear()
        self._supp = keyboard.hook(self.bloquear_teclado, suppress=True)
        self._instalar_bloqueio_mouse()

        self.construir_janela(foto)
        # Depois do "flagrante", joga para a tela de bloqueio do Windows:
        # a partir daí só a senha da conta abre o PC (não dá pra burlar).
        self._timer_bloqueio = self.root.after(
            int(SEGUNDOS_FLAGRANTE * 1000), self.sair_protecao
        )
        # Rede de segurança: se suspender/bloquear antes, solta tudo na hora.
        threading.Thread(target=self._monitor_saida, daemon=True).start()

    def capturar_foto(self):
        if cv2 is None:
            return None
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            ok, frame = False, None
            for _ in range(6):  # descarta quadros iniciais (exposição)
                ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return None
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            caminho = os.path.join(PASTA_FOTOS, ts + ".jpg")
            # imencode evita problemas com acentos no caminho
            ok2, buf = cv2.imencode(".jpg", frame)
            if ok2:
                buf.tofile(caminho)
                return caminho
            return None
        except Exception as ex:
            print(f"(Não consegui usar a webcam: {ex})")
            return None

    def bloquear_teclado(self, e):
        # Recebe TODO evento de teclado e o suprime do sistema (return False).
        return False

    # ------------------------- Bloqueio de mouse (ctypes) -----------------

    def _instalar_bloqueio_mouse(self):
        def proc(nCode, wParam, lParam):
            if nCode == HC_ACTION and self._mouse_blocking:
                return 1  # engole o evento de mouse
            return self.user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._mouse_proc_ref = LowLevelMouseProc(proc)
        self._mouse_hook_id = self.user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._mouse_proc_ref, None, 0
        )
        self._mouse_blocking = True

    def _remover_bloqueio_mouse(self):
        self._mouse_blocking = False
        if self._mouse_hook_id:
            try:
                self.user32.UnhookWindowsHookEx(self._mouse_hook_id)
            except Exception:
                pass
            self._mouse_hook_id = None
        self._mouse_proc_ref = None

    # ------------------------------ Janela --------------------------------

    def construir_janela(self, foto_path):
        FUNDO = "#0d0d0d"
        VERMELHO = "#ff3b3b"

        win = tk.Toplevel(self.root)
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.configure(bg=FUNDO)
        win.config(cursor="none")
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        # Cabeçalho
        tk.Label(
            win, text="F L A G R A N T E !", fg=VERMELHO, bg=FUNDO,
            font=("Segoe UI Black", 44, "bold"),
        ).pack(pady=(30, 4))
        tk.Label(
            win, text="— alguém mexeu no computador —", fg="#bbbbbb", bg=FUNDO,
            font=("Segoe UI", 14, "italic"),
        ).pack(pady=(0, 16))

        # Foto em moldura estilo "polaroid"
        if foto_path:
            try:
                img = Image.open(foto_path)
                maxw, maxh = int(sw * 0.45), int(sh * 0.45)
                w, h = img.size
                escala = min(maxw / w, maxh / h)
                img = img.resize((max(1, int(w * escala)), max(1, int(h * escala))))
                self._imgtk = ImageTk.PhotoImage(img)
                moldura = tk.Frame(
                    win, bg="white", highlightbackground=VERMELHO,
                    highlightthickness=5,
                )
                moldura.pack(pady=6)
                tk.Label(moldura, image=self._imgtk, bg="white").pack(
                    padx=14, pady=(14, 6)
                )
                quando = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
                tk.Label(
                    moldura, text=f"Pego no flagra  •  {quando}",
                    fg="#222222", bg="white", font=("Segoe UI", 13, "italic"),
                ).pack(pady=(0, 12))
            except Exception:
                pass

        # Frase sorteada
        tk.Label(
            win, text=random.choice(FRASES), fg="white", bg=FUNDO,
            font=("Segoe UI", 22, "bold"),
            wraplength=int(sw * 0.75), justify="center",
        ).pack(pady=(18, 8))

        # Contagem regressiva até a tela de bloqueio do Windows
        self.lbl_contagem = tk.Label(
            win, text="", fg="#ff9a3b", bg=FUNDO, font=("Segoe UI", 15, "bold"),
        )
        self.lbl_contagem.pack(pady=6)

        self.lock_win = win
        self._restante = int(SEGUNDOS_FLAGRANTE)
        self._tique_contagem()

    def _tique_contagem(self):
        if self.estado != TRAVADO or self.lock_win is None:
            return
        try:
            if self._restante <= 0:
                self.lbl_contagem.config(text="Bloqueando a tela...")
            else:
                self.lbl_contagem.config(
                    text=f"Bloqueando a tela em {self._restante}s"
                )
                self._restante -= 1
                self.root.after(1000, self._tique_contagem)
        except Exception:
            pass

    # ------------------------- Monitor de saída ---------------------------

    def _esta_bloqueado(self):
        # True quando a estação está bloqueada (tampa fechada / Win+L /
        # Ctrl+Alt+Del): o desktop de entrada vira o seguro do Windows e um
        # processo comum não consegue abri-lo.
        try:
            h = self.user32.OpenInputDesktop(0, False, 0x0100)  # SWITCHDESKTOP
            if not h:
                return True
            self.user32.CloseDesktop(h)
            return False
        except Exception:
            return False

    def _monitor_saida(self):
        # Sai da proteção quando o PC suspender (salto no relógio) ou bloquear.
        ultimo = time.time()
        while self.estado == TRAVADO:
            time.sleep(0.5)
            agora = time.time()
            suspendeu = (agora - ultimo) > 4  # dormiu/suspendeu entre os ticks
            ultimo = agora
            if suspendeu or self._esta_bloqueado():
                self.root.after(0, self.sair_protecao)
                return

    # ------------------------------ Sair ----------------------------------

    def sair_protecao(self):
        if self.estado != TRAVADO:
            return
        self.estado = PARADO
        self.vigiar_ativo = False

        if self._timer_bloqueio is not None:
            try:
                self.root.after_cancel(self._timer_bloqueio)
            except Exception:
                pass
            self._timer_bloqueio = None

        if self._supp is not None:
            try:
                keyboard.unhook(self._supp)
            except Exception:
                pass
            self._supp = None
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            mouse.unhook_all()
        except Exception:
            pass
        self._remover_bloqueio_mouse()

        if self.lock_win is not None:
            try:
                self.lock_win.destroy()
            except Exception:
                pass
            self.lock_win = None

        self.pressed.clear()
        keyboard.add_hotkey(HOTKEY, self.ao_atalho)
        # Garante que o Windows peça a senha da conta ao voltar.
        try:
            self.user32.LockWorkStation()
        except Exception:
            pass
        print("Saiu da proteção. O Windows vai pedir a senha. (PARADO)")


def _instancia_unica():
    """Evita rodar dois Guardiões ao mesmo tempo (ex.: auto-início + clique)."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Guardiao_de_Tela_Mutex")
    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    return True  # mantém o mutex vivo enquanto o processo existir


if __name__ == "__main__":
    if not _instancia_unica():
        raise SystemExit("O Guardião já está rodando.")
    Guardiao().iniciar()
