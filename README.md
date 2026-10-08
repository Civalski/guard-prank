# 🔒 Guard Prank — Guardião de Tela

Uma "pegadinha de segurança" para Windows. Você deixa o notebook aberto, arma com
um atalho, e **a tela continua exatamente como estava**. Se alguém encostar no
mouse/touchpad ou no teclado, o programa:

1. tira uma **foto pela webcam** de quem mexeu;
2. mostra a foto em **tela cheia** com uma frase de deboche (o "flagrante");
3. e, em seguida, joga para a **tela de bloqueio do Windows** — a partir daí
   **só a senha da sua conta** destrava o PC.

É um dissuasor pessoal e divertido para quando você sai da frente do computador.

![status](https://img.shields.io/badge/plataforma-Windows-blue) ![python](https://img.shields.io/badge/python-3.8%2B-green)

---

## ✅ Requisitos

- **Windows** 10/11
- **Python 3.8+** ([python.org](https://www.python.org/downloads/))
- Uma **webcam**
- Sua conta do Windows precisa ter **senha ou PIN** (é o que destrava depois)

## 📦 Instalação

```bash
pip install -r requirements.txt
```

Dependências: `keyboard`, `mouse`, `opencv-python`, `pillow`.

## ▶️ Como rodar

- **Com janela** (útil para ver mensagens/erros): dê dois cliques em
  **`iniciar.bat`** (ele pede permissão de Administrador, o que deixa o bloqueio
  mais firme) — ou rode `python guardiao.py`.
- **Em segundo plano** (sem terminal): dê dois cliques em **`iniciar_oculto.vbs`**.

### Iniciar junto com o Windows (opcional)

1. Aperte `Win + R`, digite `shell:startup` e Enter.
2. Copie um atalho do `iniciar_oculto.vbs` para dentro dessa pasta.

Pronto: ele sobe sozinho toda vez que o Windows liga.

## 🎮 Como usar

1. Quando for sair, pressione **`Ctrl + Shift + T`** → **armado**. A tela
   continua igual, nada aparece. Espere ~2 segundos antes de tirar a mão.
2. Se alguém mexer → foto + frase em tela cheia e PC bloqueado.
3. Mudou de ideia antes de alguém mexer? Aperte **`Ctrl + Shift + T`** de novo
   para cancelar.

## 🧠 Como funciona o bloqueio (e por que é seguro)

Quando alguém mexe, o teclado e o mouse são bloqueados e a foto aparece por
alguns segundos (o "flagrante"). Depois, o programa chama a **tela de bloqueio
nativa do Windows**.

A partir daí, **só a senha/PIN da conta** abre o PC: `Ctrl + Alt + Del` na tela
de login não abre nada e não é possível chegar no Gerenciador de Tarefas sem
entrar. Usar a tela nativa do Windows é o que torna a saída à prova de burla —
nenhum programa comum consegue fazer melhor que isso.

> ⚠️ **Só protege se a conta tiver senha ou PIN.** Se o Windows entra sozinho,
> qualquer um passa pela tela de login. Verifique em
> *Configurações → Contas → Opções de entrada*.

**Sem risco de travar para sempre:** o `Ctrl + Alt + Del` sempre funciona (o
Windows nunca deixa um programa bloqueá-lo) e, ao detectá-lo, o Guardião entrega
na hora para a tela de bloqueio. Fechar a tampa / suspender também sai da
proteção.

## 🖼️ Onde ficam as fotos

Em **`%USERPROFILE%\GuardiaoDeTela\capturas`** (fora do OneDrive, não
sincroniza), com nome por data e hora, ex.: `2026-10-08_14-30-05.jpg`.

## ⚙️ Personalização

No topo do `guardiao.py`:

- **`FRASES`** — a lista de frases sorteadas no flagrante (edite/adicione as suas).
- **`HOTKEY`** — o atalho (padrão `ctrl+shift+t`).
- **`SEGUNDOS_FLAGRANTE`** — por quantos segundos a foto fica na tela antes do
  bloqueio do Windows (padrão `15`).
- **`GRACA_SEGUNDOS`** — folga após armar antes de começar a vigiar (padrão `2`).

Depois de editar, reinicie o programa.

## 🛑 Gerenciar / desligar

- **Parar agora:** `Ctrl + Alt + Del` → Gerenciador de Tarefas → encerrar
  `pythonw.exe` (ou `python.exe`).
- **Tirar da inicialização automática:** `Win + R` → `shell:startup` → apague o
  atalho do Guardião.

## 📄 Aviso

Projeto pessoal, para uso **no seu próprio computador**. É um dissuasor para
brincadeira/proteção leve, **não** uma solução de segurança corporativa. Use com
bom senso.
