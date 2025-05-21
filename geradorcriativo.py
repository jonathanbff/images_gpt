#!/usr/bin/env python3
"""
geradorcriativo.py
Gera 3 variações criativas de uma imagem com diferentes cores e textos usando GPT-image-1.

Requisitos:
  pip install openai python-dotenv pillow

Uso:
  python geradorcriativo.py -i imagem.png
"""
import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from io import BytesIO
import re

from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv

# Configuração básica
load_dotenv()

MODEL_VISION = "gpt-4o-mini"
MODEL_TEXT = "gpt-4o-mini"
MODEL_IMAGE = "gpt-image-1"

OUT_DIR = Path("outputs")
DEFAULT_SIZE = "1024x1536"
DEFAULT_STYLE = "photorealistic"

client = OpenAI()

# Utilitários
def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}")

def image_to_base64(path):
    data = base64.b64encode(path.read_bytes()).decode()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{data}"

def ensure_size(img_bytes, w, h):
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()

# Analisador de imagem
def analisar_imagem(img_path):
    log("Analisando layout da imagem com reconhecimento detalhado de componentes")
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
    
    # Exemplo para compreensão do formato esperado
    example = """
    Exemplo de análise com texturas e iluminação:
    {
      "canvas_size": { "width": 768, "height": 1365 },
      "color_palette": ["#D90000", "#FFFFFF", "#F1F1F1", "#1F1F1F", "#05A874"],
      "textures": {
        "background": {
          "type": "radial-gradient",
          "colors": ["#D90000", "#8B0000"],
          "center": "top-center"
        },
        "credit_card": {
          "type": "fluid-marble",
          "colors": ["#D90000", "#FF4D4D", "#FFA3A3"],
          "direction": "diagonal",
          "intensity": "medium"
        },
        "button_unselected": {
          "type": "flat",
          "color": "#E0E0E0"
        },
        "button_selected": {
          "type": "glossy",
          "gradient": ["#D90000", "#A10000"]
        },
        "slider_track": {
          "type": "metallic",
          "color": "#CCCCCC"
        }
      },
      "lighting": {
        "card": {
          "type": "specular",
          "position": "top-right",
          "intensity": "high",
          "effect": "adds depth and gloss to card surface"
        },
        "background": {
          "type": "soft-glow",
          "position": "center",
          "intensity": "low",
          "effect": "focus user attention on content center"
        },
        "highlight_elements": {
          "targets": ["limit-amount", "15"],
          "effect": "subtle light bloom"
        }
      },
      "placeholders": [
        {
          "id": "background",
          "type": "background-shape",
          "role": "background",
          "style": {
            "fillColor": "gradient from textures.background"
          }
        },
        {
          "id": "credit-card-image",
          "type": "illustration",
          "role": "hero",
          "style": {
            "position": "top",
            "angle": "rotated (approx. -20 degrees)",
            "colors": ["#D90000", "#F83535"],
            "texture": "textures.credit_card",
            "features": ["chip", "contactless icon", "VISA logo"],
            "lighting": "lighting.card"
          }
        }
      ]
    }
    """
    
    # Primeira tentativa com temperatura 0 para máxima precisão
    res = client.chat.completions.create(
        model=MODEL_VISION,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": b64}},
                {"type": "text", "text": prompt}
            ]
        }],
        temperature=0,
        response_format={"type": "json_object"}  # Forçar formato JSON
    )
    
    content = res.choices[0].message.content
    
    try:
        # Tentar parsear diretamente como JSON
        result = json.loads(content)
        log("✓ Análise JSON obtida com sucesso")
        return result
    except json.JSONDecodeError as e:
        log(f"⚠️ Erro ao decodificar JSON: {str(e)}")
        
        # Tentar extrair apenas a parte JSON da resposta
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            try:
                json_content = content[json_start:json_end]
                result = json.loads(json_content)
                log("✓ JSON extraído com sucesso da resposta parcial")
                return result
            except json.JSONDecodeError:
                log("⚠️ Falha ao extrair JSON da resposta")
        
        # Segunda tentativa com um prompt simplificado
        log("🔄 Tentando nova abordagem com prompt simplificado")
        
        # Prompt simplificado focado apenas nos elementos essenciais
        simple_prompt = """
        Analise esta imagem e extraia apenas:
        1. Dimensões em pixels
        2. Elementos principais (textos, formas, botões)
        3. Cores predominantes com códigos hexadecimais
        
        Retorne APENAS um objeto JSON válido com esta estrutura simples:
        {
            "canvas_size": {"w": W, "h": H},
            "placeholders": [
                {"id": "1", "type": "text", "value": "texto", "bbox": [x, y, w, h]},
                {"id": "2", "type": "shape", "value": "#HEX", "bbox": [x, y, w, h]},
                {"id": "3", "type": "button", "value": "texto do botão", "bbox": [x, y, w, h]}
            ],
            "color_palette": ["#HEX1", "#HEX2", "#HEX3"]
        }
        
        NÃO inclua explicações ou texto fora do JSON. Apenas o objeto JSON válido.
        """
        
        res2 = client.chat.completions.create(
            model=MODEL_VISION,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": b64}},
                    {"type": "text", "text": simple_prompt}
                ]
            }],
            temperature=0,
            response_format={"type": "json_object"}  # Forçar formato JSON
        )
        
        content2 = res2.choices[0].message.content
        
        try:
            # Tentar parsear a segunda resposta
            result = json.loads(content2)
            log("✓ Análise obtida com prompt simplificado")
            
            # Converter o formato simples para o formato esperado
            if "color_palette" in result and isinstance(result["color_palette"], list) and len(result["color_palette"]) > 0:
                result["color_palette"] = {
                    "primary": result["color_palette"][0],
                    "secondary": result["color_palette"][1] if len(result["color_palette"]) > 1 else result["color_palette"][0],
                    "accent": result["color_palette"][2] if len(result["color_palette"]) > 2 else result["color_palette"][0],
                    "text": "#FFFFFF",  # Valor padrão
                    "background": result["color_palette"][0],
                    "all_colors": result["color_palette"]
                }
            
            # Adicionar layout mínimo
            result["layout"] = {
                "background": result["color_palette"]["primary"] if isinstance(result["color_palette"], dict) else "#FFFFFF",
                "grid_structure": "layout padrão",
                "margins": [10, 10, 10, 10],
                "visual_flow": "topo para baixo"
            }
            
            # Adicionar estilo mínimo
            result["style"] = {
                "typography": "sans-serif padrão",
                "visual_style": "corporativo padrão",
                "effects": []
            }
            
            return result
        except json.JSONDecodeError:
            # Se todas as tentativas falharem, criar um modelo básico a partir da resposta textual
            log("⚠️ Criando modelo básico a partir da análise textual")
            
            # Extrair informações básicas do texto
            colors = re.findall(r'#[0-9A-Fa-f]{6}', content + content2)
            texts = re.findall(r'"([^"]+)"', content + content2)
            
            # Criar um modelo básico com informações extraídas
            basic_model = {
                "canvas_size": {"w": 1024, "h": 1536},  # Tamanhos padrão
                "placeholders": [],
                "color_palette": {
                    "primary": colors[0] if colors else "#800080",  # Roxo padrão da imagem de exemplo
                    "secondary": colors[1] if len(colors) > 1 else "#FFFFFF",
                    "accent": colors[2] if len(colors) > 2 else "#FFA500",
                    "text": "#FFFFFF",
                    "background": colors[0] if colors else "#800080",
                    "all_colors": colors if colors else ["#800080", "#FFFFFF", "#FFA500"]
                },
                "layout": {
                    "background": colors[0] if colors else "#800080",
                    "grid_structure": "layout padrão",
                    "margins": [10, 10, 10, 10],
                    "visual_flow": "topo para baixo"
                },
                "style": {
                    "typography": "sans-serif padrão",
                    "visual_style": "corporativo padrão",
                    "effects": []
                },
                "raw_analysis": content  # Guardar a análise original para referência
            }
            
            # Adicionar textos encontrados como placeholders
            for i, text in enumerate(texts[:5]):  # Limitar a 5 textos
                if len(text) > 3:  # Ignorar textos muito curtos
                    basic_model["placeholders"].append({
                        "id": str(i+1),
                        "type": "text",
                        "value": text,
                        "bbox": [10, 100 + i*100, 800, 50],  # Posição estimada
                        "font": {
                            "color": "#FFFFFF",
                            "size": 16,
                            "family": "sans-serif",
                            "weight": "normal",
                            "alignment": "left",
                            "style": "normal"
                        },
                        "layer": 1,
                        "description": f"Texto {i+1}",
                        "visual_hierarchy": "primário" if i == 0 else "secundário"
                    })
            
            # Adicionar formas básicas
            basic_model["placeholders"].append({
                "id": str(len(basic_model["placeholders"])+1),
                "type": "shape",
                "shape_type": "retângulo",
                "value": basic_model["color_palette"]["primary"],
                "bbox": [0, 0, 1024, 768],
                "opacity": 1.0,
                "border": {"color": "none", "width": 0},
                "corners": "reto",
                "shadow": False,
                "layer": 0,
                "description": "Fundo principal"
            })
            
            # Adicionar botão
            basic_model["placeholders"].append({
                "id": str(len(basic_model["placeholders"])+1),
                "type": "button",
                "value": "PEÇA JÁ!",
                "bbox": [300, 800, 400, 80],
                "colors": {"bg": basic_model["color_palette"]["accent"], "text": "#FFFFFF"},
                "corners": "arredondado",
                "description": "Botão de call-to-action"
            })
            
            return basic_model

# Gerador de variações
def gerar_variacoes(spec, num_variacoes=3):
    log("Gerando variações textuais e de cores com preservação rigorosa da estrutura compositiva")
    
    prompt = f"""
    Com base nesta análise DETALHADA da imagem, crie {num_variacoes} variações com novos textos, esquemas de cores e texturas, 
    PRESERVANDO RIGOROSAMENTE a composição e estrutura de design originais.
    
    REGRAS CRUCIAIS PARA PRESERVAÇÃO DA IDENTIDADE VISUAL:
    1. ESTRUTURA COMPOSITIVA: Mantenha EXATAMENTE a mesma distribuição espacial, grid, hierarquia visual e fluxo de leitura
    2. ELEMENTOS GRÁFICOS PRINCIPAIS: Preserve todas as formas e elementos estruturais em suas posições e proporções originais
    3. TIPOGRAFIA: Mantenha o mesmo estilo tipográfico, pesos, tamanhos relativos e hierarquia entre textos
    4. LOGOTIPOS: Preserve intactos em posição, tamanho e proporção
    
    ELEMENTOS QUE PODEM SER ALTERADOS:
    1. CORES: Crie paletas harmonicamente derivadas da original usando:
       - Tons análogos (cores adjacentes no círculo cromático)
       - Tons complementares (cores opostas no círculo cromático) 
       - Variações monocromáticas (diferentes luminosidades da mesma cor)
       - Preserve sempre o contraste e legibilidade originais
    
    2. TEXTURAS: Modifique texturas mantendo a identidade visual:
       - Substitua entre tipos compatíveis (gradiente→gradiente, flat→flat)
       - Alterne entre texturas planas, gradientes, metálicas ou marmorizadas
       - Aplique variações nas propriedades da textura como direção ou intensidade
       - Mantenha compatibilidade com o elemento e sua função na composição
    
    3. TEXTOS: Altere apenas o conteúdo textual mantendo:
       - Mesmo tom comunicativo e registro linguístico
       - Comprimento similar (número de caracteres, linhas)
       - Mesmo propósito comunicativo de cada texto
       - Mesma hierarquia de informação
    
    4. EFEITOS DE ILUMINAÇÃO: Modifique com sutileza:
       - Altere a direção ou intensidade da iluminação
       - Adicione ou remova brilhos sutis
       - Ajuste reflexos em elementos com superfícies brilhantes
       - Mantenha a legibilidade e clareza da informação
    
    5. PEQUENOS DETALHES DECORATIVOS: Apenas elementos não-estruturais como:
       - Texturas sutis
       - Ícones secundários (mantendo estilo e função)
       - Efeitos de sombra ou brilho
    
    Use o seguinte formato JSON:
    
    {{
      "variacoes": [
        {{
          "id": "variacao1",
          "cores": {{
            "primaria": "#HEX1",
            "secundaria": "#HEX2", 
            "destaque": "#HEX3",
            "background": "#HEX4",
            "texto": "#HEX5",
            "derivacao": "análoga/complementar/monocromática"
          }},
          "texturas": {{
            "background": {{
              "type": "tipo-de-textura", 
              "colors": ["#HEX1", "#HEX2"],
              "direction": "direção",
              "intensity": "intensidade"
            }},
            "elementos_principais": {{
              "type": "tipo-de-textura",
              "colors": ["#HEX1", "#HEX2"]
            }},
            "botoes": {{
              "type": "tipo-de-textura",
              "colors": ["#HEX1", "#HEX2"]
            }}
          }},
          "iluminacao": {{
            "principal": {{
              "type": "tipo-de-iluminacao",
              "position": "posição",
              "intensity": "intensidade"
            }},
            "destaques": [
              "elemento1", "elemento2"
            ]
          }},
          "textos": {{
            "1": "Novo texto para o elemento 1",
            "2": "Novo texto para o elemento 2",
            "3": "Novo texto para o elemento 3"
          }},
          "ideia_grafica": "Descrição EXTREMAMENTE DETALHADA da variação, especificando: 1. A estrutura EXATA mantida da imagem original (grid, layout, alinhamentos) 2. CADA elemento visual e sua posição preservada 3. As alterações ESPECÍFICAS de cores (com códigos HEX precisos) e texturas 4. As alterações textuais e seu impacto visual 5. Detalhes de refinamento estético permitidos 6. Instruções EXPLÍCITAS para manter proporções, tamanhos e espaçamentos originais"
        }},
        ... mais variações ...
      ]
    }}
    
    IMPORTANTE:
    - Analise METICULOSAMENTE todos os detalhes da composição original antes de propor variações
    - Para cada elemento visual, determine explicitamente o que será mantido vs. alterado
    - Crie variações que pareçam pertencer à mesma família visual/marca, apenas com leves alterações
    - Inclua na descrição gráfica referências numéricas exatas (posições, tamanhos, proporções)
    """
    
    try:
        res = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[{"role": "system", "content": prompt},
                     {"role": "user", "content": json.dumps(spec, ensure_ascii=False, indent=2)}],
            temperature=0.7,
            response_format={"type": "json_object"}  # Forçar formato JSON
        )
        
        content = res.choices[0].message.content
        
        try:
            # Tentar parsear diretamente como JSON
            result = json.loads(content)
            log("✓ Variações geradas com sucesso")
            return result
        except json.JSONDecodeError as e:
            log(f"⚠️ Erro ao decodificar JSON das variações: {str(e)}")
            
            # Tentar extrair apenas a parte JSON da resposta
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)
                    log("✓ JSON de variações extraído com sucesso da resposta parcial")
                    return result
                except json.JSONDecodeError:
                    log("⚠️ Falha ao extrair JSON das variações")
    except Exception as e:
        log(f"⚠️ Erro ao chamar API para variações: {str(e)}")
    
    # Se todas as tentativas falharem, criar variações básicas
    log("ℹ️ Criando variações básicas automaticamente")
    
    # Extrair cores da paleta original
    colors = spec.get("color_palette", {})
    if isinstance(colors, dict):
        primary = colors.get("primary", "#800080")  # Roxo padrão
        secondary = colors.get("secondary", "#FFFFFF")
        accent = colors.get("accent", "#FFA500")
    elif isinstance(colors, list) and len(colors) > 0:
        primary = colors[0]
        secondary = colors[1] if len(colors) > 1 else "#FFFFFF"
        accent = colors[2] if len(colors) > 2 else "#FFA500"
    else:
        primary, secondary, accent = "#800080", "#FFFFFF", "#FFA500"
    
    # Gerar paletas de cores derivadas
    paletas = [
        # Original com pequenas variações
        {
            "primaria": primary,
            "secundaria": secondary,
            "destaque": accent,
            "background": primary,
            "texto": "#FFFFFF",
            "derivacao": "original"
        },
        # Análoga
        {
            "primaria": shift_hue(primary, 30),
            "secundaria": shift_hue(secondary, 15),
            "destaque": shift_hue(accent, 45),
            "background": shift_hue(primary, 30),
            "texto": "#FFFFFF",
            "derivacao": "análoga"
        },
        # Complementar
        {
            "primaria": shift_hue(primary, 180),
            "secundaria": shift_hue(secondary, 180),
            "destaque": accent,
            "background": shift_hue(primary, 180),
            "texto": "#FFFFFF",
            "derivacao": "complementar"
        }
    ]
    
    # Extrair textos originais dos placeholders
    textos_originais = {}
    for p in spec.get("placeholders", []):
        if p.get("type") == "text" and "value" in p:
            textos_originais[p["id"]] = p["value"]
    
    # Gerar alternativas de texto simples (baseado no tipo do elemento)
    textos_alternativos = {}
    for id, texto in textos_originais.items():
        if "empréstimo" in texto.lower() or "r$" in texto.lower():
            textos_alternativos[id] = [
                "Crédito de até R$ 5.000*",
                "Empréstimo facilitado",
                "Dinheiro na hora para você"
            ]
        elif "cpf" in texto.lower():
            textos_alternativos[id] = [
                "Apenas com seu CPF*",
                "Sem burocracia e rápido",
                "Processo 100% digital"
            ]
        elif "prazo" in texto.lower() or "meses" in texto.lower():
            textos_alternativos[id] = [
                "9 meses",
                "15 meses",
                "18 meses"
            ]
        elif "peça" in texto.lower() or "faça" in texto.lower() or "já" in texto.lower():
            textos_alternativos[id] = [
                "SOLICITE AGORA!",
                "CLIQUE AQUI!",
                "QUERO AGORA!"
            ]
        else:
            textos_alternativos[id] = [
                f"Novo texto {id}",
                f"Alternativa {id}",
                f"Variação {id}"
            ]
    
    # Montar as variações
    variacoes = []
    for i in range(min(num_variacoes, 3)):  # Limitar a 3 variações
        textos = {}
        for id in textos_originais:
            opcoes = textos_alternativos.get(id, [f"Texto {id}"])
            textos[id] = opcoes[i % len(opcoes)]
        
        variacoes.append({
            "id": f"variacao{i+1}",
            "cores": paletas[i],
            "textos": textos,
            "ideia_grafica": (
                f"Manter rigorosamente a mesma composição, estrutura e layout da imagem original. "
                f"Alterar apenas: 1) esquema de cores para a paleta {paletas[i]['derivacao']} indicada, "
                f"2) textos conforme especificado, mantendo mesma fonte, peso e alinhamento. "
                f"Preservar todas as posições, tamanhos, proporções e a hierarquia visual original."
            )
        })
    
    return {"variacoes": variacoes}

# Utilidade para manipulação de cores
def shift_hue(hex_color, degrees):
    """Desloca o matiz de uma cor em X graus no círculo cromático"""
    # Remover # se presente
    hex_color = hex_color.lstrip('#')
    
    # Converter hex para RGB
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    # Converter RGB para HSL
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2
    
    if max_c == min_c:
        h = s = 0  # acromático
    else:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
        
        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        
        h /= 6
    
    # Deslocar o matiz
    h = (h + degrees/360) % 1
    
    # Converter HSL de volta para RGB
    if s == 0:
        r = g = b = l  # acromático
    else:
        def hue_to_rgb(p, q, t):
            t %= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)
    
    # Converter RGB de volta para hex
    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255), int(g * 255), int(b * 255)
    )

# Gerador de imagens
def gerar_imagens(variacoes, spec, size=DEFAULT_SIZE, style=DEFAULT_STYLE):
    log("Gerando criativos otimizados para marketing digital e plataformas sociais")
    
    w, h = map(int, size.split("x"))
    resultados = []
    
    # Determinar plataforma com base no tamanho
    if size == "1024x1536":
        platform_type = "Facebook Feed/Stories (formato vertical)"
    elif size == "1536x1024":
        platform_type = "Google Display (formato horizontal)"
    elif size == "1024x1024":
        platform_type = "Instagram (formato quadrado)"
    else:
        platform_type = "Redes Sociais (formato padrão)"
    
    for i, v in enumerate(variacoes):
        # Compatibilidade com diferentes formatos de cores
        if isinstance(v.get("cores"), dict):
            # Novo formato (dicionário)
            cores = v["cores"]
            cores_str = f"primária {cores.get('primaria', '#FFFFFF')} (80% da superfície), secundária {cores.get('secundaria', '#CCCCCC')} (detalhes), " \
                       f"destaque {cores.get('destaque', '#FF0000')} (CTA e pontos focais), texto {cores.get('texto', '#000000')}"
        elif isinstance(v.get("cores"), list) and len(v["cores"]) > 0:
            # Formato antigo (lista)
            cores = {
                "primaria": v["cores"][0],
                "secundaria": v["cores"][1] if len(v["cores"]) > 1 else v["cores"][0],
                "destaque": v["cores"][2] if len(v["cores"]) > 2 else v["cores"][0],
                "texto": "#FFFFFF",
                "background": v["cores"][0]
            }
            cores_str = ", ".join(v["cores"])
        else:
            # Fallback para caso não haja cores definidas
            cores = {
                "primaria": "#800080",  # Roxo padrão
                "secundaria": "#FFFFFF",
                "destaque": "#FFA500",
                "texto": "#FFFFFF",
                "background": "#800080"
            }
            cores_str = "cores padrão"
        
        # Extrair definições de textura, se disponíveis
        texturas_str = ""
        if "texturas" in v and isinstance(v["texturas"], dict):
            texturas = v["texturas"]
            
            # Textura de fundo
            if "background" in texturas:
                bg_texture = texturas["background"]
                bg_colors = ", ".join(bg_texture.get("colors", [cores.get("background", "#800080")]))
                texturas_str += f"""
                TEXTURA DE FUNDO:
                - Tipo: {bg_texture.get('type', 'plana')}
                - Cores: {bg_colors}
                - Direção: {bg_texture.get('direction', 'não especificada')}
                - Intensidade: {bg_texture.get('intensity', 'média')}
                """
            
            # Textura dos elementos principais
            if "elementos_principais" in texturas:
                elem_texture = texturas["elementos_principais"]
                elem_colors = ", ".join(elem_texture.get("colors", [cores.get("primaria", "#800080")]))
                texturas_str += f"""
                TEXTURA DOS ELEMENTOS PRINCIPAIS:
                - Tipo: {elem_texture.get('type', 'plana')}
                - Cores: {elem_colors}
                """
            
            # Textura dos botões
            if "botoes" in texturas:
                btn_texture = texturas["botoes"]
                btn_colors = ", ".join(btn_texture.get("colors", [cores.get("destaque", "#FFA500")]))
                texturas_str += f"""
                TEXTURA DOS BOTÕES:
                - Tipo: {btn_texture.get('type', 'plana')}
                - Cores: {btn_colors}
                """
        else:
            # Usar texturas do spec original se disponíveis
            if "textures" in spec:
                spec_textures = spec["textures"]
                texturas_str = "TEXTURAS DA COMPOSIÇÃO:\n"
                
                for key, texture in spec_textures.items():
                    if isinstance(texture, dict):
                        texture_type = texture.get('type', 'não especificada')
                        texture_colors = ", ".join(texture.get('colors', [])) if 'colors' in texture else texture.get('color', 'não especificada')
                        texturas_str += f"- {key}: tipo {texture_type}, cores {texture_colors}\n"
            else:
                # Fallback para texturas básicas baseadas nas cores
                texturas_str = """
                TEXTURAS BÁSICAS:
                - Fundo: gradiente suave com cor primária
                - Elementos de destaque: acabamento brilhante
                - Botões: efeito glossy para destacar área clicável
                """
        
        # Extrair definições de iluminação, se disponíveis
        iluminacao_str = ""
        if "iluminacao" in v and isinstance(v["iluminacao"], dict):
            ilum = v["iluminacao"]
            
            # Iluminação principal
            if "principal" in ilum:
                main_light = ilum["principal"]
                iluminacao_str += f"""
                ILUMINAÇÃO PRINCIPAL:
                - Tipo: {main_light.get('type', 'ambiente')}
                - Posição: {main_light.get('position', 'superior-direita')}
                - Intensidade: {main_light.get('intensity', 'média')}
                """
            
            # Elementos destacados
            if "destaques" in ilum and isinstance(ilum["destaques"], list):
                destaques = ", ".join(ilum["destaques"])
                iluminacao_str += f"""
                ELEMENTOS COM DESTAQUE DE LUZ:
                - {destaques}
                """
        else:
            # Usar iluminação do spec original se disponível
            if "lighting" in spec:
                spec_lighting = spec["lighting"]
                iluminacao_str = "ILUMINAÇÃO DA COMPOSIÇÃO:\n"
                
                for key, light in spec_lighting.items():
                    if isinstance(light, dict):
                        light_type = light.get('type', 'não especificada')
                        light_position = light.get('position', 'não especificada')
                        light_intensity = light.get('intensity', 'média')
                        iluminacao_str += f"- {key}: tipo {light_type}, posição {light_position}, intensidade {light_intensity}\n"
            else:
                # Fallback para iluminação básica
                iluminacao_str = """
                ILUMINAÇÃO BÁSICA:
                - Luz principal: superior-direita, ambiente
                - Destaque sutil nos elementos de conversão (CTA, valores)
                """
                
        # Obter uma referência ao layout original através dos dados em spec
        layout_original = "Grid original estruturado"
        if "layout" in spec and "grid_structure" in spec["layout"]:
            layout_original = f"Grid original: {spec['layout']['grid_structure']}"
            
        estilo_original = "Estilo corporativo"
        if "style" in spec and "visual_style" in spec["style"]:
            estilo_original = f"Estilo visual: {spec['style']['visual_style']}"
        
        prompt = f"""
        Gere um ANÚNCIO DIGITAL OTIMIZADO para {platform_type} com as seguintes especificações:
        
        DIMENSÕES E FORMATO:
        - Proporção: {size} (formato otimizado para {platform_type})
        - Estilo: {style} com apelo visual para marketing digital
        
        ESQUEMA DE CORES PARA MARKETING:
        {cores_str}
        
        TEXTURAS E TRATAMENTOS DE SUPERFÍCIE:
        {texturas_str}
        
        EFEITOS DE ILUMINAÇÃO E DESTAQUES:
        {iluminacao_str}
        
        INSTRUÇÕES PARA PRESERVAÇÃO DA ESTRUTURA CONVERSORA:
        1. Mantenha a mesma estrutura compositiva e fluxo visual que leva ao CTA
        2. Preserve a hierarquia de informações que comunica claramente a proposta de valor
        3. Mantenha os elementos em posições que otimizam a jornada visual do usuário
        4. Crie um visual que capture atenção nos primeiros 2 segundos de visualização
        5. Garanta que todo texto seja perfeitamente legível em telas pequenas
        6. Otimize o contraste e impacto visual para alto CTR (taxa de cliques)
        7. Aplique as texturas e iluminações especificadas para criar profundidade visual
        
        OTIMIZAÇÕES PARA PLATAFORMAS DIGITAIS:
        - Garanta alta legibilidade em scroll rápido de feed social
        - Crie apelo visual imediato para audiências com atenção fragmentada
        - Torne a proposta de valor clara e impactante visualmente
        - Direcione o olhar para o botão CTA de forma natural
        - Mantenha densidade de informação ideal para marketing digital
        - Use texturas para criar diferenciação e memorabilidade da marca
        - Aplique iluminação para destacar elementos-chave de conversão
        
        DESCRIÇÃO DO CRIATIVO:
        {v.get("ideia_grafica", "Manter a estrutura compositiva original, adaptada para alto desempenho em marketing digital.")}
        
        ELEMENTOS ESPECÍFICOS DO ANÚNCIO:
        """
        
        # Adicionar detalhes de cada elemento com instruções específicas para marketing digital
        if "placeholders" in spec:
            for p in spec["placeholders"]:
                # Compatibilidade com diversos tipos de elementos
                element_type = p.get("type", "elemento").lower()
                
                if element_type == "text":
                    # Obter propriedades detalhadas do texto original
                    font_props = p.get("font", {})
                    font_style = f"família '{font_props.get('family', 'original')}', " \
                               f"peso {font_props.get('weight', 'original')}, " \
                               f"alinhamento {font_props.get('alignment', 'original')}"
                    
                    # Obter o novo texto para este elemento ou manter o original
                    texto = v.get("textos", {}).get(p["id"], p.get("value", "Texto"))
                    
                    # Determinar função de marketing baseada na hierarquia visual
                    hierarchy = p.get('visual_hierarchy', '').lower()
                    if "primário" in hierarchy or p["id"] == "1":
                        marketing_role = "HEADLINE PRINCIPAL (proposta de valor central)"
                    elif "secundário" in hierarchy:
                        marketing_role = "SUBHEADLINE (benefício ou detalhamento)"
                    else:
                        marketing_role = "TEXTO DE SUPORTE (informação complementar)"
                    
                    # Obter efeitos de iluminação para este elemento, se especificados
                    light_effect = ""
                    if "iluminacao" in v and "destaques" in v["iluminacao"] and p["id"] in v["iluminacao"]["destaques"]:
                        light_effect = "\n      * Efeito de luz: destaque luminoso sutil para atrair atenção"
                    elif "lighting" in spec and "highlight_elements" in spec["lighting"] and "targets" in spec["lighting"]["highlight_elements"] and p["id"] in spec["lighting"]["highlight_elements"]["targets"]:
                        light_effect_desc = spec["lighting"]["highlight_elements"].get("effect", "destaque luminoso")
                        light_effect = f"\n      * Efeito de luz: {light_effect_desc}"
                    
                    prompt += f"""
                    - {marketing_role} adaptado para {platform_type}:
                      * Conteúdo: "{texto}"
                      * Formatação: {font_style}
                      * Cor: {cores.get("texto", font_props.get("color", "#FFFFFF"))}{light_effect}
                      * IMPORTANTE: Alta legibilidade em dispositivos móveis, impacto visual imediato
                    """
                
                elif element_type == "button":
                    # Obter o texto do botão e sua cor
                    btn_text = v.get("textos", {}).get(p["id"], p.get("value", "Botão"))
                    btn_colors = p.get("colors", {})
                    btn_bg = cores.get("destaque", btn_colors.get("bg", "#FFA500"))
                    btn_text_color = cores.get("texto", btn_colors.get("text", "#FFFFFF"))
                    
                    # Obter textura do botão
                    btn_texture = ""
                    if "texturas" in v and "botoes" in v["texturas"]:
                        texture_type = v["texturas"]["botoes"].get("type", "glossy")
                        btn_texture = f"\n      * Textura: {texture_type} para maximizar apelo de clique"
                    elif "textures" in spec and "button_selected" in spec["textures"]:
                        texture_type = spec["textures"]["button_selected"].get("type", "glossy")
                        btn_texture = f"\n      * Textura: {texture_type} para destacar área clicável"
                    
                    # Obter efeito de luz no botão
                    btn_light = ""
                    if "iluminacao" in v and "destaques" in v["iluminacao"] and p["id"] in v["iluminacao"]["destaques"]:
                        btn_light = "\n      * Efeito de luz: brilho sutil nas bordas para aumentar CTR"
                    
                    prompt += f"""
                    - BOTÃO CTA adaptado para {platform_type}:
                      * Texto: "{btn_text}"
                      * Cor de fundo: {btn_bg} (cor de destaque para maximizar CTR)
                      * Cor do texto: {btn_text_color}{btn_texture}{btn_light}
                      * Cantos: {p.get('corners', 'arredondados')}
                      * IMPORTANTE: Visual que incentiva o clique, com alto contraste e apelo visual
                    """
                
                elif element_type == "shape":
                    # Detalhes da forma
                    shape_type = p.get("shape_type", "forma")
                    corners = p.get("corners", "original")
                    opacity = p.get("opacity", 1.0)
                    
                    # Determinar a cor da forma com base na sua função
                    description = p.get("description", "").lower()
                    if "fundo" in description or "background" in description:
                        cor = cores.get("background", p.get("value", cores["primaria"]))
                        shape_role = "FUNDO PRINCIPAL (cria identidade visual do anúncio)"
                        
                        # Textura do fundo
                        bg_texture = ""
                        if "texturas" in v and "background" in v["texturas"]:
                            texture_type = v["texturas"]["background"].get("type", "gradient")
                            texture_direction = v["texturas"]["background"].get("direction", "radial")
                            bg_texture = f"\n      * Textura: {texture_type} {texture_direction}"
                        elif "textures" in spec and "background" in spec["textures"]:
                            texture_type = spec["textures"]["background"].get("type", "gradient")
                            texture_direction = spec["textures"]["background"].get("direction", "radial")
                            bg_texture = f"\n      * Textura: {texture_type} {texture_direction}"
                        
                    elif "destaque" in description or "accent" in description:
                        cor = cores.get("destaque", p.get("value", cores["destaque"]))
                        shape_role = "ELEMENTO DE DESTAQUE (direciona atenção)"
                        bg_texture = ""
                        
                        # Textura de elemento de destaque
                        if "texturas" in v and "elementos_principais" in v["texturas"]:
                            texture_type = v["texturas"]["elementos_principais"].get("type", "flat")
                            bg_texture = f"\n      * Textura: {texture_type}"
                        elif "texture" in p:
                            texture_type = p["texture"].get("type", "flat")
                            bg_texture = f"\n      * Textura: {texture_type}"
                    else:
                        cor = cores.get("primaria", p.get("value", cores["primaria"]))
                        shape_role = "ELEMENTO ESTRUTURAL (define estrutura do layout)"
                        bg_texture = ""
                        
                        # Textura de elemento estrutural
                        if "texturas" in v and "elementos_principais" in v["texturas"]:
                            texture_type = v["texturas"]["elementos_principais"].get("type", "flat")
                            bg_texture = f"\n      * Textura: {texture_type}"
                        elif "texture" in p:
                            texture_type = p["texture"].get("type", "flat")
                            bg_texture = f"\n      * Textura: {texture_type}"
                    
                    prompt += f"""
                    - {shape_role} adaptado ao formato {platform_type}:
                      * Cor: {cor}
                      * Tipo: {shape_type}
                      * Cantos: {corners}
                      * Opacidade: {opacity}{bg_texture}
                      * IMPORTANTE: Criar impacto visual alinhado com padrões de plataformas sociais
                    """
                
                elif element_type in ["image", "icon", "logo"]:
                    element_name = element_type.upper()
                    
                    if element_type == "logo":
                        element_desc = "LOGO DA MARCA (identidade visual, reconhecimento)"
                    elif element_type == "icon":
                        element_desc = "ÍCONE (comunicação visual rápida)"
                    else:
                        element_desc = "IMAGEM (elemento visual de impacto)"
                    
                    # Verificar se há textura especificada para o elemento
                    img_texture = ""
                    if "style" in p and "texture" in p["style"]:
                        texture_ref = p["style"]["texture"]
                        if texture_ref.startswith("textures.") and texture_ref[9:] in spec.get("textures", {}):
                            texture_name = texture_ref[9:]
                            texture_info = spec["textures"][texture_name]
                            texture_type = texture_info.get("type", "flat")
                            img_texture = f"\n      * Textura: {texture_type}"
                    elif element_type == "image" and "texturas" in v and "elementos_principais" in v["texturas"]:
                        texture_type = v["texturas"]["elementos_principais"].get("type", "flat")
                        img_texture = f"\n      * Textura: {texture_type}"
                    
                    # Verificar se há efeito de luz especificado
                    img_light = ""
                    if "style" in p and "lighting" in p["style"]:
                        light_ref = p["style"]["lighting"]
                        if light_ref.startswith("lighting.") and light_ref[9:] in spec.get("lighting", {}):
                            light_name = light_ref[9:]
                            light_info = spec["lighting"][light_name]
                            light_type = light_info.get("type", "ambient")
                            light_intensity = light_info.get("intensity", "medium")
                            img_light = f"\n      * Iluminação: {light_type}, intensidade {light_intensity}"
                    elif "iluminacao" in v and "destaques" in v["iluminacao"] and p["id"] in v["iluminacao"]["destaques"]:
                        img_light = "\n      * Iluminação: destaque suave para atrair atenção"
                    
                    prompt += f"""
                    - {element_desc} adaptado para {platform_type}:
                      * Descrição: {p.get('description', 'elemento visual')}{img_texture}{img_light}
                      * IMPORTANTE: Visual claro e impactante mesmo em tamanhos reduzidos, otimizado para feed social
                    """
                
                else:
                    # Elemento genérico desconhecido
                    prompt += f"""
                    - ELEMENTO DE MARKETING adaptado para {platform_type}:
                      * Tipo: {element_type}
                      * IMPORTANTE: Otimizar para apelo visual e contribuição para jornada de conversão
                    """
        
        log(f" → Gerando criativo {v['id']} otimizado para {platform_type}")
        
        try:
            res = client.images.generate(
                model=MODEL_IMAGE,
                prompt=prompt,
                size=size,
                quality="auto",
                n=1
            )
            
            img_b64 = res.data[0].b64_json
            fixed = ensure_size(base64.b64decode(img_b64), w, h)
            # Nome do arquivo com formato normalizado
            safe_platform = platform_type.split()[0].lower()
            out = OUT_DIR / f"{v['id']}_{safe_platform}.png"
            out.write_bytes(fixed)
            
            resultados.append({
                "id": v['id'],
                "plataforma": platform_type,
                "tamanho": size,
                "arquivo": str(out),
                "prompt": prompt
            })
        except Exception as e:
            log(f"⚠️ Erro ao gerar criativo {v['id']} para {platform_type}: {str(e)}")
            # Salvar o prompt problemático para diagnóstico
            safe_platform = platform_type.split()[0].lower()
            error_file = OUT_DIR / f"error_{v['id']}_{safe_platform}_prompt.txt"
            error_file.write_text(prompt, encoding="utf-8")
            log(f"  Prompt salvo em {error_file}")
    
    return resultados

def main():
    parser = argparse.ArgumentParser(description="Gerador de criativos para marketing digital (Facebook/Instagram/Google Ads)")
    parser.add_argument("-i", "--image", required=True, help="Imagem de referência para o criativo")
    parser.add_argument("-n", "--num", type=int, default=3, help="Número de variações de criativo (padrão: 3)")
    parser.add_argument("--size", default=DEFAULT_SIZE, 
                       choices=["1024x1024", "1024x1536", "1536x1024", "auto"],
                       help="Tamanho suportado pelo modelo de imagem")
    parser.add_argument("--style", default=DEFAULT_STYLE, 
                       choices=["photorealistic", "flat", "3d", "cartoon"],
                       help="Estilo visual dos criativos de marketing")
    parser.add_argument("--platform", default="all", 
                       choices=["all", "facebook", "instagram", "google", "story"],
                       help="Plataforma de destino para os criativos")
    parser.add_argument("--force", action="store_true", 
                       help="Força o processamento mesmo com análise incompleta")
    
    args = parser.parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("❌ Defina OPENAI_API_KEY no ambiente")
    
    img_path = Path(args.image)
    if not img_path.exists():
        sys.exit(f"❌ Arquivo não encontrado: {img_path}")
    
    # Pipeline de processamento
    log(f"🔍 Iniciando análise da peça publicitária: {img_path}")
    spec = analisar_imagem(img_path)
    
    # Verificar se temos análise suficiente para prosseguir
    if "raw_analysis" in spec:
        log("⚠️ Usando análise simplificada (modelo básico)")
        if not args.force:
            log("💡 Use --force para continuar mesmo com análise simplificada")
            (OUT_DIR / "analise_parcial.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            log(f"🔄 Análise parcial salva em {OUT_DIR}/analise_parcial.json")
            sys.exit("❌ Análise incompleta. Verifique a imagem e tente novamente.")
        log("⚙️ Continuando com modelo básico (--force)")
    
    elementos_count = len(spec.get("placeholders", []))
    log(f"✓ Análise concluída: identificados {elementos_count} elementos no criativo")
    
    log(f"🎨 Gerando {args.num} variações otimizadas para marketing digital")
    var_pack = gerar_variacoes(spec, args.num)
    
    if "error" in var_pack:
        sys.exit(f"❌ {var_pack['error']}")
    
    variacoes = var_pack.get("variacoes", [])
    log(f"✓ Planejamento concluído: {len(variacoes)} versões de anúncios definidas")
    
    # Usar um tamanho compatível com base na plataforma
    if args.platform == "facebook":
        size = "1024x1536"  # Vertical para Facebook
        log(f"ℹ️ Usando tamanho {size} para Facebook")
    elif args.platform == "instagram":
        size = "1024x1024"  # Quadrado para Instagram
        log(f"ℹ️ Usando tamanho {size} para Instagram")
    elif args.platform == "google":
        size = "1536x1024"  # Horizontal para Google
        log(f"ℹ️ Usando tamanho {size} para Google")
    elif args.platform == "story":
        size = "1024x1536"  # Vertical para Stories
        log(f"ℹ️ Usando tamanho {size} para Stories")
    else:
        size = args.size
        log(f"ℹ️ Usando tamanho {size} conforme especificado")
    
    log(f"🖼️ Gerando criativos com dimensão {size} no estilo {args.style}")
    resultados = gerar_imagens(variacoes, spec, size, args.style)
    
    # Salvar detalhes da análise original para referência
    (OUT_DIR / "analise_original.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Salvar o plano de variações para referência
    (OUT_DIR / "plano_variacoes.json").write_text(
        json.dumps(var_pack, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Salvar manifesto com resultados
    (OUT_DIR / "resultados.json").write_text(
        json.dumps({"resultados": resultados}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    log(f"🎉 Concluído! {len(resultados)} criativos para marketing digital gerados em {OUT_DIR}/")
    
    # Agrupar por plataforma para relatório
    por_plataforma = {}
    for r in resultados:
        plat = r.get("plataforma", "Genérico")
        if plat not in por_plataforma:
            por_plataforma[plat] = []
        por_plataforma[plat].append(r)
    
    # Exibir resultados por plataforma
    for plat, items in por_plataforma.items():
        log(f"  ► {plat}: {len(items)} criativos")
        for item in items:
            log(f"    - {item['id']}: {item['arquivo']}")

if __name__ == "__main__":
    main() 