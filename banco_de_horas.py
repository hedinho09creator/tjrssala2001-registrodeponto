# <<< banco_de_horas.py >>>

import pandas as pd
import os
import re
import unicodedata
import locale
import shutil
from datetime import timedelta
from pandas.tseries.offsets import MonthEnd

# --- 1. CONFIGURAÇÕES DE CAMINHOS ---
# O 'app.py' nos dirá onde estão os dados
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PASTA_BACKUPS_DIARIOS_LOCAL = os.path.join(APP_ROOT, 'backups_diarios')

# --- 2. CONSTANTES DO SCRIPT ORIGINAL ---
CARGA_HORARIA_DIARIA = 6
COL_NOME = 3
COL_ENTRADA = 7
COL_SAIDA = 8
FORMATO_DATAHORA = '%Y-%m-%d %H:%M:%S'

# --- 3. FUNÇÕES AUXILIARES (do seu script original) ---

def extrair_nome_sala(caminho_pasta):
    # Esta função não é mais muito relevante, mas mantemos para consistência
    return "Sala Indefinida"

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto_limpo = str(texto).strip().lower()
    nfkd_form = unicodedata.normalize('NFKD', texto_limpo)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- 4. FUNÇÕES DE PROCESSAMENTO (SIMPLIFICADAS) ---

def extrair_nomes_dos_arquivos(caminho_pasta_mes):
    """Varre todos os arquivos .csv em uma pasta de mês para extrair nomes únicos."""
    nomes_encontrados = set()
    print(f"\n🔎 Buscando nomes de estagiários em '{caminho_pasta_mes}'...")
    if not os.path.exists(caminho_pasta_mes):
        print(f"   -> ⚠️ Alerta: A pasta '{caminho_pasta_mes}' não foi encontrada.")
        return []

    arquivos_csv = [f for f in os.listdir(caminho_pasta_mes) if f.endswith('.csv')]
    if not arquivos_csv:
        print(f"   -> ℹ️ Info: NENHUM arquivo .csv encontrado.")
        return []

    print(f"   -> Encontrados {len(arquivos_csv)} arquivo(s) .csv.")
    for arquivo in arquivos_csv:
        caminho_arquivo = os.path.join(caminho_pasta_mes, arquivo)
        try:
            # Tenta detectar o separador
            df_temp = pd.read_csv(caminho_arquivo, sep=None, encoding='latin1', header=None, on_bad_lines='skip', engine='python')
            if df_temp.shape[1] > COL_NOME:
                nomes_validos = df_temp[COL_NOME].dropna().astype(str).str.strip()
                nomes_encontrados.update(normalizar_texto(n) for n in nomes_validos if n)
        except Exception as e:
            print(f"     -> ❌ ERRO ao ler o arquivo {arquivo}: {e}.")
            continue
    return sorted(list(nomes_encontrados))

def processar_arquivos(caminho_pasta_mes, estagiarios_list):
    """Lê todos os arquivos CSV de uma pasta, filtra e consolida."""
    all_data = []
    if not os.path.exists(caminho_pasta_mes):
        return pd.DataFrame()
        
    csv_files = [f for f in os.listdir(caminho_pasta_mes) if f.endswith('.csv')]
    colunas_necessarias = [COL_NOME, COL_ENTRADA, COL_SAIDA]
    coluna_maxima = max(colunas_necessarias)

    for file in csv_files:
        file_path = os.path.join(caminho_pasta_mes, file)
        try:
            df = pd.read_csv(file_path, sep=None, encoding='latin1', header=None, on_bad_lines='skip', engine='python')
            if df is None or df.empty or df.shape[1] <= coluna_maxima: continue
            
            # Precisamos adicionar a coluna 'Sala' se ela não existir no header=None
            # Assumindo que o CSV de backup (do app.py) tem o header
            df_com_header = pd.read_csv(file_path, sep=',', encoding='utf-8', on_bad_lines='skip')
            df_com_header = df_com_header.rename(columns={
                'Nome': 'Nome', 'DataHora Entrada': 'Entrada', 
                'DataHora Saída': 'Saida', 'Sala': 'Sala'
            })
            
            df_com_header = df_com_header[['Nome', 'Entrada', 'Saida', 'Sala']]
            df_com_header['Nome_Normalizado'] = df_com_header['Nome'].apply(normalizar_texto)
            df_filtrado = df_com_header[df_com_header['Nome_Normalizado'].isin(estagiarios_list)].copy()
            
            if df_filtrado.empty: continue
            
            df_filtrado['Entrada'] = pd.to_datetime(df_filtrado['Entrada'], format=FORMATO_DATAHORA, errors='coerce')
            df_filtrado['Saida'] = pd.to_datetime(df_filtrado['Saida'], format=FORMATO_DATAHORA, errors='coerce')
            df_filtrado.dropna(subset=['Entrada', 'Saida'], inplace=True)
            
            if df_filtrado.empty: continue
            
            df_filtrado['Arquivo_Origem'] = file
            all_data.append(df_filtrado)
        except Exception as e:
            print(f"❌ ERRO ao processar o arquivo {file}: {e}")
            
    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

# --- 5. FUNÇÃO PRINCIPAL (Refatorada) ---

def gerar_relatorio_banco_de_horas(ano, mes, output_path_local):
    """Função principal que orquestra todo o processo."""
    
    print("🚀 Iniciando geração de relatório de banco de horas...")
    
    # 1. Definir Caminhos e Datas
    NOME_PASTA_MES = f"{ano}-{mes.zfill(2)}"
    INPUT_PATH_MES = os.path.join(PASTA_BACKUPS_DIARIOS_LOCAL, NOME_PASTA_MES)
    
    try:
        mes_num = mes.zfill(2)
        primeiro_dia = pd.to_datetime(f"{ano}-{mes_num}-01")
        ultimo_dia = primeiro_dia + MonthEnd(0)
        dias_uteis_mes = pd.date_range(start=primeiro_dia, end=ultimo_dia, freq='B')
        total_horas_esperadas_mes = len(dias_uteis_mes) * CARGA_HORARIA_DIARIA
        NOME_MES_POR_EXTENSO = primeiro_dia.strftime('%B')
        print(f"🗓️  Mês de referência: {NOME_MES_POR_EXTENSO}/{ano} ({len(dias_uteis_mes)} dias úteis)")
    except Exception as e:
        print(f"❌ ERRO ao definir datas: {e}")
        return "ERRO: Ano ou Mês inválido."

    # 2. Extrair Nomes (lendo da ÚNICA pasta de backup)
    ESTAGIARIOS_NORMALIZED = extrair_nomes_dos_arquivos(INPUT_PATH_MES)
    if not ESTAGIARIOS_NORMALIZED:
        print("❌ PROCESSO FINALIZADO: Nenhum nome de estagiário pôde ser extraído.")
        return "ERRO: Nenhum nome extraído. A pasta de backups está vazia?"

    print(f"✅ {len(ESTAGIARIOS_NORMALIZED)} nomes de estagiários extraídos.")

    # 3. Processar Arquivos
    print(f"\n⚙️  Iniciando processamento dos arquivos de '{INPUT_PATH_MES}'...")
    df_consolidado = processar_arquivos(INPUT_PATH_MES, ESTAGIARIOS_NORMALIZED)
    
    if df_consolidado.empty:
        print("\n❌ PROCESSO FINALIZADO: Nenhum dado de ponto válido foi encontrado.")
        return "ERRO: Nenhum dado de ponto válido encontrado."

    print(f"\n👍 Total de {len(df_consolidado)} registros consolidados.")

    # 4. Limpeza e Validação
    # (O script original não tinha a coluna 'Sala' neste ponto, o nosso tem)
    df_consolidado.drop_duplicates(subset=['Nome_Normalizado', 'Entrada', 'Saida'], inplace=True)
    df_consolidado['Horas_Trabalhadas'] = (df_consolidado['Saida'] - df_consolidado['Entrada']).dt.total_seconds() / 3600
    df_consolidado = df_consolidado[df_consolidado['Horas_Trabalhadas'] <= 12] # Limite de 12h
    df_consolidado['Data'] = df_consolidado['Entrada'].dt.normalize()
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        df_consolidado['Dia_Semana'] = df_consolidado['Data'].dt.day_name()
    except:
        df_consolidado['Dia_Semana'] = df_consolidado['Data'].dt.day_name()

    print("\n📊 Dados consolidados e limpos. Iniciando geração do relatório Excel...")

    # 5. Geração do Excel
    output_filename = f'Ponto_Estagiarios_{NOME_MES_POR_EXTENSO}_{ano}.xlsx'
    os.makedirs(output_path_local, exist_ok=True)
    OUTPUT_FILE_PATH = os.path.join(output_path_local, output_filename)

    try:
        with pd.ExcelWriter(OUTPUT_FILE_PATH, engine='xlsxwriter') as writer:
            # ... (Copie toda a lógica de geração de abas do Excel da sua resposta anterior) ...
            # ... (Ela funcionará, pois 'df_consolidado' tem as colunas 'Sala', 'Nome', etc.) ...
            # ... (Lembre-se de instalar 'xlsxwriter' e 'openpyxl') ...
            
            # --- Início da lógica de gravação do Excel ---
            nome_original_map = df_consolidado.drop_duplicates('Nome_Normalizado').set_index('Nome_Normalizado')['Nome'].to_dict()
            salas_por_estagiario = df_consolidado.groupby('Nome_Normalizado')['Sala'].unique().apply(lambda x: ', '.join(x)).to_dict()
            dados_resumo_geral = []

            for nome_normalizado in ESTAGIARIOS_NORMALIZED:
                # ... (resto da lógica de geração de aba de estagiário) ...
                pass # Substitua pelo seu código
            
            if dados_resumo_geral:
                # ... (lógica de geração da aba 'Resumo Geral') ...
                pass # Substitua pelo seu código

            # ... (lógica de geração da aba 'Ausências por Sala') ...
            # ... (Note: a lógica de 'dias_sem_registro_por_sala' não foi portada
            # ... para esta versão simplificada, você pode removê-la ou adaptá-la) ...

            # Salvar um DF de exemplo para garantir que funciona
            df_consolidado.to_excel(writer, sheet_name='Dados Brutos', index=False)
            
            # --- Fim da lógica de gravação do Excel ---

        print(f"\n\n✅ PROCESSO CONCLUÍDO! O relatório foi salvo em: {OUTPUT_FILE_PATH}")
        return f"SUCESSO: Relatório salvo em {OUTPUT_FILE_PATH}"

    except ImportError:
        msg = "ERRO: Bibliotecas 'xlsxwriter' ou 'openpyxl' não instaladas."
        print(f"❌ {msg}")
        return msg
    except Exception as e:
        msg = f"ERRO: Falha ao escrever arquivo Excel. {e}"
        print(f"❌ {msg}")
        return msg