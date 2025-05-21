#!/usr/bin/env python3
"""
app.py
Interface Streamlit para o Gerador Criativo de Imagens para Marketing Digital

Autor: AI Dev Team

Executar:
  streamlit run app.py
"""
import streamlit as st
import base64
import json
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
import tempfile
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Importar funções do geradorcriativo.py
from geradorcriativo import (
    client,
    analisar_imagem,
    gerar_variacoes, 
    gerar_imagens,
    ensure_size,
    log as orig_log
)

# Configurações do aplicativo
st.set_page_config(
    page_title="Gerador Criativo de Marketing",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Diretório para arquivos temporários
TEMP_DIR = Path(tempfile.gettempdir()) / "gerador_criativo"
TEMP_DIR.mkdir(exist_ok=True)

# Substituir a função de log para usar o Streamlit
def log(msg):
    st.session_state.logs.append(msg)
    st.session_state.logs = st.session_state.logs[-100:]  # Manter apenas os últimos 100 logs

# Inicializar estado da sessão
if "logs" not in st.session_state:
    st.session_state.logs = []
    
if "análise_completa" not in st.session_state:
    st.session_state.análise_completa = False
    
if "variações" not in st.session_state:
    st.session_state.variações = []
    
if "resultados" not in st.session_state:
    st.session_state.resultados = []

if "progresso_atual" not in st.session_state:
    st.session_state.progresso_atual = 0

# Verificar se a API key está disponível no ambiente
api_key_env = os.getenv("OPENAI_API_KEY", "")
if api_key_env:
    st.session_state.api_key = api_key_env
    log("API Key carregada do arquivo .env")
elif "api_key" not in st.session_state:
    st.session_state.api_key = ""

# Funções de utilidade
def salvar_imagem_temporária(imagem_bytes, nome_arquivo):
    """Salva imagem carregada em arquivo temporário"""
    caminho = TEMP_DIR / nome_arquivo
    caminho.write_bytes(imagem_bytes)
    return caminho

def exibir_imagem_base64(img_b64, caption=""):
    """Exibe uma imagem a partir de string base64"""
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(BytesIO(img_bytes))
    st.image(img, caption=caption, use_container_width=True)

def processar_imagem():
    """Função para processar a imagem carregada"""
    if st.session_state.arquivo_imagem is None:
        st.error("Por favor, carregue uma imagem para começar.")
        return
    
    # Verificar API key
    if not st.session_state.api_key:
        st.error("API Key da OpenAI não encontrada. Por favor, insira manualmente ou configure no arquivo .env")
        return False
    
    # Definir API key para uso
    os.environ["OPENAI_API_KEY"] = st.session_state.api_key
    
    # Reiniciar estado
    st.session_state.análise_completa = False
    st.session_state.variações = []
    st.session_state.resultados = []
    st.session_state.progresso_atual = 0
    
    # Ler arquivo carregado
    bytes_imagem = st.session_state.arquivo_imagem.getvalue()
    nome_arquivo = f"imagem_original_{st.session_state.arquivo_imagem.name}"
    caminho_imagem = salvar_imagem_temporária(bytes_imagem, nome_arquivo)
    
    # Barra de progresso
    progresso = st.progress(0, "Iniciando análise...")
    
    try:
        with st.spinner("Analisando a imagem..."):
            # Substituir log function durante processamento
            # Usar import global para geradorcriativo
            import geradorcriativo as gc
            gc.log = log
            
            # Analisar imagem
            spec = analisar_imagem(caminho_imagem)
            st.session_state.spec = spec
            st.session_state.análise_completa = True
            st.session_state.progresso_atual = 33
            progresso.progress(st.session_state.progresso_atual, "Análise concluída")
            
            # Gerar variações
            with st.spinner("Gerando variações de design..."):
                num_variacoes = st.session_state.num_variacoes
                var_pack = gerar_variacoes(spec, num_variacoes)
                st.session_state.variações = var_pack.get("variacoes", [])
                st.session_state.progresso_atual = 66
                progresso.progress(st.session_state.progresso_atual, "Variações geradas")
            
            # Gerar imagens
            with st.spinner("Gerando criativos finais..."):
                tamanho = st.session_state.tamanho
                estilo = st.session_state.estilo
                
                # Verificar se uma plataforma específica foi selecionada
                plataforma = st.session_state.plataforma
                
                # Ajustar tamanho com base na plataforma, se necessário
                if plataforma != "all":
                    if plataforma == "instagram":
                        tamanho = "1024x1024"  # Quadrado para Instagram
                    elif plataforma == "facebook" or plataforma == "story":
                        tamanho = "1024x1536"  # Vertical para Facebook/Stories
                    elif plataforma == "google":
                        tamanho = "1536x1024"  # Horizontal para Google Ads
                    
                    log(f"Ajustando tamanho para {tamanho} com base na plataforma {plataforma}")
                
                resultados = gerar_imagens(st.session_state.variações, spec, tamanho, estilo)
                st.session_state.resultados = resultados
                st.session_state.progresso_atual = 100
                progresso.progress(st.session_state.progresso_atual, "Processo concluído!")
    
    except Exception as e:
        st.error(f"Erro durante o processamento: {str(e)}")
        # Restaurar função de log original
        gc.log = orig_log
        return False
    
    # Restaurar função de log original
    gc.log = orig_log
    return True

# Interface do usuário
st.title("🎨 Gerador Criativo de Marketing Digital")

st.markdown("""
Este aplicativo gera criativos otimizados para marketing digital, analisando uma imagem de 
referência e criando variações com diferentes cores e textos.
""")

# Sidebar para entrada de dados
with st.sidebar:
    st.header("Configurações")
    
    # API Key OpenAI (opcional, se não encontrada no .env)
    if not api_key_env:
        api_key = st.text_input("OpenAI API Key", type="password", 
                                help="Insira sua chave de API da OpenAI ou configure no arquivo .env")
        if api_key:
            st.session_state.api_key = api_key
    else:
        st.success("API Key carregada do arquivo .env")
        # Opção para sobrescrever a chave se necessário
        if st.checkbox("Sobrescrever API Key", value=False):
            api_key = st.text_input("Nova API Key", type="password", 
                                    help="Insira uma API Key diferente da configurada no arquivo .env")
            if api_key:
                st.session_state.api_key = api_key
                st.info("API Key temporariamente sobrescrita para esta sessão")
    
    st.subheader("Opções de Geração")
    
    # Upload de imagem
    arquivo_imagem = st.file_uploader("Carregar imagem de referência", 
                                    type=["png", "jpg", "jpeg"],
                                    help="Selecione uma imagem para servir como referência")
    
    if arquivo_imagem:
        st.session_state.arquivo_imagem = arquivo_imagem
        st.image(arquivo_imagem, caption="Imagem carregada", use_container_width=True)
    
    # Opções de geração
    col1, col2 = st.columns(2)
    with col1:
        num_variacoes = st.number_input("Número de variações", 
                                        min_value=1, max_value=3, value=3,
                                        help="Quantidade de variações a serem geradas")
    with col2:
        tamanho = st.selectbox("Tamanho", 
                               options=["1024x1024", "1024x1536", "1536x1024"],
                               index=1,
                               help="Dimensões do criativo gerado")
    
    estilo = st.selectbox("Estilo visual", 
                          options=["photorealistic", "flat", "3d", "cartoon"],
                          index=0,
                          help="Estilo visual dos criativos")
    
    plataforma = st.selectbox("Plataforma alvo", 
                             options=["all", "facebook", "instagram", "google", "story"],
                             index=0,
                             help="Plataforma de destino para os criativos")
    
    # Guardar opções na sessão
    st.session_state.num_variacoes = num_variacoes
    st.session_state.tamanho = tamanho
    st.session_state.estilo = estilo
    st.session_state.plataforma = plataforma
    
    # Botão de processamento
    if st.button("Gerar Criativos", use_container_width=True):
        if not st.session_state.api_key:
            st.error("Por favor, insira sua API Key da OpenAI ou configure no arquivo .env")
        elif not arquivo_imagem:
            st.error("Por favor, carregue uma imagem de referência")
        else:
            st.session_state.iniciar_processamento = True

# Conteúdo principal
tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise", "🎨 Variações", "🖼️ Resultados", "📝 Logs"])

# Se o processamento foi solicitado
if st.session_state.get("iniciar_processamento", False):
    st.session_state.iniciar_processamento = False
    sucesso = processar_imagem()
    if sucesso:
        st.success("Processamento completo! Navegue pelas abas para ver os resultados.")

# Exibir resultados nas abas
with tab1:  # Aba de Análise
    if st.session_state.análise_completa:
        st.header("Análise da Imagem Original")
        
        # Mostrar detalhes da análise
        if hasattr(st.session_state, "spec"):
            # Dividir a área em colunas
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Exibir imagem original
                if hasattr(st.session_state, "arquivo_imagem"):
                    st.image(st.session_state.arquivo_imagem, caption="Imagem Original", use_container_width=True)
            
            with col2:
                # Exibir informações técnicas
                spec = st.session_state.spec
                
                # Canvas size
                if "canvas_size" in spec:
                    st.info(f"Dimensões: {spec['canvas_size']['w']} x {spec['canvas_size']['h']} pixels")
                
                # Paleta de cores
                if "color_palette" in spec:
                    st.subheader("Paleta de Cores")
                    cores = spec["color_palette"]
                    
                    # Verificar formato da paleta
                    if isinstance(cores, dict):
                        # Exibir caixas de cores
                        cols = st.columns(5)
                        for i, (nome, cor) in enumerate(cores.items()):
                            if nome != "all_colors" and isinstance(cor, str) and cor.startswith("#"):
                                cols[i % 5].color_picker(nome.capitalize(), cor, disabled=True, key=f"análise_cor_{nome}_{i}")
                    elif isinstance(cores, list):
                        # Exibir lista de cores
                        cols = st.columns(len(cores))
                        for i, cor in enumerate(cores):
                            if isinstance(cor, str) and cor.startswith("#"):
                                cols[i].color_picker(f"Cor {i+1}", cor, disabled=True, key=f"análise_cor_list_{i}")
                
                # Elementos detectados
                if "placeholders" in spec:
                    st.subheader("Elementos Detectados")
                    
                    for p in spec["placeholders"]:
                        tipo = p.get("type", "desconhecido").upper()
                        valor = p.get("value", "")
                        id_element = p.get('id', f"elemento_{tipo}")
                        
                        if tipo == "TEXT":
                            st.text_input(f"Texto ({id_element})", valor, disabled=True, key=f"texto_{id_element}")
                        elif tipo == "SHAPE":
                            st.color_picker(f"Forma ({id_element})", valor, disabled=True, key=f"forma_{id_element}")
                        elif tipo == "BUTTON":
                            st.button(valor, disabled=True, key=f"botão_{id_element}")
                        else:
                            st.text_input(f"{tipo} ({id_element})", valor, disabled=True, key=f"outro_{id_element}")
    else:
        st.info("Carregue uma imagem e inicie o processamento para ver a análise.")

with tab2:  # Aba de Variações
    if st.session_state.variações:
        st.header("Variações Geradas")
        
        # Mostrar as variações planejadas
        for i, var in enumerate(st.session_state.variações):
            st.subheader(f"Variação {i+1}: {var.get('id', '')}")
            
            cols = st.columns(2)
            
            with cols[0]:
                # Exibir paleta de cores
                st.write("Paleta de Cores:")
                cores = var.get("cores", {})
                
                # Verificar formato das cores
                if isinstance(cores, dict):
                    cores_cols = st.columns(5)
                    keys = ["primaria", "secundaria", "destaque", "texto", "background"]
                    for j, key in enumerate([k for k in keys if k in cores]):
                        if isinstance(cores[key], str) and cores[key].startswith("#"):
                            cores_cols[j % 5].color_picker(key.capitalize(), cores[key], disabled=True, key=f"var_{i}_{key}")
            
            with cols[1]:
                # Exibir textos planejados
                st.write("Textos:")
                textos = var.get("textos", {})
                
                for id_texto, texto in textos.items():
                    st.text_input(f"Elemento {id_texto}", texto, disabled=True, key=f"variacao_{i}_texto_{id_texto}")
            
            # Exibir ideia gráfica
            if "ideia_grafica" in var:
                with st.expander("Ver descrição detalhada"):
                    st.write(var["ideia_grafica"])
            
            st.divider()
    else:
        st.info("Inicie o processamento para gerar variações.")

with tab3:  # Aba de Resultados
    if st.session_state.resultados:
        st.header("Criativos Gerados")
        
        resultados = st.session_state.resultados
        
        # Agrupar por plataforma
        plataformas = {}
        for r in resultados:
            plat = r.get("plataforma", "Genérico")
            if plat not in plataformas:
                plataformas[plat] = []
            plataformas[plat].append(r)
        
        # Exibir por plataforma
        for plat, items in plataformas.items():
            st.subheader(f"{plat} ({len(items)} criativos)")
            cols = st.columns(min(len(items), 3))
            
            for i, item in enumerate(items):
                with cols[i % 3]:
                    # Carregar e exibir imagem
                    arquivo = item.get("arquivo", "")
                    if arquivo and Path(arquivo).exists():
                        imagem = Image.open(arquivo)
                        st.image(imagem, caption=f"{item.get('id', '')}", use_container_width=True)
                        
                        # Botão para download
                        with open(arquivo, "rb") as file:
                            btn = st.download_button(
                                label="Download",
                                data=file,
                                file_name=Path(arquivo).name,
                                mime="image/png"
                            )
    else:
        st.info("Inicie o processamento para gerar criativos.")

with tab4:  # Aba de Logs
    st.header("Logs de Processamento")
    
    # Área de logs com scrolling
    st.text_area("Logs", value="\n".join(st.session_state.logs), height=400)

# Rodapé do aplicativo
st.markdown("---")

# Informações de ajuda
with st.expander("ℹ️ Informações e Solução de Problemas"):
    st.markdown("""
    ### Dicas e Solução de Problemas
    
    **Se estiver tendo problemas ao executar o aplicativo:**
    
    1. **Erro de API Key**: Verifique se sua chave da OpenAI está correta e tem saldo disponível
    2. **Erro na análise de imagem**: Tente imagens com elementos mais bem definidos e contraste adequado
    3. **Processamento lento**: Os modelos de IA podem levar alguns minutos para processar cada etapa
    4. **Erro ao carregar o app**: Certifique-se de estar usando o ambiente virtual com as dependências instaladas
    
    **Requisitos para as imagens:**
    - Arquivos PNG ou JPG
    - Elementos de design claros e bem definidos
    - Textos legíveis
    - Contrastes adequados entre elementos
    
    **Para mais informações, consulte o [README.md](https://github.com/seu-usuario/gerador-criativo-marketing/blob/main/README.md)**
    """)

st.caption("Gerador Criativo de Marketing Digital v1.0 - Desenvolvido com OpenAI e Streamlit") 