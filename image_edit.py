#!/usr/bin/env python3
"""
image_edit.py
Interface Streamlit simplificada para edição de imagens usando GPT-image-1

Executar:
  streamlit run image_edit.py
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
import time

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Importar cliente OpenAI
from openai import OpenAI

# Configurações do aplicativo
st.set_page_config(
    page_title="Editor de Imagens IA",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Diretório para arquivos temporários
TEMP_DIR = Path(tempfile.gettempdir()) / "image_edit"
TEMP_DIR.mkdir(exist_ok=True)

# Diretório para salvar as imagens geradas
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Inicializar o estado da sessão
if "uploaded_images" not in st.session_state:
    st.session_state.uploaded_images = []

if "prompt" not in st.session_state:
    st.session_state.prompt = ""

if "result_image" not in st.session_state:
    st.session_state.result_image = None

if "logs" not in st.session_state:
    st.session_state.logs = []

# Função para registrar logs
def log(msg):
    st.session_state.logs.append(msg)
    st.session_state.logs = st.session_state.logs[-50:]  # Manter apenas os últimos 50 logs

# Função para salvar imagem temporária
def save_temp_image(image_bytes, filename):
    """Salva uma imagem temporária no disco e retorna o caminho"""
    path = TEMP_DIR / filename
    path.write_bytes(image_bytes)
    return path

# Função para processar as imagens e gerar a edição
def generate_edited_image():
    # Verificar se existem imagens carregadas
    if not st.session_state.uploaded_images:
        st.error("Por favor, carregue pelo menos uma imagem de referência.")
        return False
    
    # Verificar se há prompt
    if not st.session_state.prompt:
        st.error("Por favor, forneça um prompt de edição.")
        return False
    
    # Verificar se a API key está disponível
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        api_key = st.session_state.get("api_key", "")
        if not api_key:
            st.error("API Key da OpenAI não encontrada. Por favor, insira manualmente ou configure no arquivo .env")
            return False
    
    # Inicializar cliente OpenAI
    client = OpenAI(api_key=api_key)
    
    try:
        with st.spinner("Gerando imagem editada..."):
            # Carregar imagens como arquivos binários
            image_files = []
            for img in st.session_state.uploaded_images:
                # Se for um objeto UploadedFile, usar diretamente
                if hasattr(img, 'read'):
                    image_files.append(img)
                # Se for um caminho de arquivo, abrir o arquivo
                else:
                    image_path = Path(img)
                    if image_path.exists():
                        image_files.append(open(image_path, "rb"))
            
            log(f"Enviando {len(image_files)} imagens para processamento")
            log(f"Prompt: {st.session_state.prompt}")
            
            # Chamar a API para edição de imagem
            result = client.images.edit(
                model="gpt-image-1",
                image=image_files,
                prompt=st.session_state.prompt,
            )
            
            # Fechar arquivos abertos se necessário
            for img in image_files:
                if hasattr(img, 'close') and not hasattr(img, 'name'):  # Se for um arquivo aberto manualmente
                    img.close()
            
            # Processar o resultado
            if result.data and result.data[0].b64_json:
                log("Imagem gerada com sucesso")
                
                # Converter base64 para bytes
                image_base64 = result.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                
                # Gerar nome de arquivo com timestamp atual
                temp_filename = f"edited_image_{int(time.time())}.png"
                temp_path = save_temp_image(image_bytes, temp_filename)
                
                # Salvar em outputs para referência futura
                output_path = OUTPUT_DIR / temp_filename
                output_path.write_bytes(image_bytes)
                
                log(f"Imagem salva em {output_path}")
                
                # Armazenar resultado para exibição
                st.session_state.result_image = {
                    "bytes": image_bytes,
                    "path": str(output_path)
                }
                
                return True
            else:
                st.error("Não foi possível gerar a imagem. Verifique as imagens de referência e o prompt.")
                return False
    
    except Exception as e:
        st.error(f"Erro durante o processamento: {str(e)}")
        log(f"Erro: {str(e)}")
        return False

# Interface do usuário
st.title("🖼️ Editor de Imagens com IA")

st.markdown("""
Este aplicativo permite editar e combinar imagens usando o modelo GPT-image-1 da OpenAI.
Faça upload de imagens de referência e forneça um prompt descritivo do resultado desejado.
""")

# Sidebar para configurações
with st.sidebar:
    st.header("Configurações")
    
    # API Key (se não estiver no .env)
    api_key_env = os.getenv("OPENAI_API_KEY", "")
    if not api_key_env:
        api_key = st.text_input("OpenAI API Key", type="password", 
                               help="Insira sua chave de API da OpenAI ou configure no arquivo .env")
        if api_key:
            st.session_state.api_key = api_key
            os.environ["OPENAI_API_KEY"] = api_key
    else:
        st.success("API Key carregada do arquivo .env")
    
    st.subheader("Exemplos de Prompts")
    
    prompt_examples = [
        "Gere uma imagem fotorrealista de uma cesta de presentes em fundo branco rotulada 'Relax & Unwind', com uma fita e fonte manuscrita, contendo todos os itens nas imagens de referência.",
        "Combine todas as imagens de referência em uma única composição artística no estilo de uma natureza morta renascentista.",
        "Crie uma cena de produto comercial profissional mostrando todos os itens das imagens de referência organizados elegantemente.",
        "Transforme os objetos das imagens de referência em uma única ilustração coesa no estilo cartoon minimalista."
    ]
    
    selected_example = st.selectbox("Exemplos de prompts", 
                                   options=["Selecione um exemplo..."] + prompt_examples,
                                   index=0)
    
    if selected_example != "Selecione um exemplo...":
        if st.button("Usar este exemplo"):
            st.session_state.prompt = selected_example

# Área principal
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Imagens de Referência")
    
    # Upload de múltiplas imagens
    uploaded_files = st.file_uploader("Carregar imagens de referência", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        st.session_state.uploaded_images = uploaded_files
        
        # Mostrar as imagens carregadas
        st.write(f"{len(uploaded_files)} imagens carregadas:")
        image_cols = st.columns(min(3, len(uploaded_files)))
        
        for i, img_file in enumerate(uploaded_files):
            with image_cols[i % 3]:
                st.image(img_file, caption=f"Imagem {i+1}", use_container_width=True)
    
    st.subheader("Prompt de Edição")
    
    # Área de texto para o prompt
    prompt = st.text_area("Descreva o resultado desejado", 
                         value=st.session_state.prompt,
                         height=150, 
                         help="Seja específico sobre como você deseja que as imagens sejam combinadas ou editadas")
    
    if prompt:
        st.session_state.prompt = prompt
    
    # Botão para processar
    if st.button("Gerar Imagem Editada", use_container_width=True):
        generate_edited_image()

with col2:
    st.subheader("Resultado")
    
    if st.session_state.result_image:
        # Exibir a imagem gerada
        result_image = st.session_state.result_image
        image = Image.open(BytesIO(result_image["bytes"]))
        st.image(image, caption="Imagem Gerada", use_container_width=True)
        
        # Botão para download
        st.download_button(
            label="Baixar Imagem",
            data=result_image["bytes"],
            file_name=Path(result_image["path"]).name,
            mime="image/png"
        )
    else:
        st.info("A imagem editada aparecerá aqui após o processamento.")

# Área de logs
with st.expander("📋 Logs"):
    st.text_area("Detalhes do Processamento", value="\n".join(st.session_state.logs), height=200)

# Informações de ajuda
with st.expander("ℹ️ Como Usar"):
    st.markdown("""
    ### Instruções de Uso
    
    1. **Carregue imagens de referência**: Faça upload de até 4 imagens que você deseja combinar ou editar.
    2. **Escreva um prompt detalhado**: Descreva exatamente como você deseja que as imagens sejam combinadas ou alteradas.
    3. **Clique em "Gerar Imagem Editada"**: Aguarde enquanto a IA processa sua solicitação.
    4. **Baixe o resultado**: Após a geração, você pode visualizar e baixar a imagem resultante.
    
    ### Dicas para Melhores Resultados
    
    - Use imagens com fundos limpos para melhor integração
    - Seja específico sobre posicionamento, estilo e aparência desejada
    - Para melhores resultados, limite o número de imagens de entrada (2-4 geralmente é ideal)
    - Resoluções mais altas produzem resultados mais detalhados
    """)

st.caption("Editor de Imagens com IA v1.0 - Desenvolvido com OpenAI GPT-image-1 e Streamlit") 