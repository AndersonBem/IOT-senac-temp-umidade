"""Portal temporario para configurar o Wi-Fi da ESP32-C3 pelo celular.

Execute sem substituir /main.py:
    python -m mpremote connect COMx run .\src\wifi_portal.py
"""

import json
import network
import socket
import time
import ubinascii
import _thread
from machine import reset, unique_id


# Troque esta senha antes de usar fora de testes. WPA2 exige no minimo 8 caracteres.
CONFIG_AP_PREFIXO = "Caminho-do-Vale"
CONFIG_AP_SENHA = "Projeto123"
ARQUIVO_REDES = "redes.json"


def resposta_http(status, tipo, corpo):
    corpo_bytes = corpo.encode("utf-8")
    cabecalhos = (
        "HTTP/1.1 %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n"
    ) % (status, tipo, len(corpo_bytes))
    return cabecalhos.encode("utf-8") + corpo_bytes


def decodificar_formulario(valor):
    """Decodifica dados enviados por um formulario HTML, inclusive acentos."""
    resultado = bytearray()
    indice = 0

    while indice < len(valor):
        if valor[indice] == "+":
            resultado.append(32)
            indice += 1
        elif valor[indice] == "%" and indice + 2 < len(valor):
            try:
                resultado.append(int(valor[indice + 1:indice + 3], 16))
                indice += 3
            except ValueError:
                resultado.extend(valor[indice].encode())
                indice += 1
        else:
            resultado.extend(valor[indice].encode())
            indice += 1

    return resultado.decode("utf-8", "replace")


def pagina(mensagem=""):
    status = ""
    if mensagem:
        status = '<div class="status">' + mensagem + "</div>"

    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Caminho do Vale | Wi-Fi</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; color: #25402f;
      font-family: Arial, Helvetica, sans-serif;
      background: #f4f7f1;
    }
    .app { display: flex; min-height: 100vh; }
    .menu {
      width: 245px; padding: 26px 18px; color: #f8fff8;
      background: linear-gradient(160deg, #176b3d, #48ac59);
    }
    .marca { display: flex; align-items: center; gap: 9px; margin: 4px 9px 34px; }
    .folha {
      display: grid; place-items: center; width: 35px; height: 35px;
      border-radius: 12px; background: #d8ed7c; color: #176b3d;
      font-size: 22px;
    }
    .marca strong { display: block; font-size: 17px; line-height: 16px; }
    .marca small { color: #d8f2d7; font-size: 11px; }
    .menu p { margin: 10px 8px; font-size: 11px; color: #d8f2d7; text-transform: uppercase; }
    .item {
      display: block; margin: 4px 0; padding: 12px 12px; border-radius: 9px;
      color: #ecffed; font-size: 14px;
    }
    .item.ativo { background: rgba(255,255,255,.19); font-weight: bold; }
    .rodape-menu { position: absolute; bottom: 26px; font-size: 11px; color: #d8f2d7; }
    .conteudo { flex: 1; padding: 28px 42px; max-width: 1020px; }
    .barra { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
    .barra h1 { margin: 0; font-size: 20px; font-weight: 600; }
    .online { color: #488557; font-size: 12px; }
    .online i {
      display: inline-block; width: 8px; height: 8px; margin-right: 5px;
      border-radius: 50%; background: #6cc65b;
    }
    .hero {
      padding: 27px 30px; border-radius: 14px; color: white;
      background: linear-gradient(110deg, #2d874c, #1f6240);
      box-shadow: 0 8px 22px rgba(27, 96, 53, .18);
    }
    .hero h2 { margin: 0 0 8px; font-size: 25px; }
    .hero h2 span { color: #e0e878; }
    .hero p { margin: 0; color: #e5f3e5; font-size: 14px; }
    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 18px 0; }
    .card {
      min-height: 92px; padding: 16px; border: 1px solid #e0e8de;
      border-radius: 12px; background: white; box-shadow: 0 3px 11px rgba(32, 65, 41, .05);
    }
    .card b { display: block; margin-bottom: 6px; color: #63906d; font-size: 11px; font-weight: normal; }
    .card strong { font-size: 20px; }
    .painel {
      padding: 25px; border: 1px solid #e0e8de; border-radius: 14px;
      background: white; box-shadow: 0 3px 11px rgba(32, 65, 41, .05);
    }
    .painel h3 { margin: 0 0 6px; font-size: 18px; }
    .painel .descricao { margin: 0 0 22px; color: #718173; font-size: 13px; }
    label { display: block; margin: 14px 0 6px; color: #49624e; font-size: 13px; font-weight: bold; }
    input {
      width: 100%; padding: 13px 14px; outline: none; border: 1px solid #cddbcf;
      border-radius: 8px; background: #fbfdfb; color: #25402f; font-size: 15px;
    }
    input:focus { border-color: #47a75a; box-shadow: 0 0 0 3px rgba(71,167,90,.13); }
    button {
      width: 100%; margin-top: 22px; padding: 14px; border: 0; border-radius: 8px;
      background: #2c914a; color: white; font-size: 15px; font-weight: bold;
    }
    .status { margin: 0 0 18px; padding: 12px; border-radius: 8px; background: #edf8df; color: #426d2e; font-size: 13px; }
    .aviso { margin: 17px 0 0; color: #809083; font-size: 11px; text-align: center; }
    @media (max-width: 700px) {
      .menu { display: none; }
      .conteudo { padding: 20px 16px; }
      .hero { padding: 22px 20px; }
      .hero h2 { font-size: 21px; }
      .cards { grid-template-columns: 1fr 1fr; }
      .barra { margin-bottom: 18px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="menu">
      <div class="marca"><div class="folha">❋</div><div><strong>Caminho<br>do Vale</strong><small>Monitoramento inteligente</small></div></div>
      <p>Configuração</p>
      <div class="item">◈ Visão geral</div>
      <div class="item">⌁ Monitoramento</div>
      <div class="item">◉ Cargas e lotes</div>
      <div class="item ativo">⚙ Configurações</div>
      <div class="rodape-menu">ESP32-C3 · Portal local</div>
    </aside>
    <main class="conteudo">
      <div class="barra"><h1>Configurações</h1><span class="online"><i></i>Portal ativo</span></div>
      <section class="hero">
        <h2>Conecte ao <span>Caminho do Vale</span></h2>
        <p>Cadastre a rede que levará os dados da sua operação até a plataforma.</p>
      </section>
      <section class="cards">
        <div class="card"><b>DISPOSITIVO</b><strong>ESP32-C3</strong></div>
        <div class="card"><b>REDE NECESSÁRIA</b><strong>2,4 GHz</strong></div>
        <div class="card"><b>STATUS</b><strong>Configurar</strong></div>
      </section>
      <section class="painel">
        <h3>Rede Wi-Fi</h3>
        <p class="descricao">Informe os dados da rede local para conectar o dispositivo.</p>
        """ + status + """
        <form method="post" action="/wifi">
          <label>Nome da rede (SSID)</label>
          <input name="ssid" placeholder="Ex.: Minha Rede 2G" required>
          <label>Senha da rede</label>
          <input name="senha" type="password" placeholder="Digite a senha" required>
          <button type="submit">Salvar e conectar</button>
        </form>
        <p class="aviso">As credenciais são armazenadas somente na memória da placa.</p>
      </section>
    </main>
  </div>
</body>
</html>"""


def salvar_rede(ssid, senha):
    """Guarda a rede na flash da placa para a integracao futura com main.py."""
    with open(ARQUIVO_REDES, "w") as arquivo:
        json.dump([[ssid, senha]], arquivo)


def servidor_dns(ip):
    """Responde qualquer nome DNS com o IP da ESP32 para ativar o captive portal."""
    endereco = socket.getaddrinfo("0.0.0.0", 53)[0][-1]
    dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns.bind(endereco)
    ip_bytes = bytes([int(parte) for parte in ip.split(".")])

    while True:
        pedido, cliente = dns.recvfrom(512)

        try:
            posicao = 12
            while posicao < len(pedido) and pedido[posicao] != 0:
                posicao += pedido[posicao] + 1

            # Pergunta DNS: nome, terminador zero, tipo e classe.
            fim_pergunta = posicao + 5
            if len(pedido) < fim_pergunta:
                continue

            resposta = (
                pedido[:2] + b"\x81\x80" + pedido[4:6] +
                b"\x00\x01\x00\x00\x00\x00" +
                pedido[12:fim_pergunta] +
                b"\xc0\x0c\x00\x01\x00\x01" +
                b"\x00\x00\x00\x3c\x00\x04" + ip_bytes
            )
            dns.sendto(resposta, cliente)
        except Exception as erro:
            print("[Portal] Erro DNS:", erro)


def iniciar_portal():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    sufixo = ubinascii.hexlify(unique_id()).decode()[-4:]
    nome_ap = CONFIG_AP_PREFIXO + sufixo
    ap.config(
        essid=nome_ap,
        password=CONFIG_AP_SENHA,
        authmode=network.AUTH_WPA_WPA2_PSK,
    )

    ip = ap.ifconfig()[0]
    print("\n[Portal] Rede criada:", nome_ap)
    print("[Portal] Senha:", CONFIG_AP_SENHA)
    print("[Portal] Abra no celular: http://%s/\n" % ip)

    # O DNS local faz qualquer endereco HTTP apontar para esta pagina.
    _thread.start_new_thread(servidor_dns, (ip,))

    endereco = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    servidor = socket.socket()
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(endereco)
    servidor.listen(1)

    while True:
        cliente, _ = servidor.accept()

        try:
            requisicao = cliente.recv(2048)
            primeira_linha = requisicao.split(b"\r\n", 1)[0].split()
            metodo, caminho = primeira_linha[0], primeira_linha[1]

            # Sistemas Android/iOS fazem requisicoes HTTP para detectar portais.
            # Responder a qualquer GET com a pagina induz a abertura automatica.
            if metodo == b"GET":
                resposta = resposta_http(
                    "200 OK", "text/html; charset=utf-8", pagina()
                )

            elif metodo == b"POST" and caminho == b"/wifi":
                corpo = requisicao.split(b"\r\n\r\n", 1)[1].decode("utf-8")
                campos = {}
                for item in corpo.split("&"):
                    chave, valor = item.split("=", 1)
                    campos[chave] = decodificar_formulario(valor)

                ssid = campos.get("ssid", "").strip()
                senha = campos.get("senha", "")
                if not ssid or not senha:
                    resposta = resposta_http(
                        "400 Bad Request", "text/html; charset=utf-8",
                        pagina("Preencha todos os campos."),
                    )
                else:
                    salvar_rede(ssid, senha)
                    cliente.sendall(resposta_http(
                        "200 OK", "text/html; charset=utf-8",
                        pagina("Rede salva. A placa sera reiniciada."),
                    ))
                    time.sleep(2)
                    reset()

            else:
                resposta = resposta_http(
                    "405 Method Not Allowed", "text/plain; charset=utf-8",
                    "Metodo nao permitido"
                )

            cliente.sendall(resposta)

        except Exception as erro:
            print("[Portal] Erro:", erro)

        finally:
            cliente.close()


if __name__ == "__main__":
    iniciar_portal()
