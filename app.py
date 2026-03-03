# <<< app.py (SEM GERAÇÃO DE RELATÓRIO) >>>

import os
import time
import qrcode
import uuid
import threading
import csv
import json
import ipaddress
import shutil
import smtplib
import pandas as pd
import sys
import traceback # <--- ADICIONADO: Importado para usar em tratamento de erro
from datetime import datetime, date, timedelta, time as time_obj
from pytz import timezone
from flask import (
    Flask, request, send_from_directory, send_file, abort,
    jsonify, render_template, redirect, url_for, session
)
from flask_compress import Compress
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
# import pyheif # REMOVIDO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- REMOVIDO: Bloco de importação do banco_de_horas ---

# --- 1. CONFIGURAÇÃO DE CAMINHOS LOCAIS ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS_APP = os.path.join(APP_ROOT, 'dados_app')
PASTA_ANEXOS_LOCAL = os.path.join(PASTA_DADOS_APP, 'anexos')
PASTA_LOG_DISPOSITIVOS_LOCAL = os.path.join(PASTA_DADOS_APP, 'logs_dispositivos')
PASTA_BACKUPS_DIARIOS_LOCAL = os.path.join(APP_ROOT, 'backups_diarios')
PASTA_RELATORIOS_GERADOS_LOCAL = os.path.join(APP_ROOT, 'relatorios_gerados') # Pasta mantida caso seja usada para outra coisa
PASTA_STATIC = os.path.join(APP_ROOT, 'static')
PASTA_TEMPLATES = os.path.join(APP_ROOT, 'templates')

# Arquivos de dados principais
CSV_FILENAME_LOCAL = os.path.join(PASTA_DADOS_APP, "registro_scan.csv")
CSV_LIVE_LOCAL = os.path.join(PASTA_DADOS_APP, "registro_scan_live.csv")
LOGO_LOCAL_PATH = os.path.join(PASTA_STATIC, "unica_logo.png")
HTML_FILENAME = os.path.join(PASTA_DADOS_APP, "registro_ponto_tjrs.html")

# Cria todas as pastas necessárias
for pasta in [PASTA_DADOS_APP, PASTA_ANEXOS_LOCAL, PASTA_LOG_DISPOSITIVOS_LOCAL,
              PASTA_BACKUPS_DIARIOS_LOCAL, PASTA_RELATORIOS_GERADOS_LOCAL, PASTA_STATIC, PASTA_TEMPLATES]:
    os.makedirs(pasta, exist_ok=True)

# --- 2. CONSTANTES GLOBAIS ---
EXPIRACAO_MINUTOS_QR = 2
TZ_SAO_PAULO = timezone("America/Sao_Paulo")
GESTOR_PASSWORD = "GESTOR-TJRS-0911"
REDES_PERMITIDAS = [
    ipaddress.ip_network("10.209.0.0/16"),  # Cobre tudo de 10.209.0.0 até 10.209.255.255
    ipaddress.ip_network("177.66.6.0/24"), # Cobre tudo de 177.66.6.0 até 177.66.6.255
]
# Configurações de E-mail
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_ADDRESS = 'gestaodepontotjrs@gmail.com'
EMAIL_PASSWORD = 'qvly lipi bnis fwte'
EMAIL_RECIPIENT = 'gestaodepontotjrs@gmail.com'

# Mapa de IDs (fornecido por você)
ID_NOME_MAP = {
    "52523": "Hederson Rangel dos Santos Gomes",
    "50678": "Vinicius Dal Mas Ligabue",
    "52196": "Bernardo Ceresa Rolla",
    "52146": "Bruna Pereira Souza Cardoso",
    "52386": "Eduardo Muller Cerveira",
    "52234": "Giovana Rodrigues Fonseca",
    "52473": "Gustavo Zwirts Soares",
    "52561": "Matheus Santana Alves",
    "52414": "Otávio Stumm François",
    "49742": "Paola Silva dos Santos",
    "52550": "Renata Câmara dos Reis",
    "52157": "Thayná Rodenbusch de Morais",
    "52373": "Wanderson de Souza Alves",
    "52528": "Ana Paula Steinmetz",
    "50396": "Barbara Barcellos",
    "40513": "Francielly dos Santos Antunes",
    "52618": "Gabriele Santos de Souza",
    "52390": "João Pedro Spindola Dornelles",
    "52442": "Joao Vitor Sott",
    "52490": "Maria Eduarda de Andrade Lima",
    "52093": "Maria Eduarda Travi",
    "52259": "Mauricio do Amaral Goncalves",
    "50399": "Teresa Julia dos Santos Peranconi",
    "52278": "Sophia Caieron de Avelar",
    "34322": "Vanessa da Rosa Siqueira",
    "52309": "Giulia Petro Cruz",
    "41096": "Isabella da Silva Marques",
    "52853": "Graziela Strehlow Osielski Barbosa",
    "40590": "Julia Delfino dos Santos",
    "52942": "Vitória da Silva Neves da Fontoura",
    "49760": "Pedro Henrique Correa Finklei",
    "49767": "Giovana Salatino da Silva",
    "50411": "Maísa Vitória Mello",
    "49812": "Mauren Pereira",
    "52249": "Ana Sofia Güths",
    "52139": "Ariany Cristiny Almeida Dias",
    "52126": "Arthur André Storchi Michelon",
    "52270": "Bernardo Chagas da Silva",
    "52083": "Bernardo Tissiani Von Helden",
    "52151": "Brenda Corrêa Silveira",
    "49380": "Brenda da Silva Ribeiro",
    "46510": "Clara de Freitas Dias Pereira",
    "52085": "Franciely Santos Albuquerque",
    "52281": "Gabriela Trovão Alegre",
    "52175": "Jonas Quemuel Rosa da Silva",
    "52079": "Juliana dos Santos Oliveira",
    "52280": "Matheus Cristiano da Cruz Paim",
    "52432": "Quezia Rute Tumba Chilombo",
    "52113": "Tiago Pereira Nascimento",
    "52419": "William Diogo Lopez Carvalho",
    "52226": "Erika Rosalen Bonatto",
    "52248": "Laura Augusto Álvares da Silva",
    "52201": "Henrique Farias Paiva da Conceição",
    "52283": "Fabricio Almeida da Silva",
    "52368": "Daniely Victoria da Silva",
    "52132": "Eduarda Casarin Gomes",
    "42406": "Helenilde Pereira da Silva",
    "22003": "Não sei ainda/Teste",
    "12079": "Sabrina de Cassia Dutra dos Santos",
    "52090": "Fabricio Lewis da Motta",
    "52534": "Lorenzo Lovatto Gonzaga",
    "52412": "Giulia Trindade Viegas",
    "52389": "Nicole da Silva Iloi",
    "53073": "Catarina Hermeling de Almeida",
    "53124": "João Vitor Vianna Duarte",
    "53081": "Otavio Augusto Moreira da Silva",
    "53094": "Rebeca Hannich",
    "53095": "William Marcondes Couto Ferreira",
    "53054": "Yanomi Souza de Melo",
    "53108": "Mirela Fróis de Abreu",
    "53183": "Maria Clara dos Passos Oliveira",
    "52540": "Anthony Alves Avila",
    "52127": "Yasmim Kolodziejska D Avila",
    "52218": "Carolina Haas",
    "52911": "Laura Caroline Mota Moreira",
    "38637": "Gabryelen Azeredo de Oliveira",
    "52548": "Lucas Carvalho Euclydes",
    "48038": "Rafaela Roth Thiago",
    "50887": "Sara Rafaela Koepsel Alves",
    "49368": "Guilherme Machado dos Santos",
    "46535": "Nina Virginia Ribeiro Lehmann",
    "50821": "Andrielly da Rosa Fagundes",
    "50444": "Ilidiane Pires Lumertz",
    "48058": "Kaillany Sanguinte de Freitas Fialho",
    "52529": "Marya Eduarda Guerra Mancio",
    "52069": "Pedro Franco Freitas Pereira",
    "52141": "Thomaz Ghisolfi Keller",
    "52164": "Camila Barboza Kuhn",
    "52940": "Victor Anzolin Davila",
    "52881": "Bruno Fraga Merlo",
    "41512": "Eduardo Dambrosi Skripski",
    "52593": "Rhayane da Luz Lopes",
    "52598": "Manuella Moreira",
    "49236": "Volmer Martins Pinto",
    "52882": "Luci Vitória",
    "53329": "Helena Nascimento Biansini",
    "53313": "Marcella Kurylo Barni",
    "53310": "Steffani de Souza Gonçalves",
    "49683": "Rafael da Silva Irion",
    "53342": "Amanda Hertzog Hainzenreder",
    "53377": "Karen Livia Costa Pereira",
    "45521": "Henrique Barreto Viana Vieira",
    "53408": "Leandro Azevedo",
    "53385": "Hamilton Gonzaga Filho",
    "36506": "Eduarda Martini Fischmann",
    "28828": "Gabriela Fabra Dornelles",
    "53391": "Gisele Horn",
    "52316": "Luciana Cusinato dos Santos",
    "47502": "Laura Benedusi dos Santos",
    "45448": "Viviane Rosa de Souza",
    "18018": "Bruna Campos de Araújo Tonello",
    "30726": "Douglas Bueno Esposito",
    "53406": "Luís Roberto da Silva Felipe",
    "":""
}

# --- MUDANÇA 1: Adicionada a coluna "ID Estagiário" ---
CSV_HEADER = ["UUID", "IP", "DeviceID", "ID Estagiário", "Nome", "Sala", "Justificativa", "Arquivo", "DataHora Entrada", "DataHora Saída"]

if not os.path.exists(CSV_FILENAME_LOCAL):
    with open(CSV_FILENAME_LOCAL, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
if not os.path.exists(CSV_LIVE_LOCAL): # Garante que o live também exista
    with open(CSV_LIVE_LOCAL, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)


# --- 3. ESTADO GLOBAL ---
ip_cache = {}
ultimo_qr_code = None
ultimo_qr_code_timestamp = None
executor = ThreadPoolExecutor(max_workers=3)
csv_lock = threading.Lock()
dispositivos_registrados_hoje = {}
data_log_dispositivos_em_memoria = None # <--- (CORREÇÃO BUG 'DIA SEGUINTE') [ALTERAÇÃO 1/4]

# --- 5. FUNÇÕES DE E-MAIL E LOG ---

def enviar_email_com_anexo():
    if not EMAIL_ADDRESS or 'seu_email' in EMAIL_ADDRESS:
        print("⚠️ AVISO: E-mail de envio não configurado. Pulando envio de backup por e-mail.")
        return

    try:
        data_hoje = datetime.now(TZ_SAO_PAULO).strftime('%d/%m/%Y')
        subject = f"REGISTROS DO DIA {data_hoje} - SALA 2205"

        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject

        body = "Em anexo, segue o arquivo CSV com todos os registros de ponto do dia até o momento."
        msg.attach(MIMEText(body, 'plain'))

        with open(CSV_FILENAME_LOCAL, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f"attachment; filename= {os.path.basename(CSV_FILENAME_LOCAL)}",
        )
        msg.attach(part)

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, EMAIL_RECIPIENT, text)
        server.quit()
        print(f"📧 E-mail de backup enviado com sucesso para {EMAIL_RECIPIENT}.")
    except Exception as e:
        print(f"❌ ERRO AO ENVIAR E-MAIL DE BACKUP: {e}")


def get_device_log_filename():
    # Usar o fuso de SP para garantir que o nome do arquivo mude à meia-noite (SP)
    data_hoje = datetime.now(TZ_SAO_PAULO).strftime('%Y-%m-%d')
    return os.path.join(PASTA_LOG_DISPOSITIVOS_LOCAL, f"devices_{data_hoje}.json")

def carregar_dispositivos_registrados():
    log_file = get_device_log_filename()
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            print(f"-> Log de dispositivos de hoje ({log_file}) carregado.")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"-> Nenhum log de dispositivos de hoje ({log_file}) encontrado. Começando do zero.")
        return {}

def salvar_dispositivo_registrado(device_id, nome):
    global dispositivos_registrados_hoje
    log_file = get_device_log_filename()
    dispositivos_registrados_hoje[device_id] = nome
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(dispositivos_registrados_hoje, f, indent=4)
    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao salvar log de dispositivos: {e}")

# --- 4. INICIALIZAÇÃO DO FLASK ---
app = Flask(__name__)
app.secret_key = 'chave_seScreta_para_sessoes_flask'
Compress(app)

# --- Carregar o estado dos dispositivos NA INICIALIZAÇÃO ---
print("Carregando estado inicial dos dispositivos...")
dispositivos_registrados_hoje = carregar_dispositivos_registrados()
# Define a data atual (com fuso) para o cache em memória
data_log_dispositivos_em_memoria = datetime.now(TZ_SAO_PAULO).date()
# --- FIM DA CARGA INICIAL ---


# --- 6. FUNÇÕES PRINCIPAIS DO APP (QRCODE E BACKUP LOCAL) ---

def limpar_qr_codes_antigos(arquivo_para_manter):
    """
    Exclui todos os arquivos 'qrcode_*.png' da pasta de dados,
    exceto o arquivo que acabou de ser gerado e está em uso.
    """
    print(f"🧹 Iniciando limpeza de QR Codes antigos. Mantendo: {arquivo_para_manter}")
    arquivos_excluidos = 0
    try:
        # Itera sobre todos os arquivos na pasta de dados
        for filename in os.listdir(PASTA_DADOS_APP):

            # Verifica se é um arquivo de QR Code
            if filename.startswith("qrcode_") and filename.endswith(".png"):

                # NÃO exclui o arquivo que acabamos de gerar
                if filename != arquivo_para_manter:
                    try:
                        caminho_arquivo = os.path.join(PASTA_DADOS_APP, filename)
                        os.remove(caminho_arquivo)
                        print(f"-> 🗑️ QR Code antigo excluído: {filename}")
                        arquivos_excluidos += 1
                    except Exception as e_remove:
                        print(f"-> ❌ Falha ao excluir {filename}: {e_remove}")

    except Exception as e:
        print(f"❌ AVISO: Falha ao listar pasta para limpar QR Codes antigos: {e}")

    if arquivos_excluidos == 0:
        print("-> Nenhum QR Code antigo para excluir.")

def gerar_qrcode_e_html():
    global ultimo_qr_code

    novo_uuid = str(uuid.uuid4())
    ultimo_qr_code = novo_uuid

    with app.app_context():
        link_registro = url_for('registrar', uuid=novo_uuid, _external=True)

    qr_filename = f"qrcode_{novo_uuid}.png"
    qr_path = os.path.join(PASTA_DADOS_APP, qr_filename)

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(link_registro)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    try:
        if os.path.exists(LOGO_LOCAL_PATH):
            logo = Image.open(LOGO_LOCAL_PATH)
            basewidth = 100
            wpercent = (basewidth/float(logo.size[0]))
            hsize = int((float(logo.size[1])*float(wpercent)))
            logo = logo.resize((basewidth, hsize), Image.LANCZOS)
            pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
            img.paste(logo, pos)
    except Exception as e:
        print(f"Aviso: Não foi possível adicionar o logo ao QR Code. {e}")

    # 1. Salva o NOVO arquivo de QR Code
    img.save(qr_path)

    # 2. Chama a limpeza, passando o nome do arquivo que deve ser MANTIDO
    executor.submit(limpar_qr_codes_antigos, qr_filename)

    qr_url = f"/qrcodes/{qr_filename}"
    logo_url = "/static/unica_logo.png"
    agora_sp = datetime.now(TZ_SAO_PAULO)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="{EXPIRACAO_MINUTOS_QR * 60}"> <title>Registro de Presença dos Estagiários</title>
    <style>
        :root {{
            --primary: #2f6af2; --accent: #6c5ce7; --ink: #0f172a;
            --muted: #64748b; --card: #ffffff; --bg: #f7f8fc;
            --shadow: 0 15px 40px rgba(47, 106, 242, 0.2); --radius: 16px;
        }}
        * {{ box-sizing: border-box; }}
        html, body {{ height: 100%; }}
        body {{
            margin: 0; font-family: Arial, Helvetica, sans-serif;
            color: var(--ink);
            background: var(--bg); display: flex; flex-direction: column;
            align-items: center; justify-content: center; padding: 20px;
        }}
        .main-container {{
            width: 90vw; max-width: 1360px; background: #fff;
            border-radius: var(--radius); box-shadow: var(--shadow);
            border: 1px solid rgba(47, 106, 242, 0.1); display: flex;
            flex-direction: column; position: relative;
        }}
        .header {{
            z-index: 50; background: #fff;
            border-bottom: 1px solid #eef2f7;
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 28px; width: 100%; border-radius: var(--radius) var(--radius) 0 0;
        }}
        .brand {{ display: flex; align-items: center; gap: 12px; font-weight: 700; color: var(--primary); }}
        .brand img {{ height: 28px; }}
        .nav {{ display: flex; align-items: center; gap: 32px; }}
        .nav a {{ color: var(--ink); text-decoration: none; font-weight: 600; position: relative; }}
        .nav a:hover {{ color: var(--primary); }}
        .dropdown {{ position: relative; }}
        .dropdown-menu {{
            position: absolute; top: 36px; right: 0;
            min-width: 280px;
            background: #fff; border: 1px solid #eaeef5;
            border-radius: 12px; box-shadow: var(--shadow); padding: 12px; display: none; z-index: 100;
        }}
        .dropdown:hover .dropdown-menu, .dropdown.open .dropdown-menu {{ display: block; }}
        .contact-row {{ display: flex; align-items: center; gap: 10px; padding: 8px 6px; border-radius: 10px; }}
        .contact-row:hover {{ background: #f2f4ff; }}
        .contact-meta {{ font-size: 12px; color: var(--muted); }}
        .popover {{ position: relative; }}
        .popover-panel {{
            position: absolute; top: 36px; left: 50%;
            transform: translateX(-50%);
            width: min(560px, 92vw); background: #fff; border: 1px solid #eaeef5;
            border-radius: 12px; box-shadow: var(--shadow); padding: 16px 18px;
            display: none;
            line-height: 1.5; z-index: 100;
        }}
        .popover:hover .popover-panel, .popover.open .popover-panel {{ display: block; }}
        .popover-panel p {{ margin: 0 0 10px 0; color: #1f2f37; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; }}
        .shell {{ width: 100%; padding: 0 20px 20px 20px; }}
        .hero {{ padding: 30px; position: relative; overflow: hidden; }}
        .hero-grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 24px; align-items: center; }}
        .hero-content {{ position: relative; padding-top: 40px; }}
        .hero-content img {{ position: absolute; top: -75px; left: 0; height: 125px; }}
        .title {{ font-size: 44px; line-height: 1.05; margin: 0 0 14px 0; }}
        .lead {{ color: var(--muted); font-size: 16px; }}
        .qr-wrap {{ text-align: center; }}
        .qr-wrap img {{ width: 320px; max-width: 100%; height: auto; border-radius: 12px; border: 6px solid #f4f6ff; }}
        .qr-caption {{ margin-top: 10px; color: var(--muted); font-weight: 600; }}
        .stamp {{ margin-top: 14px; text-align: center; color: var(--muted); font-size: 14px; }}
        .deco {{
            position: absolute;
            inset: 0; pointer-events: none;
            background: radial-gradient(600px 600px at -120px 80%, rgba(47, 106, 242, .08), transparent 60%),
                        radial-gradient(520px 520px at 110% 80px, rgba(108, 92, 231, .12), transparent 60%);
            border-radius: inherit; opacity: 1;
        }}
        @media (max-width: 900px) {{
            .main-container {{ width: 95vw; }}
            body {{ justify-content: flex-start; }}
            .hero-grid {{ grid-template-columns: 1fr; gap: 12px; }}
            .title {{ font-size: 34px; }}
            .nav {{ gap: 18px; }}
            .popover-panel {{ left: auto; right: 0; }}
            .deco {{ display: none; }}
        }}
    </style>
    </head>
    <body>
    <div class="main-container">
        <header class="header">
            <div class="brand">
                <img src="{logo_url}" alt="UNICAA">
            </div>
            <nav class="nav">
                <div>
                    <a href="/gestor/login" target="_blank">PAINEL GESTOR</a>
                </div>
                <div class="dropdown" id="contact">
                    <a href="#" aria-haspopup="true" aria-expanded="false">CONTATO</a>
                    <div class="dropdown-menu" role="menu" aria-label="Contatos Teams">
                        <div class="contact-row">
                            <div>
                                <div><strong>Hederson Gomes</strong></div>
                                <div class="contact-meta">Equipe da UNICAA</div>
                            </div>
                        </div>
                        <div class="contact-row">
                            <div>
                                <div><strong>Vinicius Dal Mas Ligabue</strong></div>
                                <div class="contact-meta">Equipe da UNICAA</div>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>
        </header>
        <main class="shell">
            <section class="hero">
                <div class="deco"></div>
                <div class="hero-grid">
                    <div class="hero-content">
                        <img src="{logo_url}" alt="UNICAA">
                        <h1 class="title">Registro de Presença dos Estagiários</h1>
                        <p class="lead">Escaneie o QR Code ao lado para registrar sua presença com segurança.</p>
                    </div>
                    <div class="qr-wrap">
                        <img src="{qr_url}" alt="QR Code de registro">
                        <div class="qr-caption">Escaneie o QR Code para Registrar</div>
                        <div class="stamp">Gerado em {agora_sp.strftime('%d/%m/%Y')}</div>
                    </div>
                 </div>
            </section>
        </main>
    </div>
    <script>
        const contact = document.getElementById('contact');
        contact.querySelector('a').addEventListener('click', (e) => {{
            e.preventDefault();
            contact.classList.toggle('open');
        }});
        document.addEventListener('click', (e) => {{
            if (!contact.contains(e.target)) contact.classList.remove('open');
        }});
    </script>
    </body>
    </html>
    """

    with open(HTML_FILENAME, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ QR Code ({qr_filename}) e HTML (Novo Visual) gerados com sucesso.")

def fazer_backup_diario():
    print("⚙️  Iniciando rotina de backup diário local...")
    with csv_lock:
        if not os.path.exists(CSV_FILENAME_LOCAL) or os.path.getsize(CSV_FILENAME_LOCAL) <= len(','.join(CSV_HEADER)) + 2:
            print("-> Arquivo de registro vazio. Backup não necessário.")
            return

        hoje = datetime.now(TZ_SAO_PAULO)
        pasta_destino_mes = os.path.join(PASTA_BACKUPS_DIARIOS_LOCAL, hoje.strftime('%Y-%m'))
        os.makedirs(pasta_destino_mes, exist_ok=True)

        nome_backup = f"registro_backup_{hoje.strftime('%Y-%m-%d')}.csv"
        caminho_backup = os.path.join(pasta_destino_mes, nome_backup)

        try:
            shutil.copy(CSV_FILENAME_LOCAL, caminho_backup)
            print(f"✅ Backup diário salvo localmente em: {caminho_backup}")

            # Limpar o arquivo principal
            with open(CSV_FILENAME_LOCAL, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
            print("-> Arquivo de registro local limpo para o próximo dia.")

            # Limpar também o arquivo 'live'
            with open(CSV_LIVE_LOCAL, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
            print("-> Arquivo 'live' limpo para o próximo dia.")

        except Exception as e:
            print(f"❌ Erro during o backup diário local: {e}")

# --- (NOVA FUNÇÃO DE CORREÇÃO PARA APPS PERSISTENTES - BUG 'DIA SEGUINTE') ---
def verificar_e_limpar_log_diario_em_memoria():
    """
    Verifica se o dia mudou desde que o app foi carregado (crítico para PythonAnywhere).
    Se o dia mudou, esta função limpa o dicionário de dispositivos em memória
    para permitir os registros do novo dia.
    """
    global dispositivos_registrados_hoje, data_log_dispositivos_em_memoria

    # Usar a data de São Paulo para consistência
    hoje_sp = datetime.now(TZ_SAO_PAULO).date()

    # Se a data em memória for de um dia anterior...
    if data_log_dispositivos_em_memoria is None or data_log_dispositivos_em_memoria != hoje_sp:
        print(f"🔄 DETECTADA MUDANÇA DE DIA (de {data_log_dispositivos_em_memoria} para {hoje_sp}).")
        print("... Limpando o cache de dispositivos em memória.")

        with csv_lock: # Usar o lock para segurança
            dispositivos_registrados_hoje.clear()
            data_log_dispositivos_em_memoria = hoje_sp

            try:
                # Tenta recarregar o log de HOJE (caso o app tenha sido reiniciado
                # no meio do dia, por exemplo).
                # A função 'carregar_dispositivos_registrados' já usa
                # 'get_device_log_filename', que está corrigida para o fuso SP.
                dispositivos_registrados_hoje = carregar_dispositivos_registrados()
                print("... Log de dispositivos de HOJE (re)carregado com sucesso.")
            except Exception as e:
                print(f"... Falha ao recarregar log de dispositivos de hoje: {e}. Começando do zero.")
                dispositivos_registrados_hoje = {}
# --- FIM DA NOVA FUNÇÃO ---


# ==========================================================
# 🔧 FUNÇÃO SALVAR_NO_CSV_ASYNC - VERSÃO CORRIGIDA COMPLETA
# ==========================================================

def salvar_no_csv_async(dados):
    try:
        with csv_lock:
            # 1. Checagem de dispositivo (na memória)
            if dados['device_id'] in dispositivos_registrados_hoje:
                nome_registrado = dispositivos_registrados_hoje[dados['device_id']]
                if dados['tipo'] == 'entrada':
                    return {"mensagem": f"🔒 Este dispositivo já registrou a ENTRADA para '{nome_registrado}' hoje."}, 409
                elif dados['nome'].lower() != nome_registrado.lower():
                    return {"mensagem": f"🔒 Tentativa de SAÍDA inválida. Este dispositivo pertence a '{nome_registrado}' e não pode registrar para '{dados['nome']}'."}, 409

            # 2. Ler o CSV principal
            rows = []
            try:
                with open(CSV_FILENAME_LOCAL, mode="r", newline='', encoding='utf-8') as f:

                    # LINHA 583: Deve ter 5 níveis de indentação (20 espaços)
                    reader = csv.DictReader(f)

                    # LINHA 585: Esta linha DEVE estar perfeitamente alinhada com a 583.
                    rows = list(reader)

            except FileNotFoundError:
                pass

            # 3. Encontrar registro existente (se houver)
            registro_existente_index = -1
            dia_atual_str = dados['agora_str'].split(' ')[0]
            for i, row in enumerate(rows):
                mesmo_nome = row.get('Nome', '').strip().lower() == dados['nome'].lower()
                mesma_data_entrada = row.get('DataHora Entrada', '').startswith(dia_atual_str)
                if mesmo_nome and mesma_data_entrada:
                    registro_existente_index = i
                    break

            # 4. Lógica de Entrada/Saída
            if dados['tipo'] == 'entrada':
                if registro_existente_index != -1:
                    return {"mensagem": f"🔒 {dados['nome']}, você já registrou ENTRADA hoje no CSV."}, 409

                # Salva na memória e no log de dispositivos
                salvar_dispositivo_registrado(dados['device_id'], dados['nome'])

                novo_registro = {
                    "UUID": str(uuid.uuid4()), "IP": dados['ip'], "DeviceID": dados['device_id'],
                    "ID Estagiário": dados.get('id_estagiario'),
                    "Nome": dados['nome'], "Sala": dados['sala'],
                    "Justificativa": dados['justificativa'], "Arquivo": dados['arquivo_path'],
                    "DataHora Entrada": dados['agora_str'], "DataHora Saída": ""
                }
                rows.append(novo_registro)

            elif dados['tipo'] == 'saida':
                if registro_existente_index == -1:
                    return {"mensagem": f"❌ Não foi possível registrar a SAÍDA. Não existe um registro de ENTRADA para {dados['nome']} hoje."}, 400

                registro_existente = rows[registro_existente_index]
                if registro_existente.get('DataHora Saída', '').strip():
                    return {"mensagem": f"🔒 {dados['nome']}, você já registrou SAÍDA hoje."}, 409

                registro_existente['DataHora Saída'] = dados['agora_str']
                if not registro_existente.get('ID Estagiário') and dados.get('id_estagiario'):
                    registro_existente['ID Estagiário'] = dados['id_estagiario']
                if dados['justificativa']:
                    registro_existente['Justificativa'] += f" / Saída: {dados['justificativa']}"
                if dados['arquivo_path']:
                    registro_existente['Arquivo'] += f",{dados['arquivo_path']}"
                if not registro_existente.get('DeviceID'):
                    registro_existente['DeviceID'] = dados['device_id']

            # 5. Salvar no CSV principal
            try:
                with open(CSV_FILENAME_LOCAL, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                    writer.writeheader()
                    writer.writerows(rows)
            except Exception as e:
                print(f"❌ ERRO CRÍTICO AO SALVAR NO CSV PRINCIPAL: {e}")
                return {"mensagem": f"❌ Erro Crítico ao salvar dados: {e}"}, 500

            # 6. Cópia para o CSV "live"
            try:
                shutil.copy(CSV_FILENAME_LOCAL, CSV_LIVE_LOCAL)
                print(f"✅ CSV 'live' local atualizado.")
            except Exception as e:
                print(f"❌ AVISO: Falha ao copiar para CSV 'live': {e}")

            # 7. Envio de e-mail (não é fatal)
            try:
                enviar_email_com_anexo()
            except Exception as e_email:
                print(f"❌ AVISO: O registro foi salvo, mas falhou ao enviar o e-mail de backup: {e_email}")

            # 8. Retorno final de sucesso
            return {"mensagem": f"✅ Registro de {dados['tipo'].upper()} para {dados['nome']} confirmado!"}, 200

    except Exception as e:
        import traceback
        print(f"❌ ERRO dentro de salvar_no_csv_async: {e}")
        traceback.print_exc()
        return {"mensagem": f"❌ Erro interno durante o salvamento: {e}"}, 500


# --- 7. ROTAS FLASK (APP DE PONTO) ---

@app.route("/")
def index():
    global ultimo_qr_code, ultimo_qr_code_timestamp, HTML_FILENAME

    # --- ADICIONADO ---
    # Verifica e limpa o cache de memória se o dia mudou
    verificar_e_limpar_log_diario_em_memoria()
    # --- FIM DA ADIÇÃO ---

    agora = datetime.now(TZ_SAO_PAULO)
    hora_atual = agora.time()

    horario_abertura = time_obj(11, 50)
    horario_fechamento = time_obj(20, 2)

    if not (horario_abertura <= hora_atual <= horario_fechamento):
        return """
        <html><head><title>Sistema Fechado</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style> body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; } </style>
        </head><body>
        <h1>🔒 Sistema de Ponto Fechado</h1>
        <p>O registro de ponto está disponível apenas das 11:50 às 20:02.</p>
        </body></html>
        """

    qr_expirado = False
    if ultimo_qr_code_timestamp:
        tempo_passado = (agora - ultimo_qr_code_timestamp).total_seconds()
        if tempo_passado > (EXPIRACAO_MINUTOS_QR * 60):
            qr_expirado = True
            print(f"-> QR Code expirou. Tempo passado: {tempo_passado}s")

    if not ultimo_qr_code or not os.path.exists(HTML_FILENAME) or qr_expirado:
        print("🔄 Gerando novo QR Code (expirado ou não existente)...")
        gerar_qrcode_e_html()
        ultimo_qr_code_timestamp = agora

    try:
        return send_file(HTML_FILENAME)
    except FileNotFoundError:
        abort(404, "Arquivo HTML não encontrado. Aguarde a próxima geração.")

@app.route("/static/<filename>")
def serve_static(filename):
    return send_from_directory(PASTA_STATIC, filename)

@app.route("/qrcodes/<filename>")
def serve_qrcode(filename):
    return send_from_directory(PASTA_DADOS_APP, filename)

@app.route("/anexos/<filename>")
def serve_anexo(filename):
    return send_from_directory(PASTA_ANEXOS_LOCAL, filename)

@app.route("/api/get_nome/<id_estagiario>")
def get_nome(id_estagiario):
    nome = ID_NOME_MAP.get(id_estagiario, "")
    if nome:
        return jsonify({"nome": nome})
    else:
        return jsonify({"erro": "ID não encontrado"}), 404

@app.route("/registrar/<uuid>", methods=["GET"])
def registrar(uuid):
    # --- ADICIONADO ---
    # Verifica e limpa o cache de memória se o dia mudou
    verificar_e_limpar_log_diario_em_memoria()
    # --- FIM DA ADIÇÃO ---

    agora = datetime.now(TZ_SAO_PAULO).time()
    if not (time_obj(11, 50) <= agora <= time_obj(20, 2)):
         return "<h3>🚫 Sistema Fechado</h3><p>O horário para registro é das 11:50 às 20:02.</p>", 403

    if uuid != ultimo_qr_code:
        return "<h3>⚠️ Este QR Code expirou. Escaneie novamente!</h3>", 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    try:
        ip_addr_obj = ipaddress.ip_address(ip)
        if not any(ip_addr_obj in rede for rede in REDES_PERMITIDAS):
            return f"<h2>🚫 Acesso negado</h2><p>Seu IP ({ip}) não está na lista de redes autorizadas.</p>", 403
    except ValueError:
        return f"<h2>🚫 Acesso negado</h2><p>IP com formato inválido detectado: {ip}</p>", 403

    return f"""<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Registro - TJRS</title></head><body
style="background:white; color:black; font-family:Arial, sans-serif; padding:20px; text-align:center;"><h1>Registro de Ponto</h1><form id="registro-form" action="/confirmar/{uuid}" method="POST" enctype="multipart/form-data" onsubmit="enviarRegistro(event)"><select name="tipo_registro" required style="width:100%; padding:10px; font-size:16px; margin-bottom:10px;"><option value="" disabled selected>Selecione o Tipo de Registro</option><option value="entrada">Entrada</option><option value="saida">Saída</option></select>
<input type="text" id="id_estagiario" name="id_estagiario" placeholder="Seu ID de 5 dígitos" required maxlength="5" oninput="buscarNome()" style="width:100%; padding:10px; font-size:16px; margin-bottom:10px; box-sizing: border-box;" />
<div id="nome-resultado" style="margin: 10px 0; font-size: 1.1em; min-height: 25px;"></div><input type="hidden" name="nome" id="nome_completo"><select name="sala" required style="width:100%; padding:10px; font-size:16px; margin-bottom:10px;"><option value="" disabled selected>Selecione sua sala</option><option>Sala 2001</option><option>Sala 2205</option><option>Sala 2107</option><option>Sala 2203</option><option>Sala 2207</option></select><textarea name="justificativa" placeholder="Justificativa (Opcional)" style="width:100%; padding:10px; font-size:16px; margin-bottom:10px; min-height: 80px; box-sizing: border-box;"></textarea><label for="arquivo" style="display:block; margin-bottom: 5px;">Anexar comprovante (Opcional):</label><input type="file" id="arquivo" name="arquivo" accept="image/*,application/pdf" style="width:100%; padding:10px; font-size:16px; margin-bottom:15px; box-sizing: border-box;"><input type="hidden" name="device_id" id="device_id"><button id="submit-button" type="submit" disabled style="padding:12px 20px; font-size:16px; background:#cccccc; color:#666; border:none; border-radius:5px; cursor:not-allowed;">Registrar</button></form><div id="mensagem"></div><script>function gerarUUID() {{ return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{ var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8); return v.toString(16); }}); }} let deviceId = localStorage.getItem('device_id'); if (!deviceId) {{ deviceId = gerarUUID(); localStorage.setItem('device_id', deviceId); }} document.getElementById('device_id').value = deviceId; const idInput = document.getElementById('id_estagiario'); const nomeResultadoDiv = document.getElementById('nome-resultado'); const nomeCompletoInput = document.getElementById('nome_completo'); const submitButton = document.getElementById('submit-button'); async function buscarNome() {{ const id = idInput.value; if (id.length === 5) {{ nomeResultadoDiv.innerHTML = 'Buscando...'; try {{ const resposta = await fetch(`/api/get_nome/${{id}}`); if (resposta.ok) {{ const data = await resposta.json(); nomeResultadoDiv.innerHTML = `<p style="color:green;">Olá,
<strong>${{data.nome}}</strong>! Confirme seus dados e registre.</p>`; nomeCompletoInput.value = data.nome; submitButton.disabled = false; submitButton.style.background = '#1465bb'; submitButton.style.cursor = 'pointer';
submitButton.style.color = '#fff';
}} else {{ nomeResultadoDiv.innerHTML = '<p style="color:red;">ID não encontrado. Verifique e tente novamente.</p>'; nomeCompletoInput.value = '';
submitButton.disabled = true; submitButton.style.background = '#cccccc'; submitButton.style.cursor = 'not-allowed'; submitButton.style.color = '#666';
}} }} catch(err) {{ nomeResultadoDiv.innerHTML = '<p style="color:red;">Erro de conexão ao buscar ID.</p>';
}} }} else {{ nomeResultadoDiv.innerHTML = '';
nomeCompletoInput.value = ''; submitButton.disabled = true; submitButton.style.background = '#cccccc'; submitButton.style.cursor = 'not-allowed';
submitButton.style.color = '#666';
}} }} async function enviarRegistro(e) {{ e.preventDefault(); const form = e.target; const dados = new FormData(form);
const botao = form.querySelector("button");
botao.disabled = true; botao.innerText = "Enviando..."; try {{ const resposta = await fetch(form.action, {{method:"POST", body:dados}});
const json = await resposta.json();
const div = document.getElementById("mensagem"); div.innerHTML = `<p style='margin-top:20px;font-size:1.1em;color:${{resposta.ok?"green":"red"}};'>${{json.mensagem}}</p>`; if(resposta.ok){{ form.remove();
}} else {{ botao.disabled = false; botao.innerText = "Tentar Novamente";
}} }} catch(erro) {{ console.error("Erro:",erro); alert("❌ Erro ao enviar registro.");
botao.disabled = false; botao.innerText = "Registrar";
}} }}</script></body></html>"""


@app.route("/confirmar/<uuid>", methods=["POST"])
def confirmar(uuid):
    # Verifica e limpa o cache de memória se o dia mudou
    # (Esta chamada é redundante se já foi chamada no index/registrar, mas não causa mal)
    verificar_e_limpar_log_diario_em_memoria()

    agora_dt = datetime.now(TZ_SAO_PAULO)
    agora_time = agora_dt.time()
    if not (time_obj(11, 50) <= agora_time <= time_obj(20, 2)):
        return jsonify({"mensagem": "🚫 O sistema está fechado para registros."}), 403

    if uuid != ultimo_qr_code:
        return jsonify({"mensagem": "❌ Este QR Code expirou. Por favor, escaneie novamente."}), 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    try:
        ip_addr_obj = ipaddress.ip_address(ip)
        if not any(ip_addr_obj in rede for rede in REDES_PERMITIDAS):
            return jsonify({"mensagem": f"🚫 Acesso negado. IP ({ip}) não autorizado."}), 403
    except ValueError:
        return jsonify({"mensagem": f"🚫 Acesso negado. IP inválido: {ip}"}), 403

    nome = request.form.get("nome", "").strip()
    id_estagiario = request.form.get("id_estagiario", "").strip()
    tipo = request.form.get("tipo_registro")
    device_id = request.form.get("device_id", "").strip()
    sala = request.form.get("sala")
    justificativa = request.form.get("justificativa", "")
    arquivo = request.files.get("arquivo")

    if not device_id:
        return jsonify({"mensagem": "❌ Erro: Não foi possível identificar o dispositivo. Atualize a página e tente novamente."}), 400
    if not nome:
        return jsonify({"mensagem": "❌ Erro: O ID não foi validado ou o nome não foi encontrado. Volte e digite seu ID novamente."}), 400
    if not all([nome, id_estagiario, sala, tipo]):
        return jsonify({"mensagem": "❌ Erro: ID, Nome, Sala e Tipo são obrigatórios."}), 400

    nome_arquivo_salvo = ""
    if arquivo and arquivo.filename:
        os.makedirs(PASTA_ANEXOS_LOCAL, exist_ok=True)
        extensao = os.path.splitext(arquivo.filename)[1].lower()
        nome_base = f"{uuid}_{int(time.time())}"
        try:
            if extensao == ".heic":
                print("❌ ERRO: Tentativa de upload de .heic bloqueada.")
                return jsonify({"mensagem": "❌ Erro: Anexos .heic não são suportados. Por favor, converta para PNG ou JPG."}), 400

            nome_arquivo_salvo = f"{nome_base}{extensao}"
            caminho_arquivo_local = os.path.join(PASTA_ANEXOS_LOCAL, nome_arquivo_salvo)
            arquivo.save(caminho_arquivo_local)
        except Exception as e:
            print(f"❌ Erro ao processar ou salvar anexo: {e}")
            return jsonify({"mensagem": f"❌ Erro ao processar o anexo: {e}"}), 500

    dados_para_salvar = {
        'uuid': uuid, 'ip': ip, 'device_id': device_id, 'nome': nome,
        'id_estagiario': id_estagiario,
        'sala': sala, 'justificativa': justificativa,
        'arquivo_path': nome_arquivo_salvo, 'tipo': tipo, 'agora_str': agora_dt.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Submeter a tarefa assíncrona
    future = executor.submit(salvar_no_csv_async, dados_para_salvar)

    # TRECHO DE CÓDIGO ATUALIZADO
    try:
        result = future.result()
        print(f"DEBUG: Resultado retornado pela função: {result}")

        if not result or not isinstance(result, tuple) or len(result) != 2:
            print("⚠️ Função não retornou um tuple (dict, status).")
            return jsonify({"mensagem": "❌ Erro interno: retorno inválido."}), 500

        response_data, status_code = result

        return jsonify(response_data), status_code

    except Exception as e:
        import traceback
        print(f"❌ ERRO AO PROCESSAR FUTURE: {e}")
        traceback.print_exc()
        return jsonify({"mensagem": "❌ Erro interno do servidor. Tente novamente."}), 500


# --- 8. ROTAS DE GESTOR ---
@app.route("/gestor/login", methods=["GET", "POST"])
def gestor_login():
    if request.method == "POST":
        if request.form.get("senha") == GESTOR_PASSWORD:
            session['gestor_logado'] = True
            return redirect(url_for('gestor_dashboard'))
        else:
            return render_template('gestor_login.html', erro="Senha incorreta.")
    return render_template('gestor_login.html', erro=None)

@app.route("/gestor/logout")
def gestor_logout():
    session.pop('gestor_logado', None)
    return redirect(url_for('gestor_login'))


@app.route("/gestor/dashboard")
def gestor_dashboard():
    if not session.get('gestor_logado'):
        return redirect(url_for('gestor_login'))

    filtro_nome = request.args.get('filtro_nome', '').strip()
    filtro_sala = request.args.get('filtro_sala', '').strip()
    filtro_id_estagiario = request.args.get('filtro_id_estagiario', '').strip()

    filtros_ativos = {
        'nome': filtro_nome,
        'sala': filtro_sala,
        'id_estagiario': filtro_id_estagiario
    }

    titulo_registros = "Registros Diários"
    registros_df = pd.DataFrame(columns=CSV_HEADER)

    try:
        if os.path.exists(CSV_LIVE_LOCAL):
            registros_df = pd.read_csv(CSV_LIVE_LOCAL)

            for col in ['Nome', 'Sala', 'DeviceID', 'ID Estagiário']:
                if col not in registros_df.columns:
                    registros_df[col] = pd.NA

            registros_df['Nome'] = registros_df['Nome'].astype(str)
            registros_df['Sala'] = registros_df['Sala'].astype(str)
            registros_df['DeviceID'] = registros_df['DeviceID'].astype(str)
            registros_df['ID Estagiário'] = registros_df['ID Estagiário'].astype(str)

            # Aplicar filtros
            if filtro_nome:
                registros_df = registros_df[registros_df['Nome'].str.contains(filtro_nome, case=False, na=False)]
            if filtro_sala:
                registros_df = registros_df[registros_df['Sala'].str.contains(filtro_sala, case=False, na=False)]
            if filtro_id_estagiario:
                registros_df = registros_df[registros_df['ID Estagiário'].str.contains(filtro_id_estagiario, case=False, na=False)]

            # Ordenar e limitar
            if 'DataHora Entrada' in registros_df.columns:
                registros_df = registros_df.sort_values(by='DataHora Entrada', ascending=False)

            if any(filtros_ativos.values()):
                    titulo_registros = f"Mostrando {len(registros_df)} resultado(s) para sua busca"
            else:
                registros_df = registros_df.head(50)
                titulo_registros = "Registros Diários (Últimos 50)"

        registros_df = registros_df.fillna('')
        colunas = registros_df.columns.tolist()
        lista_de_registros = registros_df.to_dict('records')

    except Exception as e:
        session['mensagem'] = f"Erro ao ler CSV: {e}"
        lista_de_registros = []
        colunas = CSV_HEADER
        titulo_registros = "Erro ao carregar registros"

    # --- REMOVIDO: Bloco "Carregar relatórios gerados" ---

    return render_template(
        'gestor_dashboard.html',
        registros=lista_de_registros,
        colunas=colunas,
        filtros=filtros_ativos,
        titulo_registros=titulo_registros,
        # --- REMOVIDO: relatorios_gerados=relatorios ---
        mensagem=session.pop('mensagem', None)
    )


@app.route("/gestor/download_csv")
def gestor_download_csv():
    if not session.get('gestor_logado'):
        abort(43)
    try:
        return send_file(CSV_LIVE_LOCAL, as_attachment=True, download_name='registros_diarios_live.csv')
    except FileNotFoundError:
        abort(404, "Arquivo CSV 'live' não encontrado.")

# --- REMOVIDO: Rota /gestor/gerar_relatorio ---

# --- REMOVIDO: Rota /gestor/download_relatorio ---


# --- 9. ROTAS DE EDIÇÃO ATUALIZADAS ---

@app.route("/gestor/editar/<uuid>", methods=["GET"])
def gestor_editar_registro_form(uuid):
    if not session.get('gestor_logado'):
        return redirect(url_for('gestor_login'))

    registro = None
    try:
        # Tenta ler do 'live' primeiro
        df = pd.read_csv(CSV_LIVE_LOCAL)
        df = df.fillna('')
        registro_df = df[df['UUID'] == uuid]

        if not registro_df.empty:
            registro = registro_df.to_dict('records')[0]
        else:
            # Se não achar, procura no principal (pode ser um registro antigo)
            with csv_lock:
                df_main = pd.read_csv(CSV_FILENAME_LOCAL)
                df_main = df_main.fillna('')

            registro_df_main = df_main[df_main['UUID'] == uuid]
            if not registro_df_main.empty:
                 registro = registro_df_main.to_dict('records')[0]
            else:
                session['mensagem'] = f"ERRO: Registro com UUID {uuid} não encontrado em nenhum arquivo."
                return redirect(url_for('gestor_dashboard'))

        if 'ID Estagiário' not in registro:
            registro['ID Estagiário'] = ''

    except Exception as e:
        session['mensagem'] = f"ERRO ao ler dados para edição: {e}"
        return redirect(url_for('gestor_dashboard'))

    return render_template('gestor_editar_registro.html', registro=registro)


@app.route("/gestor/editar/salvar", methods=["POST"])
def gestor_salvar_edicao():
    if not session.get('gestor_logado'):
        abort(403)

    try:
        uuid = request.form.get('uuid')
        nome = request.form.get('nome')
        id_estagiario = request.form.get('id_estagiario')
        sala = request.form.get('sala')
        justificativa = request.form.get('justificativa')
        data_entrada = request.form.get('data_entrada')
        data_saida = request.form.get('data_saida')

        if not uuid:
            session['mensagem'] = "ERRO: UUID não fornecido. Edição falhou."
            return redirect(url_for('gestor_dashboard'))

        with csv_lock:
            # Edições DEVEM ir para o arquivo principal
            df = pd.read_csv(CSV_FILENAME_LOCAL)

            index_list = df.index[df['UUID'] == uuid].tolist()
            if not index_list:
                session['mensagem'] = f"ERRO: Registro com UUID {uuid} não encontrado no momento de salvar."
                return redirect(url_for('gestor_dashboard'))

            idx_para_editar = index_list[0]

            df.at[idx_para_editar, 'Nome'] = nome
            df.at[idx_para_editar, 'ID Estagiário'] = id_estagiario
            df.at[idx_para_editar, 'Sala'] = sala
            df.at[idx_para_editar, 'Justificativa'] = justificativa
            df.at[idx_para_editar, 'DataHora Entrada'] = data_entrada
            df.at[idx_para_editar, 'DataHora Saída'] = data_saida

            df.to_csv(CSV_FILENAME_LOCAL, index=False, encoding='utf-8')

        # Sincronizar a mudança com o arquivo 'live'
        shutil.copy(CSV_FILENAME_LOCAL, CSV_LIVE_LOCAL)

        session['mensagem'] = f"Registro de '{nome}' (UUID: {uuid}) atualizado com sucesso."
        return redirect(url_for('gestor_dashboard'))

    except Exception as e:
        print(f"ERRO CRÍTICO em gestor_salvar_edicao: {e}")
        session['mensagem'] = f"ERRO CRÍTICO ao salvar edição: {e}"
        return redirect(url_for('gestor_dashboard'))


# --- 10. INICIALIZAÇÃO (PARA TAREFAS E TESTE LOCAL) ---
if __name__ == "__main__":
    # Esta parte é para rodar tarefas agendadas (como o backup)
    if len(sys.argv) > 1 and sys.argv[1] == '--run-backup':
        print("⚙️  Executando tarefa de backup diário...")
        if csv_lock.acquire(timeout=60):
            try:
                fazer_backup_diario()
            finally:
                csv_lock.release()
            print("✅ Tarefa de backup concluída.")
        else:
            print("❌ ERRO DE BACKUP: Não foi possível obter o lock.")
        exit()

    # Esta parte é para rodar o app localmente (python app.py)
    # O PythonAnywhere NÃO usa esta parte
    print("🚀 Servidor Flask de DESENVOLVIMENTO iniciado. Acesse http://127.0.0.1:5000")
    print("   Acesso de Gestor: http://127.0.0.1:5000/gestor/login")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)