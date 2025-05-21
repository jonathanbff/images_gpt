#!/usr/bin/env python3
"""
agentes_criativos.py
Sistema de criação de anúncios com múltiplos agentes especializados.

1) Agente Composer: Identifica a composição e entende elementos, cor, textura, texto.
2) Agente de Copy: Gera textos de alta conversão com base na composição.
3) Agente Designer: Gera imagens com instruções de composição e textos.
4) Agente Double Checker: Verifica erros e insere logos.
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
    page_title="Sistema de Criação de Anúncios",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes e configurações
MODEL_VISION = "gpt-4o-mini"
MODEL_TEXT = "gpt-4o-mini"
MODEL_IMAGE = "gpt-image-1"

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

# Interface principal
st.title("🎨 Sistema de Criação de Anúncios")

# Sidebar com logs e configurações
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
    
    st.divider()
    
    # Área de logs
    st.subheader("📋 Logs")
    logs_text = "\n".join(st.session_state.logs)
    st.text_area("Detalhes do Processamento", value=logs_text, height=400)

# Implementação do Agente Composer
def agente_composer(img_path):
    """
    Agente Composer: Identifica a composição e entende elementos, cor, textura, texto.
    """
    log("Agente Composer: Analisando a composição da imagem")
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
        log(f"⚠️ Erro no Agente Composer: {str(e)}")
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

# Implementação do Agente de Copy
def agente_copy(composition_analysis):
    """
    Agente de Copy: Gera textos de alta conversão com base na composição analisada.
    """
    log("Agente de Copy: Gerando textos de alta conversão")
    
    try:
        # Extrair elementos de texto da análise
        text_elements = []
        for p in composition_analysis.get("placeholders", []):
            if p.get("type") == "text" and "value" in p:
                text_elements.append({
                    "id": p.get("id", ""),
                    "text": p.get("value", ""),
                    "description": p.get("description", ""),
                    "visual_hierarchy": p.get("visual_hierarchy", "")
                })
        
        # Se não houver elementos de texto, retornar mensagem de erro
        if not text_elements:
            log("⚠️ Nenhum elemento de texto encontrado na análise")
            return {
                "error": "Nenhum elemento de texto encontrado na análise",
                "suggestions": []
            }
        
        prompt = f"""
        Como especialista em copywriting para marketing digital, gere textos de alta conversão 
        para substituir os textos originais neste layout, mantendo a função comunicativa 
        e hierarquia visual de cada elemento.
        
        ELEMENTOS DE TEXTO ORIGINAIS:
        {json.dumps(text_elements, indent=2, ensure_ascii=False)}
        
        INSTRUÇÕES:
        1. Analise a função comunicativa de cada elemento de texto
        2. Mantenha o mesmo comprimento aproximado (número de caracteres/palavras)
        3. Preserve a hierarquia visual (textos primários, secundários, etc.)
        4. Crie textos otimizados para alta conversão em marketing digital
        5. Adapte o tom e estilo para marketing persuasivo e ação imediata
        6. Foque em benefícios claros, urgência e chamadas para ação direta
        
        Para cada elemento, gere 3 variações alternativas que:
        - Aumentem o apelo emocional e desejo do produto/serviço
        - Comuniquem valor e benefícios de forma clara e impactante
        - Reduzam fricção para a ação desejada (compra, cadastro, etc.)
        - Mantenham a identidade e propósito do anúncio original
        
        FORMATE SUA RESPOSTA COMO JSON:
        {{
          "suggestions": [
            {{
              "id": "ID_DO_ELEMENTO",
              "original": "texto original",
              "alternatives": [
                "primeira alternativa de alta conversão",
                "segunda alternativa de alta conversão",
                "terceira alternativa de alta conversão"
              ],
              "explanation": "breve explicação da estratégia de copywriting aplicada"
            }},
            ... mais elementos ...
          ]
        }}
        """
        
        res = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[
                {"role": "system", "content": "Você é um especialista em copywriting para marketing digital com foco em alta conversão."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        content = res.choices[0].message.content
        
        try:
            # Tentar parsear diretamente como JSON
            result = json.loads(content)
            log("✓ Sugestões de copy geradas com sucesso")
            return result
        except json.JSONDecodeError as e:
            log(f"⚠️ Erro ao decodificar JSON das sugestões de copy: {str(e)}")
            
            # Tentar extrair apenas a parte JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)
                    log("✓ JSON de sugestões de copy extraído com sucesso da resposta parcial")
                    return result
                except json.JSONDecodeError:
                    log("⚠️ Falha ao extrair JSON das sugestões de copy")
        
        # Se falhar, criar sugestões básicas
        basic_suggestions = {"suggestions": []}
        for elem in text_elements:
            basic_suggestions["suggestions"].append({
                "id": elem["id"],
                "original": elem["text"],
                "alternatives": [
                    f"Versão otimizada 1: {elem['text']}",
                    f"Versão otimizada 2: {elem['text']}",
                    f"Versão otimizada 3: {elem['text']}"
                ],
                "explanation": "Alternativas otimizadas para maior conversão"
            })
        
        log("ℹ️ Usando sugestões básicas de copy")
        return basic_suggestions
    
    except Exception as e:
        log(f"⚠️ Erro no Agente de Copy: {str(e)}")
        return {
            "error": f"Erro ao gerar sugestões de copy: {str(e)}",
            "suggestions": []
        } 

# Implementação do Agente Compositor Detalhado
def agente_compositor_detalhado(composition_analysis, approved_copy, colors):
    """
    Agente compositor detalhado: Cria um prompt extremamente descritivo para o design
    baseado na análise da composição e nos textos aprovados.
    """
    log("Agente Compositor Detalhado: Criando prompt estruturado e detalhado")
    
    try:
        # Função para variar o matiz das cores
        def shift_hue(hex_color, degrees):
            """Desloca o matiz de uma cor em X graus no círculo cromático"""
            hex_color = hex_color.lstrip('#')
            
            try:
                # Converter hexadecimal para RGB
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                
                # Converter RGB para HSL
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                h, s, l = 0, 0, (max_val + min_val) / 2
                
                if max_val == min_val:
                    h, s = 0, 0  # acromático
                else:
                    d = max_val - min_val
                    s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
                    
                    if max_val == r:
                        h = (g - b) / d + (6 if g < b else 0)
                    elif max_val == g:
                        h = (b - r) / d + 2
                    else:
                        h = (r - g) / d + 4
                    
                    h /= 6
                
                # Ajustar matiz
                h = (h + degrees/360) % 1
                
                # Converter de volta para RGB
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
                
                # Converter de volta para hexadecimal
                return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            except Exception:
                # Em caso de erro, retornar a cor original
                return f"#{hex_color}"
        
        # Extrair dimensões da imagem
        canvas_size = composition_analysis.get("canvas_size", {"w": 1024, "h": 1536})
        width, height = canvas_size.get("w", 1024), canvas_size.get("h", 1536)
        
        # Extrair elementos de texto aprovados
        text_replacements = {}
        for suggestion in approved_copy.get("suggestions", []):
            text_id = suggestion.get("id", "")
            selected_text = suggestion.get("selected", "")
            if text_id and selected_text:
                text_replacements[text_id] = selected_text
        
        # Aplicar textos aprovados aos elementos originais (preservando posição e estilo)
        text_elements = []
        shape_elements = []
        
        for p in composition_analysis.get("placeholders", []):
            if p.get("type") == "text":
                element = copy.deepcopy(p)
                if p.get("id") in text_replacements:
                    element["value"] = text_replacements[p.get("id")]
                text_elements.append(element)
            elif p.get("type") == "shape":
                shape_elements.append(copy.deepcopy(p))
        
        # Criar descrição da paleta de cores com base na análise original
        color_palette = composition_analysis.get("color_palette", {})
        all_colors = color_palette.get("all_colors", [colors["primary"], colors["secondary"], colors["accent"]])
        
        # Combinação das cores originais com as cores variadas
        color_description = f"""
PALETA DE CORES (baseada na imagem original):
- Cor primária: {colors['primary']} (mantendo o esquema cromático da análise original)
- Cor secundária: {colors['secondary']}
- Cor de destaque: {colors['accent']}
- Cores adicionais da imagem original: {', '.join(all_colors[:5])}
- Cor de texto principal: {color_palette.get('text', '#1F1F1F')}
- Cor de fundo principal: {color_palette.get('background', colors['secondary'])}
"""
        
        # Detalhes de texturas da imagem original
        textures = composition_analysis.get("textures", {})
        if textures:
            color_description += "\nTEXTURAS (baseadas na imagem original):\n"
            for texture_name, texture_info in textures.items():
                texture_type = texture_info.get("type", "flat")
                texture_colors = texture_info.get("colors", [])
                texture_direction = texture_info.get("direction", "none")
                
                color_description += f"- {texture_name}: tipo {texture_type}"
                if texture_colors:
                    color_description += f", cores {', '.join(texture_colors[:3])}"
                if texture_direction != "none":
                    color_description += f", direção {texture_direction}"
                color_description += "\n"
        
        # Criar descrição de layout fiel à imagem original
        layout_description = "LAYOUT E ESTRUTURA (reproduzindo a imagem original):\n"
        
        # Mapeamento de regiões ocupadas para determinar o layout
        regions = {
            "top": [], "middle": [], "bottom": [],
            "left": [], "center": [], "right": []
        }
        
        # Analisar todos os elementos para determinar a distribuição no layout
        all_elements = text_elements + shape_elements
        for elem in all_elements:
            bbox = elem.get("bbox", [0, 0, 0, 0])
            elem_center_x = bbox[0] + bbox[2]/2
            elem_center_y = bbox[1] + bbox[3]/2
            
            # Classificar verticalmente
            if elem_center_y < height * 0.33:
                regions["top"].append(elem)
            elif elem_center_y < height * 0.66:
                regions["middle"].append(elem)
            else:
                regions["bottom"].append(elem)
                
            # Classificar horizontalmente
            if elem_center_x < width * 0.33:
                regions["left"].append(elem)
            elif elem_center_x < width * 0.66:
                regions["center"].append(elem)
            else:
                regions["right"].append(elem)
        
        # Descrever a distribuição dos elementos
        layout_description += "- Distribuição de elementos mantida fiel à imagem original:\n"
        
        for region_name, elems in regions.items():
            if elems:
                element_types = []
                for e in elems:
                    if e.get("type") == "text":
                        element_types.append(f"texto '{e.get('value', '')}'" if len(e.get('value', '')) < 30 else f"texto '{e.get('value', '')[:30]}...'")
                    else:
                        element_types.append(f"{e.get('shape_type', 'forma')} {e.get('value', '')}")
                
                layout_description += f"  * Região {region_name}: {len(elems)} elementos ({', '.join(element_types[:3])})\n"
        
        # Analisar fundos e estruturas principais
        background_info = composition_analysis.get("textures", {}).get("background", {})
        background_type = background_info.get("type", "flat")
        
        if background_type == "gradient" or background_type == "radial-gradient":
            layout_description += f"""
- Fundo com {background_type}:
  * Cores: {', '.join(background_info.get('colors', [colors['primary'], shift_hue(colors['primary'], -30)]))}
  * Direção: {background_info.get('direction', 'top-to-bottom')}
"""
        elif background_type == "pattern":
            layout_description += f"""
- Fundo com padrão do tipo {background_info.get('type', 'geométrico')}:
  * Cores: {', '.join(background_info.get('colors', [colors['primary'], colors['secondary']]))}
"""
        else:
            # Identificar se existem formas grandes que funcionam como seções
            large_shapes = [s for s in shape_elements if (s.get("bbox", [0,0,0,0])[2] > width*0.5 and s.get("bbox", [0,0,0,0])[3] > height*0.2)]
            
            if large_shapes:
                layout_description += "- Estrutura com seções de cores distintas:\n"
                for i, shape in enumerate(large_shapes):
                    bbox = shape.get("bbox", [0, 0, 0, 0])
                    position_y = (bbox[1] + bbox[3]/2) / height
                    position_str = "superior" if position_y < 0.33 else "central" if position_y < 0.66 else "inferior"
                    shape_color = shape.get("value", colors["primary"])
                    
                    layout_description += f"  * Seção {position_str}: forma {shape.get('shape_type', 'retângulo')} na cor {shape_color}\n"
            else:
                layout_description += f"""
- Fundo principal na cor {color_palette.get('background', colors['secondary'])}
- Elementos distribuídos de acordo com a hierarquia visual original
"""
        
        # Descrição detalhada de cada elemento de texto preservando posições originais
        text_description = "ELEMENTOS DE TEXTO (mantendo posições exatas da imagem original):\n"
        
        for i, text in enumerate(text_elements):
            value = text.get("value", "")
            font = text.get("font", {})
            color = font.get("color", "#000000")
            size = font.get("size", 16)
            weight = font.get("weight", "regular")
            alignment = font.get("alignment", "center")
            visual_hierarchy = text.get("visual_hierarchy", "")
            bbox = text.get("bbox", [0, 0, 0, 0])
            
            # Determinar posicionamento exato
            x_pos = bbox[0]
            y_pos = bbox[1]
            width_percent = int((bbox[2] / width) * 100)
            x_center_percent = int(((bbox[0] + bbox[2]/2) / width) * 100)
            y_center_percent = int(((bbox[1] + bbox[3]/2) / height) * 100)
            
            # Descrição de posicionamento preciso
            position_desc = f"posição exata a {x_center_percent}% da largura e {y_center_percent}% da altura"
            if x_center_percent < 33:
                position_desc += ", alinhado à esquerda"
            elif x_center_percent > 66:
                position_desc += ", alinhado à direita"
            else:
                position_desc += ", centralizado horizontalmente"
                
            # Determinar estilo de destaque baseado na análise original
            highlight_style = f"tamanho {size}px, peso {weight}, alinhamento {alignment}"
            highlight_style += f", na cor {color}"
            
            if visual_hierarchy == "primary":
                highlight_style = f"destaque principal, {highlight_style}"
            elif visual_hierarchy == "secondary":
                highlight_style = f"destaque secundário, {highlight_style}"
            
            # Adicionar descrição do texto com posicionamento preciso
            text_description += f"""
- Texto "{value}":
  * {position_desc}
  * Estilo: {highlight_style}
  * Largura aproximada: {width_percent}% da largura total
  * Preservar exatamente essa hierarquia visual
"""
        
        # Descrição de elementos visuais originais (formas, botões, etc.)
        visual_elements = "ELEMENTOS VISUAIS (da imagem original):\n"
        
        # Identificar e descrever elementos com funções específicas
        buttons = []
        containers = []
        decorative = []
        
        for shape in shape_elements:
            shape_type = shape.get("shape_type", "rectangle")
            value = shape.get("value", "")  # cor
            bbox = shape.get("bbox", [0, 0, 0, 0])
            width_percent = int((bbox[2] / width) * 100)
            height_percent = int((bbox[3] / height) * 100)
            x_center_percent = int(((bbox[0] + bbox[2]/2) / width) * 100)
            y_center_percent = int(((bbox[1] + bbox[3]/2) / height) * 100)
            
            # Posicionamento exato
            position_desc = f"posição a {x_center_percent}% da largura e {y_center_percent}% da altura"
            
            # Classificar o elemento pela função aparente
            if height_percent < 15 and width_percent < 50 and width_percent > 15:
                buttons.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
            elif width_percent > 50 and height_percent > 20:
                containers.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
            else:
                decorative.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
        
        # Descrever botões
        if buttons:
            visual_elements += "- Botões (preservar exatamente como na imagem original):\n"
            for i, btn in enumerate(buttons):
                shape = btn["shape"]
                visual_elements += f"""
  * Botão {i+1}: {shape.get('shape_type', 'retângulo')} na cor {shape.get('value', '#CCCCCC')}
    - {btn['position']}
    - Tamanho: {btn['width']}% × {btn['height']}% da tela
    - Cantos: {shape.get('corners', 'arredondados')}
    - Opacidade: {shape.get('opacity', 1.0)}
    - {shape.get('texture', {}).get('type', 'flat')}
"""
        
        # Descrever containers
        if containers:
            visual_elements += "- Containers/Seções principais:\n"
            for i, cont in enumerate(containers):
                shape = cont["shape"]
                visual_elements += f"""
  * Container {i+1}: {shape.get('shape_type', 'retângulo')} na cor {shape.get('value', '#FFFFFF')}
    - {cont['position']}
    - Tamanho: {cont['width']}% × {cont['height']}% da tela
    - Cantos: {shape.get('corners', 'arredondados')}
    - Opacidade: {shape.get('opacity', 1.0)}
    - Conteúdo posicionado conforme layout original
"""
        
        # Descrever elementos decorativos
        if decorative:
            visual_elements += "- Elementos decorativos/gráficos:\n"
            for i, dec in enumerate(decorative):
                shape = dec["shape"]
                visual_elements += f"""
  * Elemento {i+1}: {shape.get('shape_type', 'forma')} na cor {shape.get('value', '#CCCCCC')}
    - {dec['position']}
    - Tamanho: {dec['width']}% × {dec['height']}% da tela
"""
        
        # Descrever efeitos especiais e iluminação da imagem original
        lighting = composition_analysis.get("lighting", {})
        effects_description = "EFEITOS VISUAIS E ACABAMENTO (da imagem original):\n"
        
        if lighting:
            main_light = lighting.get("main", {})
            effects_description += f"""
- Iluminação principal: tipo {main_light.get('type', 'ambient')}
  * Posição: {main_light.get('position', 'top-right')}
  * Intensidade: {main_light.get('intensity', 'medium')}
  * Efeito: {main_light.get('effect', 'adds depth to the composition')}

- Efeitos de destaque: {lighting.get('highlights', {}).get('effect', 'subtle glow on key elements')}
"""
        
        effects_description += """
- Aplique sombras suaves nos textos principais para garantir legibilidade perfeita
- Adicione profundidade com micro-sombras em elementos sobrepostos
- Inclua reflexos sutis em superfícies (botões, caixas) para aparência profissional
- Mantenha consistência nos estilos de fonte e espaçamentos
- Reserve espaço limpo para inserção posterior de logo na parte inferior
"""
        
        # Combinar todas as seções em um prompt completo, mantendo fidelidade ao original
        prompt = f"""
Crie uma imagem no formato vertical, com dimensões exatas de {width}x{height} pixels, que reproduza fielmente o layout da imagem original analisada, seguindo estas especificações detalhadas:

PALETA DE CORES:
- Cor primária: {colors['primary']} (use para elementos principais, áreas de destaque e textos importantes)
- Cor secundária: {colors['secondary']} (use para fundos, áreas neutras e elementos de suporte)
- Cor de destaque/acento: {colors['accent']} (use para botões, ícones e elementos interativos)
- Cor de texto principal: {color_palette.get('text', '#1F1F1F')} (para textos de alta legibilidade)
- Cor de texto secundário: #5A5A5A (para textos legais e menos importantes)

ESTRUTURA DO FUNDO:
{layout_description}

ELEMENTOS DE TEXTO (posicionados exatamente como na imagem original):
{text_description}

ELEMENTOS VISUAIS (reproduzindo fielmente os elementos da imagem original):
{visual_elements}

COMPONENTES ESPECÍFICOS E DETALHES INTERNOS:
{len(card_elements) > 0 and f"""
CARTÃO DE CRÉDITO/DÉBITO:
- Posicionado exatamente como na imagem original
- Textura de mármore fluido, misturando tons de {colors['primary']}, {shift_hue(colors['primary'], 20)} e {shift_hue(colors['primary'], 40)}
- Detalhes realistas: chip dourado ou prateado com circuitos visíveis, símbolo de contactless com ondas
- Números impressos em alto relevo com fonte específica para cartões (divididos em grupos de 4, formato: 5678 **** **** 1234)
- Data de validade no formato MM/AA na posição correta abaixo do número principal
- Logo da bandeira (Visa/Mastercard/Elo/American Express) no canto inferior direito
- Nome do cliente em fonte específica (não preencher com texto real, usar "NOME DO CLIENTE")
- Brilho especular vindo do topo direito criando reflexos na superfície
- Rotação suave para visual dinâmico (manter ângulo exatamente como na imagem original)
- Sombra realista abaixo do cartão com desfoque suave para sensação de profundidade
- Borda fina mais clara ao redor de todo o cartão para efeito de separação com o fundo
""" or ""}

{len(button_elements) > 0 and f"""
BOTÕES:
- Botões com cantos perfeitamente arredondados (raio de 8-12px)
- Botão principal (CTA) na cor {colors['accent']} com texto em branco ou {colors['secondary']}
- Estilo 3D sutilmente elevado com pequeno gradiente vertical (mais claro no topo)
- Botões secundários em {shift_hue(colors['primary'], 30)} ou em cinza claro (#E0E0E0)
- Efeito de pressão com sombra interna nos botões selecionados
- Textura glossy sutil nos botões com reflexo horizontal na parte superior
- Borda fina mais clara (1px) no topo e esquerda, e mais escura na direita e base
- Sombra externa muito suave (2-3px de desfoque, opacidade 20%)
- Texto centralizado com padding horizontal adequado (pelo menos 20px de cada lado)
- Ícone opcional alinhado ao texto (se existir na imagem original)
""" or ""}

{len(slider_elements) > 0 and f"""
SLIDER/CONTROLE DESLIZANTE:
- Trilho horizontal com textura metálica elegante em cinza gradiente (#CCCCCC até #999999)
- Altura exata do trilho como na imagem original (geralmente 4-6px)
- Botão deslizante (thumb) circular ou oval na cor {colors['primary']} com tamanho exato como original
- Área preenchida do trilho (à esquerda do thumb) com gradiente na cor {colors['primary']} até {shift_hue(colors['primary'], 20)}
- Leve sombra no botão deslizante para sensação de elevação (1-2px offset, 3-4px blur)
- Efeito de brilho interno no thumb para aparência premium
- Marcadores de valor (ticks) abaixo do trilho, se presentes na imagem original
- Valores numéricos exatos nos extremos (mínimo/máximo) como na imagem original
- Posição do thumb mantida exatamente como na referência
""" or ""}

{len(chart_elements) > 0 and f"""
GRÁFICOS FINANCEIROS:
- Reproduza exatamente o mesmo tipo de gráfico da imagem original (barras, linhas, pizza, etc.)
- Utilize as cores primária {colors['primary']} e de destaque {colors['accent']} para os dados principais
- Para gráficos de linha: linha suave com gradiente abaixo dela, partindo da cor principal até transparente
- Para gráficos de barra: barras com cantos arredondados e sutil gradiente vertical
- Para gráficos de pizza: bordas refinadas entre segmentos e leve efeito 3D
- Legendas ou labels exatamente como na imagem original, com fonte legível e nítida
- Valores numéricos precisos conforme original, alinhados adequadamente
- Grid de fundo sutil quando presente na imagem original (linhas cinza claro #EEEEEE)
- Sombra muito suave sob todo o gráfico para destacá-lo do fundo
- Manter todos os elementos de interação visíveis na imagem original (tooltips, pontos de dados destacados)
""" or ""}

{len(icon_elements) > 0 and f"""
ÍCONES:
- Ícones minimalistas e modernos na cor {colors['primary']} ou {colors['accent']}
- Estilo consistente entre todos os ícones (flat, outline, duotone ou solid)
- Ícones financeiros específicos quando relevantes:
  * Cifrão/símbolo monetário com design clean para representar dinheiro/pagamento
  * Carteira ou cartão para pagamentos e transações
  * Gráfico ascendente para investimentos ou crescimento
  * Escudo para segurança financeira
  * Relógio/calendário para prazos e pagamentos
  * Porcentagem para taxas de juros
  * Casa para financiamento imobiliário
  * Mãos para empréstimos ou suporte
- Tamanho e posicionamento exatos como na imagem original
- Leve brilho ou sombra quando destacados no design original
""" or ""}

{len(container_elements) > 0 and f"""
CAIXAS/CONTÊINERES:
- Contêineres com cantos arredondados precisos (raio de 12-16px, ou exatamente como original)
- Fundo em {colors['secondary']} com gradiente muito sutil para evitar aparência plana
- Borda refinada de 1-2px mais escura ou mais clara conforme design original
- Sombra externa suave para efeito flutuante (4-6px blur, 30% opacidade)
- Organização interna do conteúdo mantendo espaçamento e alinhamento da imagem original
- Linhas separadoras horizontais entre seções quando presentes (cor #E0E0E0, 1px)
- Headers internos destacados com texto em negrito ou cor contrastante
- Parte superior possivelmente mais escura/destacada quando usado como cabeçalho
- Espaçamento interno (padding) consistente, geralmente 16-24px
- Elementos específicos (ícones, botões) posicionados precisamente como na referência
""" or ""}

{"""
ELEMENTOS FINANCEIROS ESPECÍFICOS:
- Simuladores de valor: caixas com valores monetários destacados em fonte grande e negrito
  * Cifrão/símbolo monetário alinhado corretamente (precedendo o valor ou sobrescrito)
  * Valores decimais em tamanho menor ou cor mais clara quando presentes
  * Rótulos explicativos posicionados acima ou ao lado dos valores

- Taxas de juros: valores percentuais destacados com símbolo "%" claro
  * Texto explicativo complementar como "ao mês" ou "ao ano" em tamanho menor
  * Cores contrastantes para diferenciar taxas promocionais ou condições especiais

- Prazos e parcelas: combinação de números e texto com hierarquia clara
  * Número de parcelas em destaque quando relevante (ex: "12x")
  * Valor da parcela com símbolo monetário em formato padronizado
  * Prazo total do financiamento/empréstimo quando aplicável

- Quadro de benefícios: lista de vantagens com ícones associados
  * Marcadores visuais consistentes (check, bullet points, etc.)
  * Espaçamento igual entre itens da lista
  * Ícones alinhados verticalmente à esquerda do texto

- Formulários ou campos: áreas para preenchimento com aparência interativa
  * Cantos arredondados e borda sutil
  * Labels posicionados consistentemente (acima ou dentro do campo)
  * Campos obrigatórios com marcação visual quando identificáveis
  * Botão de submissão alinhado e destacado com a cor primária ou de destaque
"""}

EFEITOS E ACABAMENTO:
- Iluminação principal vinda da direção superior direita
- Aplique sombras suaves aos elementos principais para criar profundidade
- Textos principais devem ter sombras sutis para garantir legibilidade em qualquer fundo
- Botões devem ter efeito de pressão/clique com sombra interna suave
- Caixas e contêineres devem ter sombra suave para simular elevação
- Elementos de destaque devem ter brilho sutil (glow) para atrair atenção
- Mantenha consistência nos estilos de fonte em toda a composição
- Aplique texturas sutis em áreas grandes para evitar aparência plana
- Reserve espaço limpo na parte inferior para inserção posterior de logo

INSTRUÇÕES ESPECÍFICAS DE COMPOSIÇÃO:
- Posicione todos os elementos EXATAMENTE nas mesmas posições relativas da imagem original
- Mantenha a hierarquia visual e o fluxo de leitura da imagem original
- Preserve os espaçamentos e margens entre elementos como na imagem analisada
- Mantenha proporções exatas como especificado ({width}x{height} pixels)
- Garanta PERFEITA legibilidade de todos os textos com contraste adequado
- Se a imagem original tiver seções distintas de cor, reproduza-as fielmente
- Os tamanhos e pesos das fontes devem seguir a hierarquia da imagem original
- Botões e elementos interativos devem ser claramente identificáveis
- Elementos decorativos devem complementar o layout sem disputar atenção
- Áreas de respiro (espaço em branco) devem ser mantidas para equilíbrio visual

IMPORTANTE: Este não é um layout genérico. A composição final deve ser IDÊNTICA à imagem original analisada, apenas com as cores e textos atualizados conforme especificado acima. Todos os elementos, suas posições, tamanhos relativos e hierarquia visual devem ser reproduzidos com máxima fidelidade.
"""
        
        log("✓ Prompt detalhado baseado na imagem original criado com sucesso")
        return prompt
        
    except Exception as e:
        log(f"⚠️ Erro no Agente Compositor Detalhado: {str(e)}")
        
        # Retornar um prompt básico em caso de erro
        return f"""
Crie uma imagem de anúncio digital profissional que REPRODUZA o layout da imagem original analisada, com dimensões exatas de {width}x{height} pixels.

Use a seguinte paleta de cores:
- Cor primária: {colors['primary']}
- Cor secundária: {colors['secondary']}
- Cor de destaque: {colors['accent']}

IMPORTANTE: Mantenha o mesmo layout e posicionamento de elementos da imagem original.
Garanta que todos os textos sejam perfeitamente legíveis.
Reserve espaço na parte inferior para inserção posterior de logo.
"""

# Implementação do Agente Designer
def agente_designer(composition_analysis, approved_copy, num_variations=4):
    """
    Agente Designer: Gera imagens com as instruções da composição e o texto aprovado.
    Gera no mínimo 4 variações de criativos.
    """
    log(f"Agente Designer: Gerando {num_variations} variações de design baseadas na imagem original")
    
    try:
        # Verificar se temos uma análise válida da imagem original
        if not composition_analysis or not composition_analysis.get("placeholders"):
            log("⚠️ Análise da imagem original insuficiente ou inválida")
            log("Análise detectada: " + str(composition_analysis)[:200] + "...")
        else:
            log(f"✓ Análise válida da imagem original detectada com {len(composition_analysis.get('placeholders', []))} elementos")
        
        # Extrair dimensões da imagem
        canvas_size = composition_analysis.get("canvas_size", {"w": 1024, "h": 1536})
        original_width, original_height = canvas_size.get("w", 1024), canvas_size.get("h", 1536)
        
        # Definir tamanho fixo para a API
        width, height = 1024, 1536
        
        log(f"Tamanho original: {original_width}x{original_height} (proporção: {original_width/original_height:.2f})")
        log(f"Tamanho ajustado: {width}x{height} (proporção: {width/height:.2f})")
        
        # Extrair paleta de cores
        colors = composition_analysis.get("color_palette", {})
        if not colors:
            colors = {
                "primary": "#800080",
                "secondary": "#FFFFFF",
                "accent": "#FFA500",
                "text": "#000000",
                "background": "#FFFFFF",
                "all_colors": ["#800080", "#FFFFFF", "#FFA500", "#000000"]
            }
        
        # Garantir os campos mínimos para cada cor
        primary_color = colors.get("primary", "#800080")
        secondary_color = colors.get("secondary", "#FFFFFF")
        accent_color = colors.get("accent", "#FFA500")
        
        # Função para gerar variações de cor
        def shift_hue(hex_color, degrees):
            """Desloca o matiz de uma cor em X graus no círculo cromático"""
            hex_color = hex_color.lstrip('#')
            
            try:
                # Converter hexadecimal para RGB
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                
                # Converter RGB para HSL
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                h, s, l = 0, 0, (max_val + min_val) / 2
                
                if max_val == min_val:
                    h, s = 0, 0  # acromático
                else:
                    d = max_val - min_val
                    s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
                    
                    if max_val == r:
                        h = (g - b) / d + (6 if g < b else 0)
                    elif max_val == g:
                        h = (b - r) / d + 2
                    else:
                        h = (r - g) / d + 4
                    
                    h /= 6
                
                # Ajustar matiz
                h = (h + degrees/360) % 1
                
                # Converter de volta para RGB
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
                
                # Converter de volta para hexadecimal
                return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            except Exception:
                # Em caso de erro, retornar a cor original
                return f"#{hex_color}"
        
        # Gerar esquemas de cores variados para cada design
        color_variations = []
        for i in range(num_variations):
            if i == 0:  # Primeira variação - cores originais
                color_variations.append({
                    "primary": primary_color,
                    "secondary": secondary_color,
                    "accent": accent_color,
                    "scheme": "original"
                })
            elif i == 1:  # Segunda variação - cores análogas
                color_variations.append({
                    "primary": shift_hue(primary_color, 30),
                    "secondary": shift_hue(secondary_color, 15),
                    "accent": shift_hue(accent_color, -15),
                    "scheme": "análogo"
                })
            elif i == 2:  # Terceira variação - cores complementares
                color_variations.append({
                    "primary": shift_hue(primary_color, 180),
                    "secondary": secondary_color,
                    "accent": shift_hue(accent_color, -30),
                    "scheme": "complementar"
                })
            else:  # Variações adicionais
                color_variations.append({
                    "primary": shift_hue(primary_color, 60 * i),
                    "secondary": shift_hue(secondary_color, 30 * i),
                    "accent": shift_hue(accent_color, -45 * i),
                    "scheme": f"variação {i}"
                })
        
        # Gerar prompts para cada variação usando o agente compositor detalhado
        design_prompts = []
        generated_designs = []
        
        for i, colors in enumerate(color_variations):
            # Usar o agente compositor prompts avançados para criar o prompt ultra-detalhado
            log(f"Gerando prompt ultra-detalhado para variação {i+1}, reproduzindo fielmente o layout original com novas cores")
            prompt = agente_compositor_prompts_avancados(composition_analysis, approved_copy, colors)
            
            # Refinar o prompt para garantir máxima fidelidade ao layout original
            refined_prompt = f"""
{prompt}

EXTREMAMENTE IMPORTANTE:
- Esta imagem DEVE reproduzir o LAYOUT EXATO da imagem original analisada
- Mantenha todos os elementos em suas POSIÇÕES EXATAS como na imagem original
- Não invente novos elementos, use APENAS os que existem na análise original
- Mantenha FIELMENTE as proporções e tamanhos relativos de todos os elementos
- O resultado deve ser idêntico à referência original, apenas com as cores e textos atualizados
- NÃO modifique a estrutura, composição ou distribuição dos elementos em relação à imagem original
- Textos devem ocupar o mesmo espaço e posição que na imagem original
"""
            
            design_prompts.append(refined_prompt)
        
        # Gerar designs para cada variação
        for i, prompt in enumerate(design_prompts):
            try:
                log(f"Gerando design variação {i+1} com esquema de cores {color_variations[i]['scheme']}")
                
                # Usar configurações ótimas para fidelidade e qualidade
                res = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    n=1,
                    size=f"{width}x{height}",
                    quality="high"        # Usar alta qualidade para máxima nitidez
                )
                
                if res.data and res.data[0].url:
                    try:
                        # A API retorna uma URL, precisamos baixar a imagem
                        log(f"Baixando imagem a partir da URL: {res.data[0].url}")
                        response = requests.get(res.data[0].url, timeout=30)
                        if response.status_code == 200:
                            image_bytes = response.content
                            
                            # Gerar nome de arquivo
                            timestamp = int(time.time())
                            filename = f"design_v{i+1}_{timestamp}.png"
                            
                            # Salvar a imagem
                            output_path = save_output_image(image_bytes, filename)
                            
                            if output_path:
                                # Adicionar ao resultado
                                generated_designs.append({
                                    "id": f"v{i+1}",
                                    "filename": filename,
                                    "path": str(output_path),
                                    "colors": color_variations[i],
                                    "bytes": image_bytes
                                })
                                
                                log(f"✓ Design variação {i+1} gerado com sucesso")
                            else:
                                log(f"⚠️ Falha ao salvar design variação {i+1}")
                        else:
                            log(f"⚠️ Falha ao baixar imagem da URL. Status code: {response.status_code}")
                    except Exception as download_error:
                        log(f"⚠️ Erro ao baixar imagem da URL: {str(download_error)}")
                elif res.data and res.data[0].b64_json:
                    # Caso a API ainda retorne b64_json
                    image_base64 = res.data[0].b64_json
                    image_bytes = base64.b64decode(image_base64)
                    
                    # Gerar nome de arquivo
                    timestamp = int(time.time())
                    filename = f"design_v{i+1}_{timestamp}.png"
                    
                    # Salvar a imagem
                    output_path = save_output_image(image_bytes, filename)
                    
                    if output_path:
                        # Adicionar ao resultado
                        generated_designs.append({
                            "id": f"v{i+1}",
                            "filename": filename,
                            "path": str(output_path),
                            "colors": color_variations[i],
                            "bytes": image_bytes
                        })
                        
                        log(f"✓ Design variação {i+1} gerado com sucesso")
                    else:
                        log(f"⚠️ Falha ao salvar design variação {i+1}")
                else:
                    log(f"⚠️ Falha ao gerar design variação {i+1}")
            
            except Exception as e:
                log(f"⚠️ Erro ao gerar design variação {i+1}: {str(e)}")
        
        # Verificar se temos pelo menos algumas variações
        if not generated_designs:
            log("⚠️ Nenhum design foi gerado com sucesso")
            return []
        
        log(f"✓ Total de {len(generated_designs)} designs gerados com sucesso")
        return generated_designs
    
    except Exception as e:
        log(f"⚠️ Erro no Agente Designer: {str(e)}")
        return [] 

# Implementação do Agente Double Checker
def agente_double_checker(design_path, logo_path=None):
    """
    Agente Double Checker: Verifica se há algum erro de português ou de sobreposição.
    Insere logo se fornecido. E finaliza o design.
    """
    log("Agente Double Checker: Verificando design e finalizando")
    
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
        log(f"⚠️ Erro no Agente Double Checker: {str(e)}")
        return {
            "has_errors": False,
            "errors": [],
            "improvement_suggestions": [],
            "final_assessment": f"Erro durante a verificação: {str(e)}",
            "design_path": design_path
        } 

# Implementação do Agente Editor
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

# Implementação do Agente Compositor Prompts Avançados
def agente_compositor_prompts_avancados(composition_analysis, approved_copy, colors):
    """
    Cria prompts extremamente detalhados e estruturados para geração de imagens
    usando técnicas avançadas de prompt engineering.
    """
    log("Agente Compositor Prompts Avançados: Criando prompt ultra-detalhado")
    
    try:
        # Função para gerar variações de cor
        def shift_hue(hex_color, degrees):
            """Desloca o matiz de uma cor em X graus no círculo cromático"""
            hex_color = hex_color.lstrip('#')
            
            try:
                # Converter hexadecimal para RGB
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                
                # Converter RGB para HSL
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                h, s, l = 0, 0, (max_val + min_val) / 2
                
                if max_val == min_val:
                    h, s = 0, 0  # acromático
                else:
                    d = max_val - min_val
                    s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
                    
                    if max_val == r:
                        h = (g - b) / d + (6 if g < b else 0)
                    elif max_val == g:
                        h = (b - r) / d + 2
                    else:
                        h = (r - g) / d + 4
                    
                    h /= 6
                
                # Ajustar matiz
                h = (h + degrees/360) % 1
                
                # Converter de volta para RGB
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
                
                # Converter de volta para hexadecimal
                return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            except Exception:
                # Em caso de erro, retornar a cor original
                return f"#{hex_color}"
                
        # Extrair dimensões da imagem
        canvas_size = composition_analysis.get("canvas_size", {"w": 1024, "h": 1536})
        width, height = canvas_size.get("w", 1024), canvas_size.get("h", 1536)
        
        # Extrair elementos de texto aprovados
        text_replacements = {}
        for suggestion in approved_copy.get("suggestions", []):
            text_id = suggestion.get("id", "")
            selected_text = suggestion.get("selected", "")
            if text_id and selected_text:
                text_replacements[text_id] = selected_text
        
        # Aplicar textos aprovados aos elementos originais (preservando posição e estilo)
        text_elements = []
        shape_elements = []
        
        for p in composition_analysis.get("placeholders", []):
            if p.get("type") == "text":
                element = copy.deepcopy(p)
                if p.get("id") in text_replacements:
                    element["value"] = text_replacements[p.get("id")]
                text_elements.append(element)
            elif p.get("type") == "shape":
                shape_elements.append(copy.deepcopy(p))

        # Análise avançada de elementos visuais e seus componentes internos
        # Identificar e categorizar elementos visuais específicos
        card_elements = []
        button_elements = []
        container_elements = []
        slider_elements = []
        icon_elements = []
        illustration_elements = []
        chart_elements = []
        divider_elements = []
        
        # Função para detectar o tipo mais provável de um elemento visual
        def detect_element_type(shape):
            shape_type = shape.get("shape_type", "rectangle").lower()
            description = shape.get("description", "").lower()
            bbox = shape.get("bbox", [0, 0, 0, 0])
            width_ratio = bbox[2] / width
            height_ratio = bbox[3] / height
            aspect_ratio = bbox[2] / bbox[3] if bbox[3] > 0 else 1
            
            # Palavras-chave para categorização
            card_keywords = ["cartão", "card", "crédito", "débito", "visa", "mastercard", "payment"]
            button_keywords = ["botão", "button", "cta", "call to action", "clique", "selecione"]
            slider_keywords = ["slider", "seletor", "controle deslizante", "barra de seleção"]
            chart_keywords = ["gráfico", "chart", "diagrama", "plot"]
            icon_keywords = ["ícone", "icon", "símbolo", "pictograma"]
            
            # Detectar cartões
            if any(kw in description for kw in card_keywords) or (1.4 < aspect_ratio < 1.8 and 0.2 < width_ratio < 0.7):
                return "card"
            
            # Detectar botões
            if any(kw in description for kw in button_keywords) or (shape_type == "rectangle" and "rounded" in shape.get("corners", "") and 0.1 < width_ratio < 0.5 and height_ratio < 0.1):
                return "button"
            
            # Detectar sliders
            if any(kw in description for kw in slider_keywords) or (shape_type == "rectangle" and width_ratio > 0.4 and height_ratio < 0.05):
                return "slider"
            
            # Detectar contêineres/painéis
            if shape_type == "rectangle" and width_ratio > 0.5 and height_ratio > 0.1:
                return "container"
            
            # Detectar ícones
            if any(kw in description for kw in icon_keywords) or (width_ratio < 0.1 and height_ratio < 0.1 and aspect_ratio < 2):
                return "icon"
            
            # Detectar ilustrações
            if "ilustração" in description or "illustration" in description or (width_ratio > 0.15 and aspect_ratio < 3):
                return "illustration"
            
            # Detectar gráficos
            if any(kw in description for kw in chart_keywords):
                return "chart"
            
            # Detectar divisores
            if shape_type == "rectangle" and width_ratio > 0.3 and height_ratio < 0.01:
                return "divider"
            
            # Elemento genérico
            return "generic"
        
        # Categorizar os elementos visuais
        for shape in shape_elements:
            element_type = detect_element_type(shape)
            
            if element_type == "card":
                card_elements.append(shape)
            elif element_type == "button":
                button_elements.append(shape)
            elif element_type == "container":
                container_elements.append(shape)
            elif element_type == "slider":
                slider_elements.append(shape)
            elif element_type == "icon":
                icon_elements.append(shape)
            elif element_type == "illustration":
                illustration_elements.append(shape)
            elif element_type == "chart":
                chart_elements.append(shape)
            elif element_type == "divider":
                divider_elements.append(shape)
        
        # Criar descrição da paleta de cores com base na análise original
        color_palette = composition_analysis.get("color_palette", {})
        all_colors = color_palette.get("all_colors", [colors["primary"], colors["secondary"], colors["accent"]])
        
        # Combinação das cores originais com as cores variadas
        color_description = f"""
PALETA DE CORES (baseada na imagem original):
- Cor primária: {colors['primary']} (mantendo o esquema cromático da análise original)
- Cor secundária: {colors['secondary']}
- Cor de destaque: {colors['accent']}
- Cores adicionais da imagem original: {', '.join(all_colors[:5])}
- Cor de texto principal: {color_palette.get('text', '#1F1F1F')}
- Cor de fundo principal: {color_palette.get('background', colors['secondary'])}
"""
        
        # Detalhes de texturas da imagem original
        textures = composition_analysis.get("textures", {})
        if textures:
            color_description += "\nTEXTURAS (baseadas na imagem original):\n"
            for texture_name, texture_info in textures.items():
                texture_type = texture_info.get("type", "flat")
                texture_colors = texture_info.get("colors", [])
                texture_direction = texture_info.get("direction", "none")
                
                color_description += f"- {texture_name}: tipo {texture_type}"
                if texture_colors:
                    color_description += f", cores {', '.join(texture_colors[:3])}"
                if texture_direction != "none":
                    color_description += f", direção {texture_direction}"
                color_description += "\n"
        
        # Criar descrição de layout fiel à imagem original
        layout_description = "LAYOUT E ESTRUTURA (reproduzindo a imagem original):\n"
        
        # Mapeamento de regiões ocupadas para determinar o layout
        regions = {
            "top": [], "middle": [], "bottom": [],
            "left": [], "center": [], "right": []
        }
        
        # Analisar todos os elementos para determinar a distribuição no layout
        all_elements = text_elements + shape_elements
        for elem in all_elements:
            bbox = elem.get("bbox", [0, 0, 0, 0])
            elem_center_x = bbox[0] + bbox[2]/2
            elem_center_y = bbox[1] + bbox[3]/2
            
            # Classificar verticalmente
            if elem_center_y < height * 0.33:
                regions["top"].append(elem)
            elif elem_center_y < height * 0.66:
                regions["middle"].append(elem)
            else:
                regions["bottom"].append(elem)
                
            # Classificar horizontalmente
            if elem_center_x < width * 0.33:
                regions["left"].append(elem)
            elif elem_center_x < width * 0.66:
                regions["center"].append(elem)
            else:
                regions["right"].append(elem)
        
        # Descrever a distribuição dos elementos
        layout_description += "- Distribuição de elementos mantida fiel à imagem original:\n"
        
        for region_name, elems in regions.items():
            if elems:
                element_types = []
                for e in elems:
                    if e.get("type") == "text":
                        element_types.append(f"texto '{e.get('value', '')}'" if len(e.get('value', '')) < 30 else f"texto '{e.get('value', '')[:30]}...'")
                    else:
                        element_types.append(f"{e.get('shape_type', 'forma')} {e.get('value', '')}")
                
                layout_description += f"  * Região {region_name}: {len(elems)} elementos ({', '.join(element_types[:3])})\n"
        
        # Analisar fundos e estruturas principais
        background_info = composition_analysis.get("textures", {}).get("background", {})
        background_type = background_info.get("type", "flat")
        
        if background_type == "gradient" or background_type == "radial-gradient":
            layout_description += f"""
- Fundo com {background_type}:
  * Cores: {', '.join(background_info.get('colors', [colors['primary'], shift_hue(colors['primary'], -30)]))}
  * Direção: {background_info.get('direction', 'top-to-bottom')}
"""
        elif background_type == "pattern":
            layout_description += f"""
- Fundo com padrão do tipo {background_info.get('type', 'geométrico')}:
  * Cores: {', '.join(background_info.get('colors', [colors['primary'], colors['secondary']]))}
"""
        else:
            # Identificar se existem formas grandes que funcionam como seções
            large_shapes = [s for s in shape_elements if (s.get("bbox", [0,0,0,0])[2] > width*0.5 and s.get("bbox", [0,0,0,0])[3] > height*0.2)]
            
            if large_shapes:
                layout_description += "- Estrutura com seções de cores distintas:\n"
                for i, shape in enumerate(large_shapes):
                    bbox = shape.get("bbox", [0, 0, 0, 0])
                    position_y = (bbox[1] + bbox[3]/2) / height
                    position_str = "superior" if position_y < 0.33 else "central" if position_y < 0.66 else "inferior"
                    shape_color = shape.get("value", colors["primary"])
                    
                    layout_description += f"  * Seção {position_str}: forma {shape.get('shape_type', 'retângulo')} na cor {shape_color}\n"
            else:
                layout_description += f"""
- Fundo principal na cor {color_palette.get('background', colors['secondary'])}
- Elementos distribuídos de acordo com a hierarquia visual original
"""
        
        # Descrição detalhada de cada elemento de texto preservando posições originais
        text_description = "ELEMENTOS DE TEXTO (mantendo posições exatas da imagem original):\n"
        
        for i, text in enumerate(text_elements):
            value = text.get("value", "")
            font = text.get("font", {})
            color = font.get("color", "#000000")
            size = font.get("size", 16)
            weight = font.get("weight", "regular")
            alignment = font.get("alignment", "center")
            visual_hierarchy = text.get("visual_hierarchy", "")
            bbox = text.get("bbox", [0, 0, 0, 0])
            
            # Determinar posicionamento exato
            x_pos = bbox[0]
            y_pos = bbox[1]
            width_percent = int((bbox[2] / width) * 100)
            x_center_percent = int(((bbox[0] + bbox[2]/2) / width) * 100)
            y_center_percent = int(((bbox[1] + bbox[3]/2) / height) * 100)
            
            # Descrição de posicionamento preciso
            position_desc = f"posição exata a {x_center_percent}% da largura e {y_center_percent}% da altura"
            if x_center_percent < 33:
                position_desc += ", alinhado à esquerda"
            elif x_center_percent > 66:
                position_desc += ", alinhado à direita"
            else:
                position_desc += ", centralizado horizontalmente"
                
            # Determinar estilo de destaque baseado na análise original
            highlight_style = f"tamanho {size}px, peso {weight}, alinhamento {alignment}"
            highlight_style += f", na cor {color}"
            
            if visual_hierarchy == "primary":
                highlight_style = f"destaque principal, {highlight_style}"
            elif visual_hierarchy == "secondary":
                highlight_style = f"destaque secundário, {highlight_style}"
            
            # Adicionar descrição do texto com posicionamento preciso
            text_description += f"""
- Texto "{value}":
  * {position_desc}
  * Estilo: {highlight_style}
  * Largura aproximada: {width_percent}% da largura total
  * Preservar exatamente essa hierarquia visual
"""
        
        # Descrição de elementos visuais originais (formas, botões, etc.)
        visual_elements = "ELEMENTOS VISUAIS (da imagem original):\n"
        
        # Identificar e descrever elementos com funções específicas
        buttons = []
        containers = []
        decorative = []
        
        for shape in shape_elements:
            shape_type = shape.get("shape_type", "rectangle")
            value = shape.get("value", "")  # cor
            bbox = shape.get("bbox", [0, 0, 0, 0])
            width_percent = int((bbox[2] / width) * 100)
            height_percent = int((bbox[3] / height) * 100)
            x_center_percent = int(((bbox[0] + bbox[2]/2) / width) * 100)
            y_center_percent = int(((bbox[1] + bbox[3]/2) / height) * 100)
            
            # Posicionamento exato
            position_desc = f"posição a {x_center_percent}% da largura e {y_center_percent}% da altura"
            
            # Classificar o elemento pela função aparente
            if height_percent < 15 and width_percent < 50 and width_percent > 15:
                buttons.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
            elif width_percent > 50 and height_percent > 20:
                containers.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
            else:
                decorative.append({
                    "shape": shape,
                    "position": position_desc,
                    "width": width_percent,
                    "height": height_percent
                })
        
        # Descrever botões
        if buttons:
            visual_elements += "- Botões (preservar exatamente como na imagem original):\n"
            for i, btn in enumerate(buttons):
                shape = btn["shape"]
                visual_elements += f"""
  * Botão {i+1}: {shape.get('shape_type', 'retângulo')} na cor {shape.get('value', '#CCCCCC')}
    - {btn['position']}
    - Tamanho: {btn['width']}% × {btn['height']}% da tela
    - Cantos: {shape.get('corners', 'arredondados')}
    - Opacidade: {shape.get('opacity', 1.0)}
    - {shape.get('texture', {}).get('type', 'flat')}
"""
        
        # Descrever containers
        if containers:
            visual_elements += "- Containers/Seções principais:\n"
            for i, cont in enumerate(containers):
                shape = cont["shape"]
                visual_elements += f"""
  * Container {i+1}: {shape.get('shape_type', 'retângulo')} na cor {shape.get('value', '#FFFFFF')}
    - {cont['position']}
    - Tamanho: {cont['width']}% × {cont['height']}% da tela
    - Cantos: {shape.get('corners', 'arredondados')}
    - Opacidade: {shape.get('opacity', 1.0)}
    - Conteúdo posicionado conforme layout original
"""
        
        # Descrever elementos decorativos
        if decorative:
            visual_elements += "- Elementos decorativos/gráficos:\n"
            for i, dec in enumerate(decorative):
                shape = dec["shape"]
                visual_elements += f"""
  * Elemento {i+1}: {shape.get('shape_type', 'forma')} na cor {shape.get('value', '#CCCCCC')}
    - {dec['position']}
    - Tamanho: {dec['width']}% × {dec['height']}% da tela
"""
        
        # Descrever efeitos especiais e iluminação da imagem original
        lighting = composition_analysis.get("lighting", {})
        effects_description = "EFEITOS VISUAIS E ACABAMENTO (da imagem original):\n"
        
        if lighting:
            main_light = lighting.get("main", {})
            effects_description += f"""
- Iluminação principal: tipo {main_light.get('type', 'ambient')}
  * Posição: {main_light.get('position', 'top-right')}
  * Intensidade: {main_light.get('intensity', 'medium')}
  * Efeito: {main_light.get('effect', 'adds depth to the composition')}

- Efeitos de destaque: {lighting.get('highlights', {}).get('effect', 'subtle glow on key elements')}
"""
        
        effects_description += """
- Aplique sombras suaves nos textos principais para garantir legibilidade perfeita
- Adicione profundidade com micro-sombras em elementos sobrepostos
- Inclua reflexos sutis em superfícies (botões, caixas) para aparência profissional
- Mantenha consistência nos estilos de fonte e espaçamentos
- Reserve espaço limpo para inserção posterior de logo na parte inferior
"""
        
        # Combinar todas as seções em um prompt completo, mantendo fidelidade ao original
        prompt = f"""
Crie uma imagem no formato vertical, com dimensões exatas de {width}x{height} pixels, que reproduza fielmente o layout da imagem original analisada, seguindo estas especificações detalhadas:

PALETA DE CORES:
- Cor primária: {colors['primary']} (use para elementos principais, áreas de destaque e textos importantes)
- Cor secundária: {colors['secondary']} (use para fundos, áreas neutras e elementos de suporte)
- Cor de destaque/acento: {colors['accent']} (use para botões, ícones e elementos interativos)
- Cor de texto principal: {color_palette.get('text', '#1F1F1F')} (para textos de alta legibilidade)
- Cor de texto secundário: #5A5A5A (para textos legais e menos importantes)

ESTRUTURA DO FUNDO:
{layout_description}

ELEMENTOS DE TEXTO (posicionados exatamente como na imagem original):
{text_description}

ELEMENTOS VISUAIS (reproduzindo fielmente os elementos da imagem original):
{visual_elements}

COMPONENTES ESPECÍFICOS E DETALHES INTERNOS:
{len(card_elements) > 0 and f"""
CARTÃO DE CRÉDITO/DÉBITO:
- Posicionado exatamente como na imagem original
- Textura de mármore fluido, misturando tons de {colors['primary']}, {shift_hue(colors['primary'], 20)} e {shift_hue(colors['primary'], 40)}
- Detalhes realistas: chip dourado ou prateado com circuitos visíveis, símbolo de contactless com ondas
- Números impressos em alto relevo com fonte específica para cartões (divididos em grupos de 4, formato: 5678 **** **** 1234)
- Data de validade no formato MM/AA na posição correta abaixo do número principal
- Logo da bandeira (Visa/Mastercard/Elo/American Express) no canto inferior direito
- Nome do cliente em fonte específica (não preencher com texto real, usar "NOME DO CLIENTE")
- Brilho especular vindo do topo direito criando reflexos na superfície
- Rotação suave para visual dinâmico (manter ângulo exatamente como na imagem original)
- Sombra realista abaixo do cartão com desfoque suave para sensação de profundidade
- Borda fina mais clara ao redor de todo o cartão para efeito de separação com o fundo
""" or ""}

{len(button_elements) > 0 and f"""
BOTÕES:
- Botões com cantos perfeitamente arredondados (raio de 8-12px)
- Botão principal (CTA) na cor {colors['accent']} com texto em branco ou {colors['secondary']}
- Estilo 3D sutilmente elevado com pequeno gradiente vertical (mais claro no topo)
- Botões secundários em {shift_hue(colors['primary'], 30)} ou em cinza claro (#E0E0E0)
- Efeito de pressão com sombra interna nos botões selecionados
- Textura glossy sutil nos botões com reflexo horizontal na parte superior
- Borda fina mais clara (1px) no topo e esquerda, e mais escura na direita e base
- Sombra externa muito suave (2-3px de desfoque, opacidade 20%)
- Texto centralizado com padding horizontal adequado (pelo menos 20px de cada lado)
- Ícone opcional alinhado ao texto (se existir na imagem original)
""" or ""}

{len(slider_elements) > 0 and f"""
SLIDER/CONTROLE DESLIZANTE:
- Trilho horizontal com textura metálica elegante em cinza gradiente (#CCCCCC até #999999)
- Altura exata do trilho como na imagem original (geralmente 4-6px)
- Botão deslizante (thumb) circular ou oval na cor {colors['primary']} com tamanho exato como original
- Área preenchida do trilho (à esquerda do thumb) com gradiente na cor {colors['primary']} até {shift_hue(colors['primary'], 20)}
- Leve sombra no botão deslizante para sensação de elevação (1-2px offset, 3-4px blur)
- Efeito de brilho interno no thumb para aparência premium
- Marcadores de valor (ticks) abaixo do trilho, se presentes na imagem original
- Valores numéricos exatos nos extremos (mínimo/máximo) como na imagem original
- Posição do thumb mantida exatamente como na referência
""" or ""}

{len(chart_elements) > 0 and f"""
GRÁFICOS FINANCEIROS:
- Reproduza exatamente o mesmo tipo de gráfico da imagem original (barras, linhas, pizza, etc.)
- Utilize as cores primária {colors['primary']} e de destaque {colors['accent']} para os dados principais
- Para gráficos de linha: linha suave com gradiente abaixo dela, partindo da cor principal até transparente
- Para gráficos de barra: barras com cantos arredondados e sutil gradiente vertical
- Para gráficos de pizza: bordas refinadas entre segmentos e leve efeito 3D
- Legendas ou labels exatamente como na imagem original, com fonte legível e nítida
- Valores numéricos precisos conforme original, alinhados adequadamente
- Grid de fundo sutil quando presente na imagem original (linhas cinza claro #EEEEEE)
- Sombra muito suave sob todo o gráfico para destacá-lo do fundo
- Manter todos os elementos de interação visíveis na imagem original (tooltips, pontos de dados destacados)
""" or ""}

{len(icon_elements) > 0 and f"""
ÍCONES:
- Ícones minimalistas e modernos na cor {colors['primary']} ou {colors['accent']}
- Estilo consistente entre todos os ícones (flat, outline, duotone ou solid)
- Ícones financeiros específicos quando relevantes:
  * Cifrão/símbolo monetário com design clean para representar dinheiro/pagamento
  * Carteira ou cartão para pagamentos e transações
  * Gráfico ascendente para investimentos ou crescimento
  * Escudo para segurança financeira
  * Relógio/calendário para prazos e pagamentos
  * Porcentagem para taxas de juros
  * Casa para financiamento imobiliário
  * Mãos para empréstimos ou suporte
- Tamanho e posicionamento exatos como na imagem original
- Leve brilho ou sombra quando destacados no design original
""" or ""}

{len(container_elements) > 0 and f"""
CAIXAS/CONTÊINERES:
- Contêineres com cantos arredondados precisos (raio de 12-16px, ou exatamente como original)
- Fundo em {colors['secondary']} com gradiente muito sutil para evitar aparência plana
- Borda refinada de 1-2px mais escura ou mais clara conforme design original
- Sombra externa suave para efeito flutuante (4-6px blur, 30% opacidade)
- Organização interna do conteúdo mantendo espaçamento e alinhamento da imagem original
- Linhas separadoras horizontais entre seções quando presentes (cor #E0E0E0, 1px)
- Headers internos destacados com texto em negrito ou cor contrastante
- Parte superior possivelmente mais escura/destacada quando usado como cabeçalho
- Espaçamento interno (padding) consistente, geralmente 16-24px
- Elementos específicos (ícones, botões) posicionados precisamente como na referência
""" or ""}

{"""
ELEMENTOS FINANCEIROS ESPECÍFICOS:
- Simuladores de valor: caixas com valores monetários destacados em fonte grande e negrito
  * Cifrão/símbolo monetário alinhado corretamente (precedendo o valor ou sobrescrito)
  * Valores decimais em tamanho menor ou cor mais clara quando presentes
  * Rótulos explicativos posicionados acima ou ao lado dos valores

- Taxas de juros: valores percentuais destacados com símbolo "%" claro
  * Texto explicativo complementar como "ao mês" ou "ao ano" em tamanho menor
  * Cores contrastantes para diferenciar taxas promocionais ou condições especiais

- Prazos e parcelas: combinação de números e texto com hierarquia clara
  * Número de parcelas em destaque quando relevante (ex: "12x")
  * Valor da parcela com símbolo monetário em formato padronizado
  * Prazo total do financiamento/empréstimo quando aplicável

- Quadro de benefícios: lista de vantagens com ícones associados
  * Marcadores visuais consistentes (check, bullet points, etc.)
  * Espaçamento igual entre itens da lista
  * Ícones alinhados verticalmente à esquerda do texto

- Formulários ou campos: áreas para preenchimento com aparência interativa
  * Cantos arredondados e borda sutil
  * Labels posicionados consistentemente (acima ou dentro do campo)
  * Campos obrigatórios com marcação visual quando identificáveis
  * Botão de submissão alinhado e destacado com a cor primária ou de destaque
"""}

EFEITOS E ACABAMENTO:
- Iluminação principal vinda da direção superior direita
- Aplique sombras suaves aos elementos principais para criar profundidade
- Textos principais devem ter sombras sutis para garantir legibilidade em qualquer fundo
- Botões devem ter efeito de pressão/clique com sombra interna suave
- Caixas e contêineres devem ter sombra suave para simular elevação
- Elementos de destaque devem ter brilho sutil (glow) para atrair atenção
- Mantenha consistência nos estilos de fonte em toda a composição
- Aplique texturas sutis em áreas grandes para evitar aparência plana
- Reserve espaço limpo na parte inferior para inserção posterior de logo

INSTRUÇÕES ESPECÍFICAS DE COMPOSIÇÃO:
- Posicione todos os elementos EXATAMENTE nas mesmas posições relativas da imagem original
- Mantenha a hierarquia visual e o fluxo de leitura da imagem original
- Preserve os espaçamentos e margens entre elementos como na imagem analisada
- Mantenha proporções exatas como especificado ({width}x{height} pixels)
- Garanta PERFEITA legibilidade de todos os textos com contraste adequado
- Se a imagem original tiver seções distintas de cor, reproduza-as fielmente
- Os tamanhos e pesos das fontes devem seguir a hierarquia da imagem original
- Botões e elementos interativos devem ser claramente identificáveis
- Elementos decorativos devem complementar o layout sem disputar atenção
- Áreas de respiro (espaço em branco) devem ser mantidas para equilíbrio visual

IMPORTANTE: Este não é um layout genérico. A composição final deve ser IDÊNTICA à imagem original analisada, apenas com as cores e textos atualizados conforme especificado acima. Todos os elementos, suas posições, tamanhos relativos e hierarquia visual devem ser reproduzidos com máxima fidelidade.
"""
        
        log("✓ Prompt detalhado baseado na imagem original criado com sucesso")
        return prompt
        
    except Exception as e:
        log(f"⚠️ Erro no Agente Compositor Prompts Avançados: {str(e)}")
        return f"""
Crie uma imagem de anúncio digital profissional que REPRODUZA o layout da imagem original analisada, com dimensões exatas de {width}x{height} pixels.

Use a seguinte paleta de cores:
- Cor primária: {colors['primary']}
- Cor secundária: {colors['secondary']}
- Cor de destaque: {colors['accent']}

IMPORTANTE: Mantenha o mesmo layout e posicionamento de elementos da imagem original.
Garanta que todos os textos sejam perfeitamente legíveis.
Reserve espaço na parte inferior para inserção posterior de logo.
"""

# Interface principal com fluxo de trabalho passo a passo
def main():
    st.markdown("### Sistema de criação automatizada de anúncios para marketing digital")
    st.markdown("Este aplicativo utiliza múltiplos agentes de IA para criar anúncios otimizados para conversão.")
    
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
                    composition = agente_composer(img_path)
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
                    final_check = agente_double_checker(
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

if __name__ == "__main__":
    main() 