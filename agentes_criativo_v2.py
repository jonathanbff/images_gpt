#!/usr/bin/env python3
"""
agentes_criativo_v2.py
Sistema de criação de anúncios com múltiplos agentes especializados - Versão 2.0

Melhorias da V2:
1) Criação baseada em prompt inicial (sem necessidade de imagem referência)
2) Inserção automática de footer com logo e informações legais
3) Geração de 5 variações de cores diferentes
4) Tradução automática para inglês e espanhol
5) Geração em formatos 1:1 e 9:16 (total de 10 criativos por projeto)
6) Logo gerada automaticamente na última etapa
7) Few-shots remodelados para melhor performance

Agentes:
1) Agente Conceitualizador: Analisa o prompt e cria conceito visual
2) Agente de Copy: Gera textos otimizados em português, inglês e espanhol
3) Agente Designer: Gera designs em múltiplas cores e formatos
4) Agente de Footer: Cria footer personalizado com logo e informações legais
5) Agente Finalizador: Combina todos os elementos e gera variações finais

Executar:
  streamlit run agentes_criativo_v2.py
"""

import streamlit as st
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
import base64
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import requests
import uuid
from typing import Dict, List, Tuple, Optional

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Importar cliente OpenAI
from openai import OpenAI

# Configurações do aplicativo
st.set_page_config(
    page_title="Sistema de Criação de Anúncios V2",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes e configurações
MODEL_VISION = "gpt-4o"
MODEL_TEXT = "gpt-4o"
MODEL_IMAGE_MAIN = "gpt-4o-mini"  # Modelo principal para usar com Responses API

# Tamanhos de imagem suportados pela Responses API
IMAGE_SIZES = {
    "1:1": (1024, 1024),
    "9:16": (1024, 1536)  # Formato vertical suportado
}

# Esquemas de cores predefinidos
COLOR_SCHEMES = {
    "vibrante": ["#FF6B35", "#F7931E", "#FFD23F", "#06FFA5", "#4D9DE0"],
    "corporativo": ["#2C3E50", "#3498DB", "#E74C3C", "#F39C12", "#95A5A6"],
    "suave": ["#D4B5A0", "#A8DADC", "#457B9D", "#1D3557", "#F1FAEE"],
    "elegante": ["#8B5A3C", "#D4AF37", "#C0392B", "#2C3E50", "#7F8C8D"]
}

# Idiomas suportados
LANGUAGES = {
    "pt": "Português",
    "en": "English", 
    "es": "Español"
}

# Opções de quantidade de criativos
QUANTITY_OPTIONS = {
    "teste": {"cores": ["vibrante"], "formatos": ["1:1"], "idiomas": ["pt"]},
    "simples": {"cores": ["vibrante", "corporativo"], "formatos": ["1:1"], "idiomas": ["pt", "en"]},
    "completo": {"cores": list(COLOR_SCHEMES.keys()), "formatos": list(IMAGE_SIZES.keys()), "idiomas": list(LANGUAGES.keys())}
}

# Diretório para arquivos temporários
TEMP_DIR = Path(tempfile.gettempdir()) / "agentes_criativos_v2"
TEMP_DIR.mkdir(exist_ok=True)

# Diretório para salvar as imagens geradas
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Carregar e inicializar cliente OpenAI
client = OpenAI()

# Inicializar estado da sessão
def init_session_state():
    """Inicializa todas as variáveis de estado da sessão"""
    default_states = {
        "step": 1,
        "concept_prompt": "",
        "brand_info": {},
        "selected_options": QUANTITY_OPTIONS["completo"],  # Padrão completo
        "concept_analysis": None,
        "copy_suggestions": {},  # Agora é um dict com idiomas
        "approved_copies": {},   # Dict com idiomas aprovados
        "generated_designs": [],
        "footer_design": None,
        "final_creatives": [],
        "logs": [],
        "project_id": str(uuid.uuid4())[:8]
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Utilitários
def log(msg: str):
    """Adiciona uma mensagem ao log e imprime no console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    st.session_state.logs.append(log_msg)
    print(log_msg)

def save_temp_image(image_bytes: bytes, filename: str) -> Path:
    """Salva uma imagem temporária no disco e retorna o caminho"""
    path = TEMP_DIR / filename
    path.write_bytes(image_bytes)
    return path

def save_output_image(image_bytes: bytes, filename: str) -> Optional[Path]:
    """Salva uma imagem na pasta de saída e retorna o caminho"""
    try:
        # Verificar se os bytes são uma imagem válida
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

def generate_project_filename(base_name: str, language: str, color_scheme: str, size: str, extension: str = "png") -> str:
    """Gera um nome de arquivo padronizado para o projeto"""
    project_id = st.session_state.project_id
    timestamp = int(time.time())
    return f"{project_id}_{base_name}_{language}_{color_scheme}_{size}_{timestamp}.{extension}"

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Converte cor hexadecimal para RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Converte RGB para hexadecimal"""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

# ===== AGENTE CONCEITUALIZADOR =====
def agente_conceitualizador(prompt_inicial: str, brand_info: Dict) -> Dict:
    """
    Agente Conceitualizador: Analisa o prompt inicial e cria um conceito visual detalhado.
    Substitui a necessidade de uma imagem de referência.
    """
    log("🧠 Agente Conceitualizador: Analisando prompt e criando conceito visual")
    
    try:
        # Few-shot examples remodelados para melhor performance
        few_shot_examples = """
EXEMPLO 1:
Prompt: "Anúncio para aplicativo de delivery de comida, focado em velocidade e praticidade"
Conceito gerado:
{
  "conceito_principal": "Velocidade e conveniência na entrega de comida",
  "elementos_visuais": {
    "foco_principal": "Smartphone com app aberto mostrando comida apetitosa",
    "elementos_secundarios": ["Ícones de velocidade (raios, cronômetro)", "Pratos coloridos", "Botão CTA destacado"],
    "composicao": "Smartphone centralizado, comida ao redor, elementos de velocidade como detalhes"
  },
  "paleta_sugerida": {
    "primaria": "#FF6B35",
    "secundaria": "#4ECDC4", 
    "destaque": "#FFE66D",
    "neutras": ["#2C3E50", "#FFFFFF"]
  },
  "tipografia": {
    "titulo": "Sans-serif bold, impactante",
    "corpo": "Sans-serif regular, legível",
    "cta": "Sans-serif bold, destacado"
  },
  "layout_sugerido": {
    "estrutura": "Composição central com elementos radiais",
    "hierarquia": "Smartphone > Título > CTA > Elementos decorativos",
    "espacamento": "Generoso, moderno, limpo"
  },
  "mood": "Dinâmico, moderno, apetitoso, confiável"
}

EXEMPLO 2:
Prompt: "Campanha para curso online de marketing digital, target jovens profissionais"
Conceito gerado:
{
  "conceito_principal": "Transformação profissional através do marketing digital",
  "elementos_visuais": {
    "foco_principal": "Laptop/desktop com gráficos de crescimento e ícones digitais",
    "elementos_secundarios": ["Gráficos de performance", "Ícones de redes sociais", "Certificado/diploma"],
    "composicao": "Laptop em ângulo dinâmico, gráficos ascendentes, elementos tech ao fundo"
  },
  "paleta_sugerida": {
    "primaria": "#3498DB",
    "secundaria": "#2C3E50",
    "destaque": "#F39C12",
    "neutras": ["#ECF0F1", "#34495E"]
  },
  "tipografia": {
    "titulo": "Sans-serif bold, profissional",
    "corpo": "Sans-serif medium, corporativo",
    "cta": "Sans-serif bold, call-to-action forte"
  },
  "layout_sugerido": {
    "estrutura": "Grid assimétrico, moderno",
    "hierarquia": "Título > Benefícios > CTA > Elementos de apoio",
    "espacamento": "Profissional, organizado, respirável"
  },
  "mood": "Profissional, aspiracional, tecnológico, confiável"
}
"""

        prompt = f"""
Você é um especialista em conceituação visual e estratégia criativa. Com base no prompt fornecido e informações da marca, crie um conceito visual EXTREMAMENTE DETALHADO e estratégico.

PROMPT INICIAL: "{prompt_inicial}"

INFORMAÇÕES DA MARCA:
- Nome: {brand_info.get('nome', 'Não informado')}
- Setor: {brand_info.get('setor', 'Não informado')}
- Público-alvo: {brand_info.get('publico_alvo', 'Não informado')}
- Objetivo da campanha: {brand_info.get('objetivo', 'Não informado')}
- Tom de voz: {brand_info.get('tom_voz', 'Não informado')}

{few_shot_examples}

AGORA CRIE UM CONCEITO PARA O PROMPT FORNECIDO:

Retorne APENAS um JSON válido (sem ```json ou formatação extra) com a seguinte estrutura EXATA:

{{
  "conceito_principal": "Descrição clara do conceito central em uma frase",
  "elementos_visuais": {{
    "foco_principal": "Elemento visual central e mais importante",
    "elementos_secundarios": ["Lista", "de", "elementos", "de", "apoio"],
    "composicao": "Descrição da organização espacial dos elementos"
  }},
  "paleta_sugerida": {{
    "primaria": "#HEXCODE",
    "secundaria": "#HEXCODE",
    "destaque": "#HEXCODE", 
    "neutras": ["#HEXCODE", "#HEXCODE"]
  }},
  "tipografia": {{
    "titulo": "Estilo da tipografia do título",
    "corpo": "Estilo da tipografia do corpo do texto",
    "cta": "Estilo da tipografia do call-to-action"
  }},
  "layout_sugerido": {{
    "estrutura": "Tipo de estrutura/grid",
    "hierarquia": "Ordem de importância visual",
    "espacamento": "Estilo do espaçamento"
  }},
  "mood": "Lista de 3-5 adjetivos que descrevem o mood visual",
  "estrategia_conversao": {{
    "ponto_focal": "Onde direcionar o olhar primeiro",
    "caminho_visual": "Sequência de leitura sugerida", 
    "elementos_persuasao": ["Lista", "de", "elementos", "persuasivos"],
    "cta_estrategia": "Como destacar e posicionar o call-to-action"
  }},
  "adaptacao_formatos": {{
    "1:1": "Considerações específicas para formato quadrado",
    "9:16": "Considerações específicas para formato vertical/stories"
  }}
}}

IMPORTANTE: 
- Seja ESPECÍFICO em cores (use códigos HEX reais)
- Considere a psicologia das cores para o público-alvo
- Pense em conversão e performance
- Adapte para os diferentes formatos
- Considere tendências visuais atuais
"""

        response = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[
                {"role": "system", "content": "Você é um especialista em conceituação visual e estratégia criativa. Retorne APENAS JSON válido, sem formatação adicional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Limpar possíveis formatações markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse do JSON
        concept_data = json.loads(content)
        
        log("✓ Conceito visual criado com sucesso")
        return {
            "success": True,
            "concept": concept_data,
            "prompt_original": prompt_inicial,
            "brand_info": brand_info
        }
        
    except json.JSONDecodeError as e:
        log(f"❌ Erro ao parsear JSON do conceito: {str(e)}")
        log(f"Conteúdo retornado: {content}")
        return {
            "success": False,
            "error": f"Erro ao processar conceito: {str(e)}",
            "content": content
        }
    except Exception as e:
        log(f"❌ Erro no Agente Conceitualizador: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# ===== AGENTE DE COPY MULTILÍNGUE =====
def agente_copy_multilingue(concept_analysis: Dict, selected_languages: List[str] = None) -> Dict:
    """
    Agente de Copy: Gera textos otimizados para conversão em múltiplos idiomas.
    """
    log("✍️ Agente de Copy: Gerando textos otimizados em múltiplos idiomas")
    
    try:
        concept = concept_analysis["concept"]
        brand_info = concept_analysis["brand_info"]
        
        # Usar idiomas selecionados ou todos
        if selected_languages is None:
            selected_languages = list(LANGUAGES.keys())
        
        # Few-shot examples para copywriting
        few_shot_examples = """
EXEMPLO 1 - Delivery de Comida:
Conceito: "Velocidade e conveniência na entrega de comida"
Público: Jovens urbanos, profissionais ocupados

PORTUGUÊS:
{
  "titulo_principal": "Comida deliciosa em 30 minutos",
  "subtitulo": "Peça agora e receba quentinho em casa",
  "cta_principal": "PEDIR AGORA",
  "cta_secundario": "Ver cardápio",
  "bullet_points": ["🚀 Entrega em 30min", "🍕 +500 restaurantes", "💳 Pague no app"],
  "urgencia": "Frete grátis hoje!",
  "beneficio_principal": "Sem sair de casa, sem estresse"
}

ENGLISH:
{
  "titulo_principal": "Delicious food in 30 minutes",
  "subtitulo": "Order now and get it hot at home",
  "cta_principal": "ORDER NOW",
  "cta_secundario": "View menu", 
  "bullet_points": ["🚀 30min delivery", "🍕 500+ restaurants", "💳 Pay in app"],
  "urgencia": "Free delivery today!",
  "beneficio_principal": "No leaving home, no stress"
}

ESPAÑOL:
{
  "titulo_principal": "Comida deliciosa en 30 minutos",
  "subtitulo": "Pide ahora y recíbela caliente en casa",
  "cta_principal": "PEDIR AHORA",
  "cta_secundario": "Ver menú",
  "bullet_points": ["🚀 Entrega en 30min", "🍕 +500 restaurantes", "💳 Paga en app"],
  "urgencia": "¡Envío gratis hoy!",
  "beneficio_principal": "Sin salir de casa, sin estrés"
}
"""

        all_copies = {}
        
        for lang_code in selected_languages:
            if lang_code not in LANGUAGES:
                log(f"⚠️ Idioma '{lang_code}' não suportado, pulando...")
                continue
                
            lang_name = LANGUAGES[lang_code]
            log(f"Gerando copy para {lang_name}...")
            
            prompt = f"""
Você é um copywriter especialista em conversão e marketing digital. Crie textos ALTAMENTE PERSUASIVOS e otimizados para conversão no idioma {lang_name}.

CONCEITO VISUAL:
{json.dumps(concept, indent=2, ensure_ascii=False)}

INFORMAÇÕES DA MARCA:
{json.dumps(brand_info, indent=2, ensure_ascii=False)}

DIRETRIZES DE COPY:
- Use gatilhos psicológicos (escassez, urgência, prova social)
- Foque nos benefícios, não nas características
- Use linguagem direta e ação
- Considere o público-alvo e tom de voz da marca
- Otimize para conversão em anúncios digitais

{few_shot_examples}

GERE AGORA o copy para o idioma {lang_name}:

Retorne APENAS um JSON válido (sem ```json ou formatação extra) com esta estrutura EXATA:

{{
  "titulo_principal": "Título impactante que chama atenção (máx 40 chars)",
  "subtitulo": "Subtítulo que explica o benefício principal (máx 60 chars)",
  "cta_principal": "Call-to-action principal forte (máx 20 chars)",
  "cta_secundario": "Call-to-action secundário opcional (máx 20 chars)",
  "bullet_points": ["Até 3 benefícios curtos", "Com emojis relevantes", "Máximo 25 chars cada"],
  "urgencia": "Elemento de urgência/escassez (máx 30 chars)",
  "beneficio_principal": "Benefício emocional principal (máx 50 chars)",
  "prova_social": "Elemento de credibilidade (máx 40 chars)",
  "garantia": "Garantia ou promessa (máx 35 chars)",
  "footer_texto": "Texto para footer legal (máx 60 chars)"
}}

IMPORTANTE:
- Mantenha os limites de caracteres
- Use verbos de ação nos CTAs
- Inclua emojis estratégicos nos bullet points
- Adapte culturalmente para o idioma
- Foque na conversão imediata
"""

            response = client.chat.completions.create(
                model=MODEL_TEXT,
                messages=[
                    {"role": "system", "content": f"Você é um copywriter especialista em {lang_name}. Retorne APENAS JSON válido, sem formatação adicional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Limpar formatação
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse do JSON
            copy_data = json.loads(content)
            all_copies[lang_code] = copy_data
            
            log(f"✓ Copy gerado para {lang_name}")
        
        log("✓ Todos os copies multilíngues gerados com sucesso")
        return {
            "success": True,
            "copies": all_copies,
            "concept_reference": concept
        }
        
    except json.JSONDecodeError as e:
        log(f"❌ Erro ao parsear JSON do copy: {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao processar copy: {str(e)}",
            "content": content
        }
    except Exception as e:
        log(f"❌ Erro no Agente de Copy: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# ===== AGENTE DESIGNER MULTIFORMAT =====
def agente_designer_multiformat(concept_analysis: Dict, approved_copies: Dict, selected_options: Dict = None) -> List[Dict]:
    """
    Agente Designer: Gera designs em múltiplas cores e formatos usando GPT-image-1.
    """
    log("🎨 Agente Designer: Gerando designs em múltiplos formatos e cores")
    
    try:
        concept = concept_analysis["concept"]
        designs_generated = []
        
        # Usar opções selecionadas ou padrão completo
        if selected_options is None:
            selected_options = QUANTITY_OPTIONS["completo"]
        
        selected_colors = selected_options.get("cores", list(COLOR_SCHEMES.keys()))
        selected_formats = selected_options.get("formatos", list(IMAGE_SIZES.keys()))
        
        total_designs = len(selected_colors) * len(selected_formats)
        log(f"Gerando {total_designs} designs ({len(selected_colors)} cores × {len(selected_formats)} formatos)")
        
        # Para cada esquema de cores selecionado
        for color_scheme_name in selected_colors:
            if color_scheme_name not in COLOR_SCHEMES:
                log(f"⚠️ Esquema de cor '{color_scheme_name}' não encontrado, pulando...")
                continue
                
            colors = COLOR_SCHEMES[color_scheme_name]
            log(f"Gerando designs para esquema: {color_scheme_name}")
            
            # Para cada formato selecionado
            for size_name in selected_formats:
                if size_name not in IMAGE_SIZES:
                    log(f"⚠️ Formato '{size_name}' não suportado, pulando...")
                    continue
                    
                width, height = IMAGE_SIZES[size_name]
                log(f"Formato: {size_name} ({width}x{height})")
                
                # Pegar copy em português como base para o prompt visual
                copy_pt = approved_copies.get("pt", {})
                
                # Construir prompt otimizado para GPT-image-1
                visual_prompt = build_visual_prompt(
                    concept=concept,
                    copy_data=copy_pt,
                    color_scheme=colors,
                    format_ratio=size_name,
                    width=width,
                    height=height
                )
                
                # Gerar imagem com a nova Responses API
                try:
                    log(f"Gerando imagem {size_name} - {color_scheme_name}...")
                    
                    response = client.responses.create(
                        model=MODEL_IMAGE_MAIN,
                        input=visual_prompt,
                        tools=[{
                            "type": "image_generation",
                            "size": f"{width}x{height}",
                            "quality": "high"
                        }]
                    )
                    
                    # Extrair dados da imagem da resposta
                    image_data = [
                        output.result
                        for output in response.output
                        if output.type == "image_generation_call"
                    ]
                    
                    if not image_data:
                        log(f"❌ Nenhuma imagem gerada para {size_name}-{color_scheme_name}")
                        continue
                    
                    # Decodificar imagem base64
                    image_base64 = image_data[0]
                    image_bytes = base64.b64decode(image_base64)
                    
                    # Verificar se os bytes são válidos
                    if len(image_bytes) == 0:
                        log(f"❌ Imagem vazia recebida para {size_name}-{color_scheme_name}")
                        continue
                    
                    # Salvar imagem
                    filename = generate_project_filename(
                        "design", "pt", color_scheme_name, size_name
                    )
                    saved_path = save_output_image(image_bytes, filename)
                    
                    if saved_path:
                        design_info = {
                            "path": str(saved_path),
                            "filename": filename,
                            "color_scheme": color_scheme_name,
                            "colors": colors,
                            "size": size_name,
                            "dimensions": (width, height),
                            "prompt_used": visual_prompt,
                            "language": "pt"  # Base sempre em português
                        }
                        designs_generated.append(design_info)
                        log(f"✓ Design {size_name}-{color_scheme_name} salvo com sucesso")
                    
                    # Pequena pausa para evitar rate limiting
                    time.sleep(2)
                    
                except Exception as img_error:
                    log(f"❌ Erro ao gerar imagem {size_name}-{color_scheme_name}: {str(img_error)}")
                    continue
        
        log(f"✓ {len(designs_generated)} designs gerados com sucesso")
        return designs_generated
        
    except Exception as e:
        log(f"❌ Erro no Agente Designer: {str(e)}")
        return []

def build_visual_prompt(concept: Dict, copy_data: Dict, color_scheme: List[str], format_ratio: str, width: int, height: int) -> str:
    """
    Constrói um prompt visual otimizado para GPT-image-1 seguindo as melhores práticas.
    """
    
    # Elementos do conceito
    foco_principal = concept["elementos_visuais"]["foco_principal"]
    elementos_secundarios = concept["elementos_visuais"]["elementos_secundarios"]
    mood = concept["mood"]
    
    # Textos do copy
    titulo = copy_data.get("titulo_principal", "")
    subtitulo = copy_data.get("subtitulo", "")
    cta = copy_data.get("cta_principal", "")
    
    # Cores do esquema
    cor_primaria = color_scheme[0]
    cor_secundaria = color_scheme[1] if len(color_scheme) > 1 else color_scheme[0]
    cor_destaque = color_scheme[2] if len(color_scheme) > 2 else color_scheme[0]
    
    # Adaptações por formato
    format_instructions = ""
    if format_ratio == "1:1":
        format_instructions = "Square format (1:1). Center composition with balanced elements around the focal point. Equal spacing on all sides."
    else:  # 9:16
        format_instructions = "Vertical format (9:16) for mobile/stories. Top-to-bottom hierarchy: header area, main visual, text area, CTA at bottom. Utilize full vertical space."
    
    prompt = f"""
Create a modern, professional advertising design with the following specifications:

MAIN CONCEPT: {foco_principal}
SUPPORTING ELEMENTS: {', '.join(elementos_secundarios[:3])}
MOOD: {mood}

LAYOUT:
{format_instructions}

COLOR SCHEME:
- Primary color: {cor_primaria}
- Secondary color: {cor_secundaria}
- Accent/highlight color: {cor_destaque}
- Use white or very light gray for text readability

TEXT ELEMENTS TO INCLUDE:
- Main headline: "{titulo}"
- Subheadline: "{subtitulo}" 
- Call-to-action button: "{cta}"

DESIGN REQUIREMENTS:
- Modern, clean typography (sans-serif)
- High contrast for text readability
- Professional gradient backgrounds or solid colors
- Subtle shadows and depth
- Space for logo placement (top-right or bottom-center)
- Marketing/advertising style
- High quality, crisp details
- Balanced composition
- Clear visual hierarchy

STYLE: Modern digital marketing advertisement, professional, conversion-optimized, clean layout, contemporary design trends.

SIZE: {width}x{height} pixels, high resolution, suitable for digital advertising.
"""
    
    return prompt

# ===== AGENTE DE FOOTER =====
def agente_footer(brand_info: Dict, approved_copies: Dict) -> Dict:
    """
    Agente de Footer: Gera apenas o logo da marca. 
    Os footers serão adicionados individualmente durante a finalização usando edição de imagem.
    """
    log("📄 Agente de Footer: Gerando logo da marca")
    
    try:
        # Gerar apenas o logo da marca
        logo_info = generate_brand_logo(brand_info)
        
        if logo_info:
            log("✓ Logo da marca gerado com sucesso")
            return {
                "success": True,
                "logo_info": logo_info
            }
        else:
            return {
                "success": False,
                "error": "Falha ao gerar logo"
            }
        
    except Exception as e:
        log(f"❌ Erro no Agente de Footer: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_brand_logo(brand_info: Dict) -> Dict:
    """
    Gera logo da marca usando GPT-image-1.
    """
    log("🎨 Gerando logo da marca...")
    
    try:
        nome_marca = brand_info.get("nome", "Marca")
        setor = brand_info.get("setor", "")
        tom_voz = brand_info.get("tom_voz", "profissional")
        
        # Prompt otimizado para logo
        logo_prompt = f"""
Create a professional, minimalist logo for the brand "{nome_marca}" in the {setor} sector.

REQUIREMENTS:
- Clean, modern design
- Professional and {tom_voz} style
- Suitable for digital use
- High contrast
- Simple geometric shapes or clean typography
- Scalable design
- Color scheme: primary brand colors with white/transparent background
- Vector-style appearance
- Corporate identity standards

STYLE: Modern logo design, clean, professional, minimalist, suitable for business use, high quality.

SIZE: 1024x1024 pixels, centered, transparent or white background.
"""
        
        response = client.responses.create(
            model=MODEL_IMAGE_MAIN,
            input=logo_prompt,
            tools=[{
                "type": "image_generation",
                "size": "1024x1024",
                "quality": "high"
            }]
        )
        
        # Extrair dados da imagem da resposta
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if not image_data:
            log("❌ Nenhum logo gerado")
            return {}
        
        # Decodificar logo base64
        logo_base64 = image_data[0]
        logo_bytes = base64.b64decode(logo_base64)
        
        if len(logo_bytes) == 0:
            log("❌ Logo vazio recebido")
            return {}
        
        # Salvar logo
        logo_filename = f"{st.session_state.project_id}_logo_{int(time.time())}.png"
        logo_path = save_output_image(logo_bytes, logo_filename)
        
        if logo_path:
            log("✓ Logo da marca gerado com sucesso")
            return {
                "path": str(logo_path),
                "filename": logo_filename,
                "prompt_used": logo_prompt
            }
        else:
            raise Exception("Falha ao salvar logo")
            
    except Exception as e:
        log(f"❌ Erro ao gerar logo: {str(e)}")
        return {}

# ===== AGENTE FINALIZADOR =====
def agente_finalizador(designs: List[Dict], logo_info: Dict, approved_copies: Dict) -> List[Dict]:
    """
    Agente Finalizador: Adiciona footers específicos para cada idioma usando edição de imagem.
    """
    log("🎯 Agente Finalizador: Adicionando footers específicos por idioma usando edição")
    
    try:
        final_creatives = []
        
        # Para cada design base gerado
        for design in designs:
            color_scheme = design["color_scheme"] 
            size = design["size"]
            design_path = design["path"]
            
            # Para cada idioma
            for lang_code in LANGUAGES.keys():
                copy_data = approved_copies.get(lang_code, {})
                
                # Adicionar footer usando edição de imagem
                final_creative = add_footer_to_design(
                    design_path=design_path,
                    design_info=design,
                    copy_data=copy_data,
                    logo_info=logo_info,
                    language=lang_code
                )
                
                if final_creative:
                    final_creatives.append(final_creative)
                    log(f"✓ Criativo final gerado: {size}-{color_scheme}-{lang_code}")
        
        log(f"✓ {len(final_creatives)} criativos finais gerados com sucesso")
        return final_creatives
        
    except Exception as e:
        log(f"❌ Erro no Agente Finalizador: {str(e)}")
        return []

def add_footer_to_design(design_path: str, design_info: Dict, copy_data: Dict, logo_info: Dict, language: str) -> Optional[Dict]:
    """
    Adiciona footer a um design base usando edição de imagem da Responses API.
    """
    try:
        # Informações legais por idioma
        legal_info = {
            "pt": {
                "copyright": f"© 2024 {copy_data.get('brand_name', 'Marca')}. Todos os direitos reservados.",
                "terms": "Termos de uso | Política de privacidade"
            },
            "en": {
                "copyright": f"© 2024 {copy_data.get('brand_name', 'Brand')}. All rights reserved.",
                "terms": "Terms of use | Privacy policy"
            },
            "es": {
                "copyright": f"© 2024 {copy_data.get('brand_name', 'Marca')}. Todos los derechos reservados.",
                "terms": "Términos de uso | Política de privacidad"
            }
        }
        
        current_legal = legal_info.get(language, legal_info["pt"])
        footer_text = copy_data.get("footer_texto", "")
        
        # Criar arquivo temporário com a imagem base
        with open(design_path, "rb") as f:
            image_bytes = f.read()
        
        # Upload da imagem para a API Files
        files_response = client.files.create(
            file=open(design_path, "rb"),
            purpose='vision'
        )
        file_id = files_response.id
        
        # Prompt para adicionar footer usando edição
        edit_prompt = f"""
Add a professional footer to the bottom of this advertisement design.

FOOTER CONTENT TO ADD:
- Main footer text: "{footer_text}"
- Copyright: "{current_legal['copyright']}"
- Legal terms: "{current_legal['terms']}"

FOOTER DESIGN REQUIREMENTS:
- Add footer area at the bottom (approximately 15% of image height)
- Clean, professional layout with light background
- Dark text for readability
- Small, elegant typography
- Center-aligned text
- Subtle separator line between main design and footer
- Footer should complement the existing design aesthetically
- Maintain the original design quality and style

The footer should be seamlessly integrated with the existing design while maintaining professional appearance.
"""

        # Usar Responses API para editar a imagem
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": edit_prompt,
                        },
                        {
                            "type": "input_image",
                            "file_id": file_id,
                        }
                    ],
                }
            ],
            tools=[{
                "type": "image_generation",
                "quality": "high"
            }]
        )
        
        # Extrair imagem editada
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if not image_data:
            log(f"❌ Falha ao adicionar footer para {language}")
            return None
        
        # Decodificar imagem editada
        edited_base64 = image_data[0]
        edited_bytes = base64.b64decode(edited_base64)
        
        # Salvar criativo final
        final_filename = generate_project_filename(
            "final", language, design_info["color_scheme"], design_info["size"]
        )
        
        final_path = save_output_image(edited_bytes, final_filename)
        
        if final_path:
            log(f"✓ Criativo final salvo: {final_filename}")
            
            # Limpar arquivo temporário
            try:
                client.files.delete(file_id)
            except:
                pass
            
            return {
                "path": str(final_path),
                "filename": final_filename,
                "language": language,
                "color_scheme": design_info["color_scheme"],
                "size": design_info["size"],
                "copy_used": copy_data,
                "base_design": design_info["path"],
                "footer_added": True,
                "creation_timestamp": int(time.time())
            }
        else:
            return None
            
    except Exception as e:
        log(f"❌ Erro ao adicionar footer para {language}: {str(e)}")
        return None

# ===== INTERFACE PRINCIPAL =====
def main():
    """Interface principal do aplicativo Streamlit"""
    
    # Verificar API Key
    api_key_env = os.getenv("OPENAI_API_KEY", "")
    if not api_key_env:
        st.error("⚠️ OpenAI API Key não encontrada! Configure no arquivo .env")
        st.stop()
    
    # Botão para voltar à página inicial
    if st.button("⬅️ Voltar à Página Inicial", key="back_to_home_v2"):
        st.switch_page("home.py")
    
    # Título e descrição
    st.title("Videomate")
    st.markdown("### Vibe Marketing with AI")
    st.markdown("New Features: you can create any type of image with AI: then image to video.")
    
    # Sidebar com informações do projeto
    with st.sidebar:
        st.header("📊 Projeto Atual")
        st.code(f"ID: {st.session_state.project_id}")
        
        st.subheader("🎯 Especificações V2")
        st.markdown("""
        - ✅ Prompt inicial (sem imagem)
        - ✅ Footer com logo automático
        - ✅ 5 esquemas de cores
        - ✅ 3 idiomas (PT/EN/ES)
        - ✅ 2 formatos (1:1, 9:16)
        - ✅ Total: 30 criativos
        """)
        
        st.divider()
        
        # Logs
        st.subheader("📋 Logs do Sistema")
        if st.session_state.logs:
            logs_text = "\n".join(st.session_state.logs[-20:])  # Últimos 20 logs
            st.text_area("Logs do sistema", value=logs_text, height=300, disabled=True, label_visibility="collapsed")
        
        # Botão para reiniciar
        if st.button("🔄 Novo Projeto", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ["logs"]:
                    del st.session_state[key]
            init_session_state()
            st.rerun()
    
    # ETAPA 1: Prompt Inicial e Informações da Marca
    if st.session_state.step == 1:
        st.header("1️⃣ Etapa 1: Conceito e Marca")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Prompt do Criativo")
            prompt_inicial = st.text_area(
                "Descreva o anúncio que você quer criar:",
                height=150,
                placeholder="Ex: Anúncio para app de delivery de comida, focado em velocidade e conveniência para jovens profissionais urbanos...",
                value=st.session_state.concept_prompt
            )
            
        with col2:
            st.subheader("Informações da Marca")
            nome_marca = st.text_input("Nome da Marca", value=st.session_state.brand_info.get("nome", ""))
            setor = st.selectbox("Setor", [
                "Tecnologia", "Alimentação", "Saúde", "Educação", "Varejo", 
                "Serviços", "Entretenimento", "Financeiro", "Outro"
            ], index=0)
            publico_alvo = st.text_input("Público-alvo", 
                                       placeholder="Ex: Jovens profissionais 25-35 anos",
                                       value=st.session_state.brand_info.get("publico_alvo", ""))
            objetivo = st.selectbox("Objetivo", [
                "Conversão/Vendas", "Geração de Leads", "Reconhecimento de Marca", 
                "Engajamento", "Download de App", "Cadastro"
            ])
            tom_voz = st.selectbox("Tom de Voz", [
                "Profissional", "Casual", "Amigável", "Urgente", "Elegante", "Divertido"
            ])
            
            # Seleção de quantidade de criativos
            st.divider()
            st.subheader("🎯 Quantidade de Criativos")
            quantity_option = st.selectbox("Selecione a quantidade:", [
                ("teste", "🔬 Teste (1 criativo - vibrante/1:1/PT)"),
                ("simples", "⚡ Simples (4 criativos - 2 cores/1 formato/2 idiomas)"),
                ("completo", "🚀 Completo (30 criativos - 5 cores/2 formatos/3 idiomas)")
            ], format_func=lambda x: x[1])
            
            selected_quantity = quantity_option[0]
            selected_options = QUANTITY_OPTIONS[selected_quantity]
            
            # Mostrar resumo
            total_criativos = len(selected_options["cores"]) * len(selected_options["formatos"]) * len(selected_options["idiomas"])
            st.info(f"📊 Total: {total_criativos} criativos finais")
            
            with st.expander("📋 Detalhes da seleção"):
                st.write(f"**Cores:** {', '.join(selected_options['cores'])}")
                st.write(f"**Formatos:** {', '.join(selected_options['formatos'])}")
                st.write(f"**Idiomas:** {', '.join(selected_options['idiomas'])}")
        
        # Salvar informações na sessão
        st.session_state.concept_prompt = prompt_inicial
        st.session_state.brand_info = {
            "nome": nome_marca,
            "setor": setor,
            "publico_alvo": publico_alvo,
            "objetivo": objetivo,
            "tom_voz": tom_voz.lower()
        }
        st.session_state.selected_options = selected_options
        
        # Botão para avançar
        if prompt_inicial and nome_marca:
            if st.button("🧠 Analisar Conceito", use_container_width=True, type="primary"):
                with st.spinner("Analisando conceito e criando estratégia visual..."):
                    concept_result = agente_conceitualizador(prompt_inicial, st.session_state.brand_info)
                    
                    if concept_result["success"]:
                        st.session_state.concept_analysis = concept_result
                        st.session_state.step = 2
                        st.success("✅ Conceito analisado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao analisar conceito: {concept_result.get('error', 'Erro desconhecido')}")
        else:
            st.warning("⚠️ Preencha o prompt e o nome da marca para continuar")
    
    # ETAPA 2: Revisão do Conceito e Geração de Copies
    elif st.session_state.step == 2:
        st.header("2️⃣ Etapa 2: Conceito Visual e Copywriting")
        
        if not st.session_state.concept_analysis:
            st.error("Conceito não encontrado. Retornando à etapa 1.")
            st.session_state.step = 1
            st.rerun()
            
        concept = st.session_state.concept_analysis["concept"]
        
        # Mostrar conceito gerado
        st.subheader("📋 Conceito Visual Criado")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Conceito Principal:**")
            st.info(concept["conceito_principal"])
            
            st.markdown("**Elementos Visuais:**")
            st.write(f"🎯 **Foco:** {concept['elementos_visuais']['foco_principal']}")
            st.write(f"📐 **Composição:** {concept['elementos_visuais']['composicao']}")
            
            if concept['elementos_visuais']['elementos_secundarios']:
                st.write("**Elementos Secundários:**")
                for elem in concept['elementos_visuais']['elementos_secundarios']:
                    st.write(f"• {elem}")
        
        with col2:
            st.markdown("**Paleta de Cores:**")
            cores_html = ""
            for tipo, cor in concept["paleta_sugerida"].items():
                if isinstance(cor, list):
                    cores_html += f"**{tipo.title()}:** "
                    for c in cor:
                        cores_html += f'<span style="background-color:{c}; color:white; padding:2px 8px; margin:2px; border-radius:3px;">{c}</span> '
                else:
                    cores_html += f'**{tipo.title()}:** <span style="background-color:{cor}; color:white; padding:2px 8px; margin:2px; border-radius:3px;">{cor}</span><br>'
            st.markdown(cores_html, unsafe_allow_html=True)
            
            st.markdown("**Mood/Estilo:**")
            st.write(concept["mood"])
        
        # Gerar copies se ainda não foram gerados
        if not st.session_state.copy_suggestions:
            if st.button("✍️ Gerar Textos Multilíngues", use_container_width=True, type="primary"):
                with st.spinner("Gerando textos otimizados em múltiplos idiomas..."):
                    selected_languages = st.session_state.selected_options.get("idiomas", list(LANGUAGES.keys()))
                    copy_result = agente_copy_multilingue(
                        st.session_state.concept_analysis, 
                        selected_languages
                    )
                    
                    if copy_result["success"]:
                        st.session_state.copy_suggestions = copy_result
                        st.success("✅ Textos gerados em todos os idiomas selecionados!")
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao gerar textos: {copy_result.get('error', 'Erro desconhecido')}")
        else:
            # Mostrar copies gerados
            st.subheader("📝 Textos Gerados por Idioma")
            
            # Criar tabs dinamicamente baseado nos idiomas selecionados
            copies = st.session_state.copy_suggestions["copies"]
            selected_languages = st.session_state.selected_options.get("idiomas", list(LANGUAGES.keys()))
            
            if len(selected_languages) == 1:
                # Se só um idioma, não usar tabs
                lang_code = selected_languages[0]
                lang_name = LANGUAGES[lang_code]
                st.markdown(f"### {lang_name}")
                copy_data = copies.get(lang_code, {})
                approved_copies = {lang_code: display_copy_editor(copy_data, lang_code)}
            else:
                # Múltiplos idiomas, usar tabs
                tab_labels = [f"{LANGUAGES[lang]}" for lang in selected_languages if lang in LANGUAGES]
                tabs = st.tabs(tab_labels)
                
                approved_copies = {}
                for i, lang_code in enumerate(selected_languages):
                    if lang_code in LANGUAGES:
                        with tabs[i]:
                            st.markdown(f"### {LANGUAGES[lang_code]}")
                            copy_data = copies.get(lang_code, {})
                            approved_copies[lang_code] = display_copy_editor(copy_data, lang_code)
            
            # Salvar copies aprovados
            st.session_state.approved_copies = approved_copies
            
            # Botão para continuar
            if st.button("🎨 Gerar Designs", use_container_width=True, type="primary"):
                st.session_state.step = 3
                st.rerun()
    
    # ETAPA 3: Geração de Designs
    elif st.session_state.step == 3:
        st.header("3️⃣ Etapa 3: Geração de Designs Base")
        
        if not st.session_state.approved_copies:
            st.error("Textos não encontrados. Retornando à etapa 2.")
            st.session_state.step = 2
            st.rerun()
        
        # Mostrar progresso estimado
        selected_options = st.session_state.selected_options
        total_designs = len(selected_options["cores"]) * len(selected_options["formatos"])
        st.info(f"🎨 Será gerado {total_designs} designs base ({len(selected_options['cores'])} cores × {len(selected_options['formatos'])} formatos)")
        
        # Gerar designs se ainda não foram gerados
        if not st.session_state.generated_designs:
            if st.button("🚀 Gerar Todos os Designs", use_container_width=True, type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("Gerando designs base... Isso pode levar alguns minutos."):
                    designs = agente_designer_multiformat(
                        st.session_state.concept_analysis,
                        st.session_state.approved_copies,
                        st.session_state.selected_options
                    )
                    
                    if designs:
                        st.session_state.generated_designs = designs
                        progress_bar.progress(100)
                        status_text.success(f"✅ {len(designs)} designs gerados com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Falha na geração de designs")
        else:
            # Mostrar designs gerados
            st.subheader(f"🎨 Designs Gerados ({len(st.session_state.generated_designs)})")
            
            # Organizar por formato
            designs_1_1 = [d for d in st.session_state.generated_designs if d["size"] == "1:1"]
            designs_9_16 = [d for d in st.session_state.generated_designs if d["size"] == "9:16"]
            
            # Tabs por formato
            tab1, tab2 = st.tabs(["📱 Formato 1:1 (Quadrado)", "📱 Formato 9:16 (Stories)"])
            
            with tab1:
                display_design_grid(designs_1_1, "1:1")
            
            with tab2:
                display_design_grid(designs_9_16, "9:16")
            
            # Botão para continuar
            if st.button("📄 Criar Footer e Finalizar", use_container_width=True, type="primary"):
                st.session_state.step = 4
                st.rerun()
    
    # ETAPA 4: Footer e Finalização
    elif st.session_state.step == 4:
        st.header("4️⃣ Etapa 4: Footer e Finalização")
        
        if not st.session_state.generated_designs:
            st.error("Designs não encontrados. Retornando à etapa 3.")
            st.session_state.step = 3
            st.rerun()
        
        # Gerar footer se ainda não foi gerado
        if not st.session_state.footer_design:
            if st.button("📄 Gerar Footer com Logo", use_container_width=True, type="primary"):
                with st.spinner("Gerando logo da marca e footer multilíngue..."):
                    footer_result = agente_footer(
                        st.session_state.brand_info,
                        st.session_state.approved_copies
                    )
                    
                    if footer_result["success"]:
                        st.session_state.footer_design = footer_result
                        st.success("✅ Footer e logo gerados!")
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao gerar footer: {footer_result.get('error', 'Erro desconhecido')}")
        else:
            # Mostrar logo gerado
            st.subheader("🎯 Logo da Marca")
            logo_info = st.session_state.footer_design.get("logo_info", {})
            if logo_info and "path" in logo_info:
                col1, col2, col3 = st.columns([1,1,1])
                with col2:
                    st.image(logo_info["path"], caption="Logo gerado", width=200)
            
            # Gerar criativos finais
            if not st.session_state.final_creatives:
                total_final = len(st.session_state.generated_designs) * len(LANGUAGES)
                st.info(f"🎯 Será gerado {total_final} criativos finais com footers específicos por idioma")
                
                if st.button("🎯 Gerar Criativos Finais", use_container_width=True, type="primary"):
                    with st.spinner("Adicionando footers e gerando criativos finais..."):
                        final_creatives = agente_finalizador(
                            st.session_state.generated_designs,
                            st.session_state.footer_design["logo_info"],
                            st.session_state.approved_copies
                        )
                        
                        if final_creatives:
                            st.session_state.final_creatives = final_creatives
                            st.success(f"✅ {len(final_creatives)} criativos finais gerados!")
                            st.session_state.step = 5
                            st.rerun()
                        else:
                            st.error("❌ Falha na geração de criativos finais")
    
    # ETAPA 5: Resultado Final
    elif st.session_state.step == 5:
        st.header("5️⃣ Etapa 5: Criativos Finais")
        
        if not st.session_state.final_creatives:
            st.error("Criativos finais não encontrados. Retornando à etapa 4.")
            st.session_state.step = 4
            st.rerun()
        
        st.success(f"🎉 {len(st.session_state.final_creatives)} criativos finais gerados com sucesso!")
        
        # Estatísticas do projeto
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Criativos Gerados", len(st.session_state.final_creatives))
        with col2:
            st.metric("Idiomas", len(LANGUAGES))
        with col3:
            st.metric("Esquemas de Cores", len(COLOR_SCHEMES))
        with col4:
            st.metric("Formatos", len(IMAGE_SIZES))
        
        # Filtros
        st.subheader("🔍 Filtros")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_language = st.selectbox("Idioma", ["Todos"] + list(LANGUAGES.values()))
        with col2:
            filter_color = st.selectbox("Esquema de Cores", ["Todos"] + list(COLOR_SCHEMES.keys()))
        with col3:
            filter_size = st.selectbox("Formato", ["Todos"] + list(IMAGE_SIZES.keys()))
        
        # Aplicar filtros
        filtered_creatives = st.session_state.final_creatives
        
        if filter_language != "Todos":
            lang_code = [k for k, v in LANGUAGES.items() if v == filter_language][0]
            filtered_creatives = [c for c in filtered_creatives if c["language"] == lang_code]
        
        if filter_color != "Todos":
            filtered_creatives = [c for c in filtered_creatives if c["color_scheme"] == filter_color]
        
        if filter_size != "Todos":
            filtered_creatives = [c for c in filtered_creatives if c["size"] == filter_size]
        
        # Mostrar criativos filtrados
        st.subheader(f"📱 Criativos ({len(filtered_creatives)} de {len(st.session_state.final_creatives)})")
        
        # Grid de criativos
        if filtered_creatives:
            cols = st.columns(2)
            for i, creative in enumerate(filtered_creatives):
                with cols[i % 2]:
                    # Informações do criativo
                    language_name = LANGUAGES[creative["language"]]
                    st.markdown(f"**{language_name} • {creative['color_scheme'].title()} • {creative['size']}**")
                    
                    # Mostrar imagem
                    if Path(creative["path"]).exists():
                        st.image(creative["path"], use_container_width=True)
                        
                        # Botão de download
                        with open(creative["path"], "rb") as f:
                            st.download_button(
                                f"⬇️ Download",
                                data=f,
                                file_name=creative["filename"],
                                mime="image/png",
                                key=f"download_{i}",
                                use_container_width=True
                            )
                    else:
                        st.error(f"Arquivo não encontrado: {creative['filename']}")
                    
                    st.divider()
        
        # Download em lote
        if st.button("📦 Download de Todos os Criativos", use_container_width=True):
            st.info("💡 Para download em lote, acesse a pasta 'outputs' do projeto")
            with st.expander("📂 Lista de Arquivos Gerados"):
                for creative in st.session_state.final_creatives:
                    st.code(creative["filename"])

def display_copy_editor(copy_data: Dict, language: str) -> Dict:
    """Exibe editor de copy para um idioma específico"""
    edited_copy = {}
    
    if not copy_data:
        st.warning(f"Copy não gerado para {language}")
        return edited_copy
    
    # Campos editáveis
    edited_copy["titulo_principal"] = st.text_input(
        "Título Principal", 
        value=copy_data.get("titulo_principal", ""),
        key=f"titulo_{language}"
    )
    
    edited_copy["subtitulo"] = st.text_input(
        "Subtítulo",
        value=copy_data.get("subtitulo", ""),
        key=f"subtitulo_{language}"
    )
    
    edited_copy["cta_principal"] = st.text_input(
        "CTA Principal",
        value=copy_data.get("cta_principal", ""),
        key=f"cta_{language}"
    )
    
    # Bullet points
    bullet_points = copy_data.get("bullet_points", ["", "", ""])
    edited_bullets = []
    for i, bullet in enumerate(bullet_points[:3]):
        edited_bullet = st.text_input(
            f"Benefício {i+1}",
            value=bullet,
            key=f"bullet_{language}_{i}"
        )
        if edited_bullet:
            edited_bullets.append(edited_bullet)
    
    edited_copy["bullet_points"] = edited_bullets
    edited_copy["urgencia"] = copy_data.get("urgencia", "")
    edited_copy["beneficio_principal"] = copy_data.get("beneficio_principal", "")
    edited_copy["footer_texto"] = copy_data.get("footer_texto", "")
    
    return edited_copy

def display_design_grid(designs: List[Dict], format_name: str):
    """Exibe grid de designs"""
    if not designs:
        st.warning(f"Nenhum design gerado para formato {format_name}")
        return
    
    # Organizar em grid de 2 colunas
    cols = st.columns(2)
    
    for i, design in enumerate(designs):
        with cols[i % 2]:
            st.markdown(f"**{design['color_scheme'].title()}**")
            
            if Path(design["path"]).exists():
                st.image(design["path"], use_container_width=True)
                
                # Mostrar cores do esquema
                colors_html = ""
                for color in design["colors"][:3]:
                    colors_html += f'<span style="background-color:{color}; width:20px; height:20px; display:inline-block; margin:2px; border-radius:50%;"></span>'
                st.markdown(colors_html, unsafe_allow_html=True)
            else:
                st.error(f"Arquivo não encontrado: {design['filename']}")
            
            st.divider()

if __name__ == "__main__":
    main()
