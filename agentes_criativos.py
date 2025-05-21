#!/usr/bin/env python3
"""
agentes_criativos.py
VideMarketing - Sistema de criação automatizada de anúncios usando IA.

1) Agente Compositor: Identifica a composição e entende elementos, cor, textura, texto.
2) Agente de Copy: Gera textos de alta conversão com base na composição.
3) Agente Designer: Gera imagens com instruções de composição e textos.
4) Agente Verificador: Verifica erros e insere logos.
5) Agente Editor: Permite edições nos designs criados.

Executar:
  streamlit run agentes_criativos.py
"""
import streamlit as st
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from io import BytesIO
import tempfile
import time
import re
import copy
from PIL import Image
from dotenv import load_dotenv
import requests

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Importar cliente OpenAI
from openai import OpenAI

# Configurações do aplicativo
st.set_page_config(
    page_title="VideMarketing - Criação de Anúncios",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes e configurações
MODEL_VISION = "gpt-4o-mini"  # Nosso modelo de análise visual
MODEL_TEXT = "gpt-4o-mini"    # Nosso modelo de geração de texto
MODEL_IMAGE = "gpt-image-1"   # Nosso modelo de geração de imagens

# Diretório para arquivos temporários
TEMP_DIR = Path(tempfile.gettempdir()) / "agentes_criativos"
TEMP_DIR.mkdir(exist_ok=True)

# Diretório para salvar as imagens geradas
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Carregar e inicializar cliente OpenAI
client = OpenAI()

# Inicializar estado da sessão
if "step" not in st.session_state:
    st.session_state.step = 1

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

if "composition_analysis" not in st.session_state:
    st.session_state.composition_analysis = None

if "copy_suggestions" not in st.session_state:
    st.session_state.copy_suggestions = None

if "approved_copy" not in st.session_state:
    st.session_state.approved_copy = None

if "generated_designs" not in st.session_state:
    st.session_state.generated_designs = []

if "selected_design" not in st.session_state:
    st.session_state.selected_design = None

if "final_design" not in st.session_state:
    st.session_state.final_design = None

if "logs" not in st.session_state:
    st.session_state.logs = []

# Utilitários
def log(msg):
    """Adiciona uma mensagem ao log e imprime no console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    st.session_state.logs.append(log_msg)
    print(log_msg)

def image_to_base64(path):
    """Converte uma imagem para base64"""
    data = base64.b64encode(path.read_bytes()).decode()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{data}"

def ensure_size(img_bytes, w, h):
    """Garante que a imagem tenha o tamanho especificado"""
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()

def save_temp_image(image_bytes, filename):
    """Salva uma imagem temporária no disco e retorna o caminho"""
    path = TEMP_DIR / filename
    path.write_bytes(image_bytes)
    return path

def save_output_image(image_bytes, filename):
    """Salva uma imagem na pasta de saída e retorna o caminho"""
    try:
        # Primeiro, verificar se os bytes são uma imagem válida
        img = Image.open(BytesIO(image_bytes))
        
        # Converter para RGB se necessário
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Salvar a imagem
        path = OUTPUT_DIR / filename
        img.save(path, format="PNG", quality=95)
        
        log(f"✓ Imagem salva em: {path}")
        return path
    except Exception as e:
        log(f"⚠️ Erro ao salvar imagem: {str(e)}")
        return None

def main():
    st.title("🎨 VideMarketing - Criação de Anúncios")
    
    # Sidebar com logs e configurações
    with st.sidebar:
        st.header("Configurações")
        
        # API Key (se não estiver no .env)
        api_key_env = os.getenv("OPENAI_API_KEY", "")
        if not api_key_env:
            api_key = st.text_input("Chave de API", type="password", 
                                  help="Insira sua chave de API ou configure no arquivo .env")
            if api_key:
                st.session_state.api_key = api_key
                os.environ["OPENAI_API_KEY"] = api_key
        else:
            st.success("Chave de API carregada do arquivo .env")
        
        st.divider()
        
        # Área de logs
        st.subheader("📋 Logs")
        logs_text = "\n".join(st.session_state.logs)
        st.text_area("Detalhes do Processamento", value=logs_text, height=400)
    
    # Modo de uso
    modo = st.radio(
        "Escolha o modo:",
        ["Uso direto da API", "Fluxo completo com agentes"],
        index=0,
        help="Escolha entre usar a API diretamente ou o fluxo completo com agentes"
    )
    
    # Uso direto da API
    if modo == "Uso direto da API":
        st.header("🖌️ Geração e Edição de Imagens")
        
        opcao_api = st.radio(
            "Escolha a operação:",
            ["Gerar imagem com prompt", "Editar imagem existente"],
            index=0
        )
        
        if opcao_api == "Gerar imagem com prompt":
            st.subheader("Geração de Imagem com Prompt")
            
            # Configurações
            col1, col2 = st.columns(2)
            with col1:
                tamanho = st.selectbox(
                    "Tamanho da imagem:",
                    ["1024x1024", "1024x1536", "1536x1024", "auto"],
                    index=0
                )
                
                qualidade = st.selectbox(
                    "Qualidade:",
                    ["low", "medium", "high", "auto"],
                    index=2,
                    help="low=baixa, medium=média, high=alta, auto=automática"
                )
            
            with col2:
                formato = st.selectbox(
                    "Formato de saída:",
                    ["png", "jpeg", "webp"],
                    index=0
                )
                
                background = st.selectbox(
                    "Fundo:",
                    ["normal", "transparent"],
                    index=0,
                    help="Transparente só funciona com formato PNG ou WebP"
                )
            
            # Se escolher jpeg ou webp, mostrar opção de compressão
            if formato in ["jpeg", "webp"]:
                compressao = st.slider("Nível de compressão (%)", 0, 100, 80)
            
            # Prompt para geração
            prompt = st.text_area(
                "Descreva a imagem que deseja gerar:",
                height=150,
                help="Descreva em detalhes o que deseja que seja gerado. Seja específico."
            )
            
            if st.button("Gerar Imagem", use_container_width=True) and prompt:
                with st.spinner("Gerando imagem... Isso pode levar até 2 minutos."):
                    try:
                        # Preparar parâmetros
                        params = {
                            "model": MODEL_IMAGE,
                            "prompt": prompt,
                            "size": tamanho,
                            "quality": qualidade
                        }
                        
                        # Adicionar parâmetros opcionais
                        if background == "transparent" and formato in ["png", "webp"]:
                            params["background"] = "transparent"
                        
                        if formato in ["jpeg", "webp"]:
                            params["output_format"] = formato
                            params["output_compression"] = compressao
                        
                        # Chamar API
                        log(f"Gerando imagem com prompt: '{prompt[:50]}...'")
                        result = client.images.generate(**params)
                        
                        # Processar resultado
                        if result.data and result.data[0].url:
                            try:
                                # Baixar imagem a partir da URL
                                log(f"Baixando imagem a partir da URL: {result.data[0].url}")
                                response = requests.get(result.data[0].url, timeout=30)
                                if response.status_code == 200:
                                    image_bytes = response.content
                                    
                                    # Gerar nome de arquivo
                                    timestamp = int(time.time())
                                    filename = f"vide_gen_{timestamp}.{formato}"
                                    
                                    # Salvar a imagem
                                    output_path = save_output_image(image_bytes, filename)
                                    
                                    if output_path:
                                        log(f"✓ Imagem salva em: {output_path}")
                                        st.success(f"✓ Imagem gerada com sucesso!")
                                        st.image(output_path, caption="Imagem gerada", use_container_width=True)
                                        
                                        # Botão para download
                                        with open(output_path, "rb") as f:
                                            st.download_button(
                                                label="Baixar imagem",
                                                data=f,
                                                file_name=filename,
                                                mime=f"image/{formato}",
                                                use_container_width=True
                                            )
                                    else:
                                        st.error("Falha ao salvar a imagem")
                                else:
                                    st.error(f"Falha ao baixar imagem. Status: {response.status_code}")
                            except Exception as download_error:
                                log(f"⚠️ Erro ao baixar a imagem: {str(download_error)}")
                                st.error(f"Erro ao baixar a imagem: {str(download_error)}")
                    except Exception as e:
                        log(f"⚠️ Erro ao gerar imagem: {str(e)}")
                        st.error(f"Erro ao gerar imagem: {str(e)}")
        
        else:  # Editar imagem existente
            st.subheader("Edição de Imagem Existente")
            
            # Upload de imagem
            uploaded_image = st.file_uploader(
                "Carregue a imagem para editar",
                type=["png", "jpg", "jpeg"]
            )
            
            if uploaded_image:
                st.image(uploaded_image, caption="Imagem original", use_container_width=True)
            
            # Opcional: upload de máscara para inpainting
            use_mask = st.checkbox("Usar máscara para edição seletiva", value=False)
            
            uploaded_mask = None
            if use_mask:
                uploaded_mask = st.file_uploader(
                    "Carregue a máscara (áreas transparentes serão substituídas)",
                    type=["png"]
                )
                
                st.info("A máscara deve ter o mesmo tamanho da imagem e conter um canal alfa. As áreas transparentes da máscara serão substituídas pelo novo conteúdo.")
                
                if uploaded_mask:
                    st.image(uploaded_mask, caption="Máscara para edição", use_container_width=True)
            
            # Prompt para edição
            edit_prompt = st.text_area(
                "Descreva as alterações desejadas:",
                height=100,
                help="Descreva as alterações que deseja fazer na imagem ou o resultado final desejado"
            )
            
            if uploaded_image and edit_prompt and st.button("Editar Imagem", use_container_width=True):
                with st.spinner("Editando imagem... Isso pode levar até 2 minutos."):
                    try:
                        # Salvar imagem temporariamente
                        timestamp = int(time.time())
                        img_path = TEMP_DIR / f"edit_source_{timestamp}{Path(uploaded_image.name).suffix}"
                        img_path.write_bytes(uploaded_image.getvalue())
                        
                        log(f"Editando imagem com prompt: '{edit_prompt[:50]}...'")
                        
                        # Verificar se tem máscara
                        if use_mask and uploaded_mask:
                            mask_path = TEMP_DIR / f"mask_{timestamp}.png"
                            mask_path.write_bytes(uploaded_mask.getvalue())
                            
                            # Chamar API de edição com máscara
                            result = client.images.edit(
                                model=MODEL_IMAGE,
                                image=open(img_path, "rb"),
                                mask=open(mask_path, "rb"),
                                prompt=edit_prompt
                            )
                        else:
                            # Chamar API de edição sem máscara
                            result = client.images.edit(
                                model=MODEL_IMAGE,
                                image=open(img_path, "rb"),
                                prompt=edit_prompt
                            )
                        
                        # Processar resultado
                        if result.data and result.data[0].url:
                            try:
                                # Baixar imagem a partir da URL
                                log(f"Baixando imagem a partir da URL: {result.data[0].url}")
                                response = requests.get(result.data[0].url, timeout=30)
                                if response.status_code == 200:
                                    image_bytes = response.content
                                    
                                    # Gerar nome de arquivo
                                    timestamp = int(time.time())
                                    filename = f"vide_edit_{timestamp}.png"
                                    
                                    # Salvar a imagem
                                    output_path = save_output_image(image_bytes, filename)
                                    
                                    if output_path:
                                        log(f"✓ Imagem editada salva em: {output_path}")
                                        st.success(f"✓ Imagem editada com sucesso!")
                                        
                                        # Mostrar antes e depois
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.image(uploaded_image, caption="Imagem original", use_container_width=True)
                                        with col2:
                                            st.image(output_path, caption="Imagem editada", use_container_width=True)
                                        
                                        # Botão para download
                                        with open(output_path, "rb") as f:
                                            st.download_button(
                                                label="Baixar imagem editada",
                                                data=f,
                                                file_name=filename,
                                                mime="image/png",
                                                use_container_width=True
                                            )
                                    else:
                                        st.error("Falha ao salvar a imagem editada")
                                else:
                                    st.error(f"Falha ao baixar imagem. Status: {response.status_code}")
                            except Exception as download_error:
                                log(f"⚠️ Erro ao baixar a imagem: {str(download_error)}")
                                st.error(f"Erro ao baixar a imagem: {str(download_error)}")
                    except Exception as e:
                        log(f"⚠️ Erro ao editar imagem: {str(e)}")
                        st.error(f"Erro ao editar imagem: {str(e)}")
        
        # Separador
        st.divider()
        st.markdown("Para usar o fluxo completo com múltiplos agentes de IA, selecione a opção acima.")
    
    # Fluxo completo com agentes
    else:
        st.header("🤖 Criação Inteligente com Múltiplos Agentes")
        st.markdown("Este sistema utiliza múltiplos agentes de IA para criar anúncios otimizados para conversão.")
        
        # Etapa 1: Upload da imagem de referência
        if st.session_state.step == 1:
            st.header("1️⃣ Etapa 1: Upload da imagem de referência")
            
            uploaded_file = st.file_uploader(
                "Carregue uma imagem de anúncio de referência", 
                type=["png", "jpg", "jpeg"]
            )
            
            if uploaded_file:
                st.image(uploaded_file, caption="Imagem de referência carregada", use_container_width=True)
                
                if st.button("Analisar composição", use_container_width=True):
                    with st.spinner("Analisando a composição da imagem..."):
                        # Salvar imagem no disco temporariamente
                        timestamp = int(time.time())
                        filename = f"reference_{timestamp}{Path(uploaded_file.name).suffix}"
                        img_path = TEMP_DIR / filename
                        img_path.write_bytes(uploaded_file.getvalue())
                        
                        # Armazenar na sessão
                        st.session_state.uploaded_image = str(img_path)
                        
                        # Analisar composição
                        composition = agente_compositor(img_path)
                        st.session_state.composition_analysis = composition
                        
                        # Avançar para a próxima etapa
                        st.session_state.step = 2
                        st.rerun()
        
        # Etapa 2: Escolher textos otimizados
        elif st.session_state.step == 2:
            st.header("2️⃣ Etapa 2: Escolher textos otimizados")
            
            if not st.session_state.composition_analysis:
                st.error("Análise de composição não encontrada. Por favor, volte à etapa 1.")
                if st.button("Voltar à etapa 1"):
                    st.session_state.step = 1
                    st.rerun()
            else:
                # Mostrar imagem de referência
                st.subheader("Imagem de referência")
                st.image(st.session_state.uploaded_image, width=300)
                
                # Gerar sugestões de copy se ainda não temos
                if not st.session_state.copy_suggestions:
                    with st.spinner("Gerando textos otimizados..."):
                        suggestions = agente_copy(st.session_state.composition_analysis)
                        st.session_state.copy_suggestions = suggestions
                
                # Verificar se temos sugestões
                if not st.session_state.copy_suggestions.get("suggestions", []):
                    st.warning("Não foi possível gerar sugestões de texto. Tente novamente.")
                    if st.button("Tentar novamente"):
                        st.session_state.copy_suggestions = None
                        st.rerun()
                else:
                    # Exibir sugestões para seleção
                    st.subheader("Selecione os textos para o anúncio")
                    
                    selections = {}
                    for suggestion in st.session_state.copy_suggestions.get("suggestions", []):
                        st.markdown(f"**Elemento original:** {suggestion.get('original', '')}")
                        st.markdown(f"*{suggestion.get('explanation', '')}*")
                        
                        # Criar opções de seleção
                        options = suggestion.get("alternatives", [])
                        # Adicionar texto original como opção
                        all_options = [suggestion.get("original", "(texto original)")] + options
                        
                        # Permitir seleção
                        selected = st.selectbox(
                            f"Selecione o texto para este elemento:",
                            all_options,
                            key=f"select_{suggestion.get('id', 'unknown')}"
                        )
                        
                        # Armazenar seleção
                        selections[suggestion.get("id", "")] = selected
                        
                        st.divider()
                    
                    # Botão para aprovar as seleções
                    if st.button("Confirmar seleções e gerar designs", use_container_width=True):
                        # Criar objeto de approved_copy
                        approved = {"suggestions": []}
                        for suggestion in st.session_state.copy_suggestions.get("suggestions", []):
                            approved["suggestions"].append({
                                "id": suggestion.get("id", ""),
                                "original": suggestion.get("original", ""),
                                "selected": selections.get(suggestion.get("id", ""), suggestion.get("original", ""))
                            })
                        
                        st.session_state.approved_copy = approved
                        st.session_state.step = 3
                        st.rerun()
        
        # Etapa 3: Gerar e escolher designs
        elif st.session_state.step == 3:
            st.header("3️⃣ Etapa 3: Selecionar design")
            
            if not st.session_state.approved_copy:
                st.error("Textos aprovados não encontrados. Por favor, volte à etapa 2.")
                if st.button("Voltar à etapa 2"):
                    st.session_state.step = 2
                    st.rerun()
            else:
                # Gerar designs se ainda não temos
                if not st.session_state.generated_designs:
                    with st.spinner("Gerando designs... Isso pode levar alguns minutos."):
                        designs = agente_designer(
                            st.session_state.composition_analysis,
                            st.session_state.approved_copy,
                            num_variations=4
                        )
                        st.session_state.generated_designs = designs
                
                # Verificar se temos designs
                if not st.session_state.generated_designs:
                    st.warning("Não foi possível gerar designs. Tente novamente.")
                    if st.button("Tentar novamente"):
                        st.session_state.generated_designs = []
                        st.rerun()
                else:
                    # Exibir designs para seleção
                    st.subheader("Selecione o design preferido")
                    st.markdown("Escolha um dos designs abaixo para continuar:")
                    
                    # Organizar os designs em grid
                    cols = st.columns(2)
                    for i, design in enumerate(st.session_state.generated_designs):
                        with cols[i % 2]:
                            st.image(design["path"], caption=f"Design {i+1}: Esquema {design['colors']['scheme']}", use_container_width=True)
                            if st.button(f"Selecionar Design {i+1}", key=f"select_design_{i}", use_container_width=True):
                                st.session_state.selected_design = design
                                st.session_state.step = 4
                                st.rerun()
        
        # Etapa 4: Verificação e finalização
        elif st.session_state.step == 4:
            st.header("4️⃣ Etapa 4: Verificação e finalização")
            
            if not st.session_state.selected_design:
                st.error("Design selecionado não encontrado. Por favor, volte à etapa 3.")
                if st.button("Voltar à etapa 3"):
                    st.session_state.step = 3
                    st.rerun()
            else:
                # Configurações para inserção de logo
                st.subheader("Inserir logo (opcional)")
                uploaded_logo = st.file_uploader("Carregue um logo (opcional)", type=["png", "jpg", "jpeg"])
                
                logo_path = None
                if uploaded_logo:
                    # Salvar logo temporariamente
                    timestamp = int(time.time())
                    logo_filename = f"logo_{timestamp}{Path(uploaded_logo.name).suffix}"
                    logo_path = TEMP_DIR / logo_filename
                    logo_path.write_bytes(uploaded_logo.getvalue())
                    st.image(logo_path, caption="Logo carregado", width=200)
                
                # Botão para verificar e finalizar
                if st.button("Verificar e finalizar design", use_container_width=True):
                    with st.spinner("Verificando design e finalizando..."):
                        # Executar verificação e finalização
                        final_check = agente_verificador(
                            st.session_state.selected_design["path"],
                            logo_path
                        )
                        
                        st.session_state.final_design = final_check
                        st.session_state.step = 5
                        st.rerun()
        
        # Etapa 5: Resultado final e edições
        elif st.session_state.step == 5:
            st.header("5️⃣ Etapa 5: Resultado final")
            
            if not st.session_state.final_design:
                st.error("Design final não encontrado. Por favor, volte à etapa 4.")
                if st.button("Voltar à etapa 4"):
                    st.session_state.step = 4
                    st.rerun()
            else:
                # Exibir o design final
                st.subheader("Design final")
                st.image(st.session_state.final_design["design_path"], caption="Design final", use_container_width=True)
                
                # Mostrar relatório de verificação
                st.subheader("Relatório de verificação")
                
                if st.session_state.final_design.get("has_errors", False):
                    st.warning("Foram encontrados problemas no design:")
                    for error in st.session_state.final_design.get("errors", []):
                        st.markdown(f"- **{error.get('type', '')}**: {error.get('description', '')}")
                        st.markdown(f"  *Sugestão*: {error.get('correction', '')}")
                else:
                    st.success("Nenhum problema encontrado no design!")
                
                # Exibir sugestões de melhoria
                if st.session_state.final_design.get("improvement_suggestions", []):
                    st.subheader("Sugestões de melhoria")
                    for suggestion in st.session_state.final_design.get("improvement_suggestions", []):
                        st.markdown(f"- {suggestion}")
                
                # Avaliação final
                if "final_assessment" in st.session_state.final_design:
                    st.subheader("Avaliação final")
                    st.markdown(st.session_state.final_design["final_assessment"])
                
                # Agente Editor - permitir edições
                st.subheader("Editar design")
                edits = st.text_area(
                    "Descreva as edições que deseja fazer no design:",
                    height=150,
                    placeholder="Ex: Aumentar o tamanho do texto principal, mudar a cor do botão para vermelho, adicionar uma sombra sutil..."
                )
                
                if edits and st.button("Aplicar edições", use_container_width=True):
                    with st.spinner("Aplicando edições ao design..."):
                        # Executar o agente editor
                        edit_result = agente_editor(
                            st.session_state.final_design["design_path"],
                            edits
                        )
                        
                        if edit_result["success"]:
                            # Atualizar o design final
                            st.session_state.final_design["design_path"] = edit_result["path"]
                            st.success("Edições aplicadas com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Falha ao aplicar edições: {edit_result['message']}")
                
                # Botão para download
                design_path = Path(st.session_state.final_design["design_path"])
                if design_path.exists():
                    with open(design_path, "rb") as f:
                        st.download_button(
                            label="Baixar design final",
                            data=f,
                            file_name=design_path.name,
                            mime="image/png",
                            use_container_width=True
                        )
                
                # Botão para recomeçar
                if st.button("Criar novo anúncio", use_container_width=True):
                    # Reiniciar o estado da sessão
                    st.session_state.step = 1
                    st.session_state.uploaded_image = None
                    st.session_state.composition_analysis = None
                    st.session_state.copy_suggestions = None
                    st.session_state.approved_copy = None
                    st.session_state.generated_designs = []
                    st.session_state.selected_design = None
                    st.session_state.final_design = None
                    st.rerun()

def agente_verificador(design_path, logo_path=None):
    """
    Agente Verificador: Verifica se há algum erro de português ou de sobreposição.
    Insere logo se fornecido. E finaliza o design.
    """
    log("Agente Verificador: Verificando design e finalizando")
    
    try:
        # Carregar a imagem do design
        design_img = Image.open(design_path).convert("RGBA")
        
        # Se um logo foi fornecido, inserir no design
        if logo_path and Path(logo_path).exists():
            try:
                log("Inserindo logo no design")
                logo_img = Image.open(logo_path).convert("RGBA")
                
                # Redimensionar o logo para um tamanho proporcional
                logo_width = int(design_img.width * 0.2)  # 20% da largura do design
                logo_ratio = logo_img.width / logo_img.height
                logo_height = int(logo_width / logo_ratio)
                logo_img = logo_img.resize((logo_width, logo_height), Image.LANCZOS)
                
                # Posicionar o logo no canto inferior direito
                position = (design_img.width - logo_width - 20, design_img.height - logo_height - 20)
                
                # Criar uma nova imagem com o logo inserido
                img_with_logo = design_img.copy()
                img_with_logo.paste(logo_img, position, logo_img)
                
                # Salvar o resultado
                timestamp = int(time.time())
                filename = f"design_with_logo_{timestamp}.png"
                
                # Converter para bytes
                buffered = BytesIO()
                img_with_logo.save(buffered, format="PNG", quality=95)
                image_bytes = buffered.getvalue()
                
                # Salvar usando a função save_output_image
                output_path = save_output_image(image_bytes, filename)
                
                if output_path:
                    log(f"✓ Logo inserido com sucesso em: {output_path}")
                    design_path = output_path
                    design_img = img_with_logo
                else:
                    log("⚠️ Falha ao salvar imagem com logo")
            except Exception as e:
                log(f"⚠️ Erro ao inserir logo: {str(e)}")
        
        # Converter imagem para base64 para enviar para a API
        buffered = BytesIO()
        design_img.save(buffered, format="PNG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        img_base64_url = f"data:image/png;base64,{img_base64}"
        
        # Verificar erros de português e sobreposição
        prompt = """
        Analise cuidadosamente esta imagem de anúncio digital e verifique:

        1. ERROS DE PORTUGUÊS:
           - Verifique todos os textos visíveis quanto a erros ortográficos
           - Verifique concordância verbal e nominal
           - Verifique uso correto de pontuação
           - Identifique abreviações incorretas ou inconsistentes

        2. PROBLEMAS DE LEGIBILIDADE E SOBREPOSIÇÃO:
           - Verifique se há texto sobreposto a elementos visuais que dificultam a leitura
           - Verifique se há texto cortado ou parcialmente visível
           - Verifique se há contraste insuficiente entre texto e fundo
           - Identifique problemas de espaçamento ou alinhamento que afetam a legibilidade

        FORMATE SUA RESPOSTA COMO JSON:
        {
          "has_errors": true/false,
          "errors": [
            {
              "type": "português/sobreposição/legibilidade",
              "description": "descrição detalhada do erro encontrado",
              "location": "onde no anúncio o erro foi encontrado",
              "correction": "sugestão de correção"
            }
          ],
          "improvement_suggestions": [
            "sugestão 1 para melhorar o design",
            "sugestão 2 para melhorar o design"
          ],
          "final_assessment": "avaliação geral da qualidade do anúncio e sua eficácia potencial"
        }
        """
        
        res = client.chat.completions.create(
            model=MODEL_VISION,
            messages=[
                {"role": "system", "content": "Você é um especialista em revisão de design e copywriting para marketing digital."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_base64_url}}
                ]}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = res.choices[0].message.content
        
        try:
            # Tentar parsear diretamente como JSON
            result = json.loads(content)
            log("✓ Verificação concluída com sucesso")
            
            # Se houver erros, adicionar ao log
            if result.get("has_errors", False):
                log(f"⚠️ Encontrados {len(result.get('errors', []))} problemas no design")
                for error in result.get("errors", []):
                    log(f"  - {error.get('type', '')}: {error.get('description', '')}")
            else:
                log("✓ Nenhum problema encontrado no design")
            
            # Adicionar informações ao resultado
            result["design_path"] = design_path
            
            return result
        
        except json.JSONDecodeError as e:
            log(f"⚠️ Erro ao decodificar JSON da verificação: {str(e)}")
            
            # Tentar extrair apenas a parte JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)
                    log("✓ JSON de verificação extraído com sucesso da resposta parcial")
                    result["design_path"] = design_path
                    return result
                except json.JSONDecodeError:
                    log("⚠️ Falha ao extrair JSON da verificação")
            
            # Se falhar, retornar resultado básico
            return {
                "has_errors": False,
                "errors": [],
                "improvement_suggestions": [],
                "final_assessment": "Verificação automática não disponível",
                "design_path": design_path
            }
    
    except Exception as e:
        log(f"⚠️ Erro no Agente Verificador: {str(e)}")
        return {
            "has_errors": False,
            "errors": [],
            "improvement_suggestions": [],
            "final_assessment": f"Erro durante a verificação: {str(e)}",
            "design_path": design_path
        }

def agente_editor(design_path, edits):
    """
    Agente Editor: Permite edições nos designs criados.
    """
    log("Agente Editor: Aplicando edições ao design")
    
    try:
        # Ler a imagem original
        design_img = Image.open(design_path).convert("RGBA")
        img_width, img_height = design_img.size
        
        # Criar um arquivo temporário para a imagem
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # Salvar a imagem no arquivo temporário
            design_img.save(temp_file.name, format="PNG")
            temp_file.flush()
            
            # Construir o prompt com as instruções de edição
            prompt = f"""
            Edite esta imagem de anúncio com as seguintes alterações:
            
            {edits}
            
            INSTRUÇÕES IMPORTANTES:
            - Mantenha a mesma resolução e proporção da imagem original ({img_width}x{img_height})
            - Preserve a estrutura geral do design e a hierarquia visual
            - Mantenha a identidade visual e estilo original
            - Aplique APENAS as alterações especificadas acima
            - Garanta que o resultado final mantém a qualidade profissional do original
            """
            
            log("Enviando solicitação de edição para a API")
            
            # Preparar a imagem para envio correto
            try:
                # Abrir o arquivo temporário em modo binário e ler seu conteúdo
                with open(temp_file.name, 'rb') as image_file:
                    # Preparar a imagem com formato explícito para garantir compatibilidade MIME
                    image_data = image_file.read()
                    
                    # Verificar se precisamos converter a imagem
                    try:
                        # Tentar enviar diretamente para a API
                        res = client.images.edit(
                            model=MODEL_IMAGE,
                            image=open(temp_file.name, 'rb'),  # Reabrir o arquivo
                            prompt=prompt,
                            n=1,
                            size=f"{img_width}x{img_height}"
                        )
                    except Exception as img_error:
                        log(f"Erro no envio direto da imagem: {str(img_error)}. Tentando método alternativo...")
                        
                        # Se falhar, tentar método alternativo: salvar em outro formato
                        alt_img = Image.open(BytesIO(image_data))
                        
                        # Converter para RGB (remover transparência) se necessário
                        if alt_img.mode == 'RGBA':
                            background = Image.new('RGB', alt_img.size, (255, 255, 255))
                            background.paste(alt_img, mask=alt_img.split()[3])  # 3 é o canal alfa
                            alt_img = background
                        
                        # Salvar em outro arquivo temporário em formato alternativo
                        with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as alt_temp:
                            alt_img.save(alt_temp.name, format="JPEG", quality=95)
                            alt_temp.flush()
                            
                            # Tentar novamente com o novo formato
                            res = client.images.edit(
                                model=MODEL_IMAGE,
                                image=open(alt_temp.name, 'rb'),
                                prompt=prompt,
                                n=1,
                                size=f"{img_width}x{img_height}"
                            )
                            
                            # Limpar arquivo temporário alternativo
                            os.unlink(alt_temp.name)
            except Exception as e:
                log(f"Todas as tentativas de edição falharam: {str(e)}")
                return {
                    "success": False,
                    "path": design_path,
                    "message": f"Falha ao editar imagem: {str(e)}"
                }
            
            # Remover o arquivo temporário original
            os.unlink(temp_file.name)
            
            if res.data and res.data[0].b64_json:
                # Decodificar a imagem
                image_base64 = res.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                
                # Gerar nome de arquivo
                timestamp = int(time.time())
                filename = f"design_edited_{timestamp}.png"
                
                # Salvar a imagem
                output_path = save_output_image(image_bytes, filename)
                
                if output_path:
                    log(f"✓ Design editado com sucesso: {output_path}")
                    return {
                        "success": True,
                        "path": str(output_path),
                        "message": "Edições aplicadas com sucesso"
                    }
                else:
                    log("⚠️ Falha ao salvar imagem editada")
                    return {
                        "success": False,
                        "path": design_path,
                        "message": "Falha ao salvar imagem editada"
                    }
            else:
                log("⚠️ Falha ao editar o design: resposta vazia da API")
                return {
                    "success": False,
                    "path": design_path,
                    "message": "Falha ao aplicar edições: resposta vazia da API"
                }
    
    except Exception as e:
        log(f"⚠️ Erro no Agente Editor: {str(e)}")
        return {
            "success": False,
            "path": design_path,
            "message": f"Erro ao aplicar edições: {str(e)}"
        }

def agente_compositor(img_path):
    """
    Agente Compositor: Identifica a composição e entende elementos, cor, textura, texto.
    """
    log("Agente Compositor: Analisando a composição da imagem")
    try:
        b64 = image_to_base64(img_path)
        
        prompt = """
        Analise esta imagem de forma EXTREMAMENTE DETALHADA e extraia:
        
        1. Dimensões exatas em pixels
        2. Elementos principais com descrições precisas:
           - Textos: conteúdo exato, fonte, peso, alinhamento, cor e hierarquia visual
           - Formas: tipo exato (retângulo, círculo, etc.), cor, opacidade, borda
           - Imagens/Ícones: descrição detalhada, função comunicativa
           - Logotipos: descrição completa, posicionamento
           - Botões: formato, cantos, sombras, efeitos
        3. Cores:
           - Código hexadecimal exato de TODAS as cores
           - Relações entre cores (primária, secundária, destaque)
           - Gradientes, transparências ou efeitos especiais
        4. Layout e composição:
           - Alinhamentos exatos (superior, inferior, centro)
           - Margens e espaçamentos precisos
           - Grids ou estruturas perceptíveis
           - Hierarquia visual e fluxo de leitura
        5. Estilos visuais:
           - Estilo tipográfico (serifa, sans-serif, espessura)
           - Elementos decorativos
           - Texturização ou tratamentos especiais
           - Estilo global (minimalista, corporativo, colorido, etc.)
        6. Texturas e efeitos de iluminação:
           - Tipos de texturas por elemento (gradiente, metálico, plano, mármore, etc.)
           - Direção e intensidade das texturas
           - Efeitos de luz e sombra (especular, brilho suave, reflexo)
           - Tratamentos de superfície (fosco, brilhante, acetinado)
        
        MUITO IMPORTANTE: Sua resposta deve ser um objeto JSON válido com a estrutura especificada abaixo. 
        Não inclua explicações, comentários ou texto adicional fora do objeto JSON.
        
        {
            "canvas_size": {"w": W, "h": H},
            "placeholders": [
                {
                    "id": "1", 
                    "type": "text", 
                    "value": "texto exato", 
                    "bbox": [x, y, w, h], 
                    "font": {
                        "color": "#HEX",
                        "size": N,
                        "family": "tipo da fonte",
                        "weight": "peso", 
                        "alignment": "alinhamento", 
                        "style": "estilo"
                    },
                    "layer": 1,
                    "description": "descrição detalhada da função deste texto",
                    "visual_hierarchy": "primário/secundário/terciário"
                },
                {
                    "id": "2", 
                    "type": "shape", 
                    "shape_type": "retângulo/círculo/etc",
                    "value": "#HEX", 
                    "bbox": [x, y, w, h],
                    "opacity": 1.0,
                    "border": {"color": "#HEX", "width": N},
                    "corners": "arredondado/reto",
                    "shadow": true/false,
                    "layer": 0,
                    "description": "função desta forma na composição",
                    "texture": {
                        "type": "flat/gradient/metallic/glossy/marble/etc",
                        "colors": ["#HEX1", "#HEX2"],
                        "direction": "diagonal/vertical/radial",
                        "intensity": "low/medium/high"
                    }
                }
            ],
            "color_palette": {
                "primary": "#HEX",
                "secondary": "#HEX",
                "accent": "#HEX",
                "text": "#HEX",
                "background": "#HEX",
                "all_colors": ["#HEX1", "#HEX2", "#HEX3", "#HEX4"]
            },
            "textures": {
                "background": {
                    "type": "flat/gradient/pattern",
                    "colors": ["#HEX1", "#HEX2"],
                    "direction": "top-to-bottom/radial/diagonal",
                    "intensity": "low/medium/high"
                },
                "primary_elements": {
                    "type": "glossy/metallic/matte/marble",
                    "colors": ["#HEX1", "#HEX2"],
                    "effect": "descrição do efeito visual"
                },
                "buttons": {
                    "type": "flat/glossy/gradient",
                    "colors": ["#HEX1", "#HEX2"]
                }
            },
            "lighting": {
                "main": {
                    "type": "ambient/specular/soft-glow",
                    "position": "top-right/center/etc",
                    "intensity": "low/medium/high",
                    "effect": "descrição do efeito visual"
                },
                "highlights": {
                    "targets": ["ID-1", "ID-2"],
                    "effect": "descrição do efeito de destaque"
                }
            }
        }
        """
        
        # Primeira tentativa com temperatura 0 para máxima precisão
        res = client.chat.completions.create(
            model=MODEL_VISION,
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em análise de design visual e composição de imagens."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": b64}}
                ]}
            ],
            temperature=0,
            response_format={"type": "json_object"}  # Forçar formato JSON
        )
        
        content = res.choices[0].message.content
        
        try:
            # Tentar parsear diretamente como JSON
            result = json.loads(content)
            log("✓ Análise da composição concluída com sucesso")
            return result
        except json.JSONDecodeError as e:
            log(f"⚠️ Erro ao decodificar JSON da análise: {str(e)}")
            
            # Tentar extrair apenas a parte JSON da resposta
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)
                    log("✓ JSON de análise extraído com sucesso da resposta parcial")
                    return result
                except json.JSONDecodeError:
                    log("⚠️ Falha ao extrair JSON da análise")
            
            # Se ainda falhar, retornar um template básico
            log("⚠️ Usando template básico de análise")
            img = Image.open(img_path)
            w, h = img.size
            return {
                "canvas_size": {"w": w, "h": h},
                "placeholders": [],
                "color_palette": {
                    "primary": "#800080",
                    "secondary": "#FFFFFF",
                    "accent": "#FFA500",
                    "text": "#000000",
                    "background": "#FFFFFF",
                    "all_colors": ["#800080", "#FFFFFF", "#FFA500", "#000000"]
                }
            }
    except Exception as e:
        log(f"⚠️ Erro no Agente Compositor: {str(e)}")
        img = Image.open(img_path)
        w, h = img.size
        return {
            "canvas_size": {"w": w, "h": h},
            "placeholders": [],
            "color_palette": {
                "primary": "#800080",
                "secondary": "#FFFFFF",
                "accent": "#FFA500",
                "text": "#000000",
                "background": "#FFFFFF",
                "all_colors": ["#800080", "#FFFFFF", "#FFA500", "#000000"]
            }
        }

# Implementação do Agente Copy
def agente_copy(analysis):
    # Implemente a lógica para gerar textos otimizados com base na análise
    # Esta é uma implementação básica e pode ser melhorada com base nas suas necessidades
    return {
        "suggestions": [
            {
                "id": "1",
                "original": "Texto original 1",
                "explanation": "Explicação do texto original 1",
                "alternatives": ["Alternativa 1 para o texto original 1", "Alternativa 2 para o texto original 1"]
            },
            {
                "id": "2",
                "original": "Texto original 2",
                "explanation": "Explicação do texto original 2",
                "alternatives": ["Alternativa 1 para o texto original 2", "Alternativa 2 para o texto original 2"]
            }
        ]
    }

# Implementação do Agente Designer
def agente_designer(composition_analysis, approved_copy, num_variations=4):
    # Implemente a lógica para gerar designs com base na análise da composição e nos textos otimizados
    # Esta é uma implementação básica e pode ser melhorada com base nas suas necessidades
    designs = []
    for i in range(num_variations):
        design = {
            "path": f"design_{i+1}.png",
            "colors": {
                "scheme": f"Esquema {i+1}",
                "primary": "#800080",
                "secondary": "#FFFFFF",
                "accent": "#FFA500",
                "text": "#000000",
                "background": "#FFFFFF"
            }
        }
        designs.append(design)
    return designs

# Alias para compatibilidade (caso ainda haja referências a agente_composer)
agente_composer = agente_compositor

if __name__ == "__main__":
    main() 