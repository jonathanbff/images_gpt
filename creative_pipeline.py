#!/usr/bin/env python3
"""
creative_pipeline.py – v3.1
Gera ou edita criativos usando gpt‑image‑1, com system prompts externos.

Requisitos:
  pip install openai python-dotenv pillow

Uso rápido:
  python creative_pipeline.py -i banner.png -n 3
"""
from __future__ import annotations
import argparse, base64, json, os, sys, re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from io import BytesIO

from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv

# ───────────────────────────── CONFIG ─────────────────────────────
load_dotenv()

MODEL_VISION = "gpt-4o-mini"
MODEL_TEXT   = "gpt-4o-mini"
MODEL_IMAGE  = "gpt-image-1"

DEFAULT_SIZE    = "1024x1024"
DEFAULT_QUALITY = "auto"
DEFAULT_BG      = "opaque"
DEFAULT_STYLE   = "photorealistic" # opções: photorealistic, flat, 3d, cartoon
OUT_DIR         = Path("outputs")
PROMPTS_DIR     = Path(__file__).resolve().parent / "prompts"

client = OpenAI()

# ─────────────────────────── UTILITÁRIOS ──────────────────────────
def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}")

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        sys.exit(f"❌ Prompt não encontrado: {path}")
    return path.read_text(encoding="utf-8")

def image_to_base64(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{data}"

def ensure_size(img_bytes: bytes, w: int, h: int) -> bytes:
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()

def parse_size(size: str) -> tuple[int, int]:
    m = re.match(r"(\d+)x(\d+)", size)
    if not m:
        raise ValueError("--size deve estar no formato LxA, ex: 1536x1024")
    return int(m.group(1)), int(m.group(2))

# ─────────────────────────── AGENTE 1 ─────────────────────────────
AGENT1_PROMPT = load_prompt("agent1_parser.txt")

def run_agent1(img_path: Path) -> Dict[str, Any]:
    log("Agente 1 ▶️  analisando layout")
    b64 = image_to_base64(img_path)
    res = client.chat.completions.create(
        model=MODEL_VISION,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": b64}},
                {"type": "text", "text": AGENT1_PROMPT}
            ]
        }],
        temperature=0
    )
    content = res.choices[0].message.content
    
    # Tenta extrair o JSON mesmo que o modelo responda com texto adicional
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        json_content = content[json_start:json_end]
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            # Se falhar, tenta limpar o texto e converter novamente
            clean_content = clean_json_string(json_content)
            return json.loads(clean_content)
    
    # Se não encontrar JSON válido, usa o conteúdo original como string
    log("⚠️ Não foi possível extrair JSON válido da resposta")
    return {"raw_response": content}

# ─────────────────────────── AGENTE 2 ─────────────────────────────
AGENT2_PROMPT       = load_prompt("agent2_strategist.txt")
AGENT2_RETRY_PROMPT = load_prompt("agent2_retry.txt")

def clean_json_string(s: str) -> str:
    start, end = s.find('{'), s.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("JSON não detectado")
    s = s[start:end+1]
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    s = s.replace("'", '"')
    s = re.sub(r':\s*null([,}])', r': null\\1', s)
    return s

def run_agent2(spec: Dict[str, Any]) -> Dict[str, Any]:
    log("Agente 2 ▶️  gerando variações textuais")
    
    # Verifica se estamos trabalhando com a saída crua do Agente 1
    if "raw_response" in spec:
        log("⚠️  Utilizando resposta textual do Agente 1 em vez de JSON")
        spec_content = spec["raw_response"]
    else:
        # Converte o novo formato para um formato compatível se necessário
        if "canvas_size" in spec and "placeholders" in spec:
            log("ℹ️  Convertendo formato novo para compatibilidade")
            # Mapeamento básico do novo formato para o formato esperado pelo Agente 2
            canvas = {
                "width": spec["canvas_size"]["w"],
                "height": spec["canvas_size"]["h"],
                "backgroundColor": spec["color_palette"][0] if spec["color_palette"] else "#FFFFFF"
            }
            
            elements = []
            for p in spec["placeholders"]:
                # Converte o placeholder para o formato esperado pelo Agente 2
                element = {
                    "id": p["id"],
                    "type": map_type(p["type"]),
                    "text": p["value"] if p["type"] == "text" else None,
                    "bbox": {
                        "x": p["bbox"][0] if isinstance(p["bbox"], list) else 0,
                        "y": p["bbox"][1] if isinstance(p["bbox"], list) else 0,
                        "w": p["bbox"][2] if isinstance(p["bbox"], list) else 0,
                        "h": p["bbox"][3] if isinstance(p["bbox"], list) else 0
                    },
                    "style": {
                        "fillColor": p["value"] if p["type"] == "shape" else "none",
                        "fontColor": (p.get("font", {}).get("color") if p["type"] == "text" 
                                     else "none"),
                        "fontSize": p.get("font", {}).get("size") if p["type"] == "text" else None,
                        "fontWeight": p.get("font", {}).get("weight") if p["type"] == "text" 
                                      else None,
                        "radius": None,
                        "alignment": None
                    },
                    "layer": 0,
                    "relation": None
                }
                elements.append(element)
            
            spec_content = json.dumps({"canvas": canvas, "elements": elements})
        else:
            spec_content = json.dumps(spec)
    
    prompt, temp = AGENT2_PROMPT, 0.7
    for _ in range(3):
        res = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": spec_content}],
            temperature=temp
        )
        content = res.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                return json.loads(clean_json_string(content))
            except Exception:
                log("⚠️  JSON inválido, trocando para prompt de retry")
                prompt, temp = AGENT2_RETRY_PROMPT, 0.2
    raise RuntimeError("Agente 2: não foi possível gerar JSON válido")

def map_type(type_str: str) -> str:
    """Mapeia os tipos do novo formato para o formato antigo"""
    mapping = {
        "text": "headline-text",  # valor padrão para textos
        "shape": "background-shape",
        "image": "illustration",
        "icon": "icon",
        "logo": "logo",
        "legal": "disclaimer-text"
    }
    return mapping.get(type_str, "background-shape")

# ─────────────────────────── AGENTE 3 ─────────────────────────────
PROMPT_TEMPLATE = load_prompt("agent3_template.txt")

def build_prompt(idea: str, palette: Dict[str, str],
                 ratio: str, transparent: bool, style: str = DEFAULT_STYLE) -> str:
    prompt = PROMPT_TEMPLATE
    prompt = prompt.replace("{{idea}}", idea)
    prompt = prompt.replace("{{ratio}}", ratio)
    prompt = prompt.replace("{{primary}}", palette["primary"])
    prompt = prompt.replace("{{secondary}}", palette["secondary"])
    prompt = prompt.replace("{{accent}}", palette["accent"])
    
    if style != "photorealistic":
        prompt = prompt.replace("photorealistic", style)
    
    if transparent:
        prompt = prompt.replace("{% if transparent %}", "")
        prompt = prompt.replace("{% endif %}", "")
    else:
        start = prompt.find("{% if transparent %}")
        end = prompt.find("{% endif %}") + len("{% endif %}")
        if start != -1 and end != -1:
            prompt = prompt[:start] + prompt[end:]
    
    return prompt

def fetch_palette(pid: str, pack: Dict[str, Any]) -> Dict[str, str]:
    return next(p for p in pack["colorPalettes"] if p["paletteId"] == pid)

def generate_images(variants: List[Dict[str, Any]], pack: Dict[str, Any],
                    size: str, quality: str, bg: str, 
                    style: str = DEFAULT_STYLE,
                    seed: int | None = None) -> List[Dict[str, Any]]:
    w, h = parse_size(size)
    assets = []
    for v in variants:
        palette = fetch_palette(v["placeholders"]["colors"], pack)
        prompt = build_prompt(
            v["placeholders"]["centralGraphicIdea"], palette, size, 
            bg == "transparent", style
        )
        log(f" → GPT generate {v['id']}")
        res = client.images.generate(
            model=MODEL_IMAGE,
            prompt=prompt,
            size=size,
            quality=quality,
            background=bg,
            n=1,
            **({"seed": seed} if seed else {})
        )
        img_b64 = res.data[0].b64_json
        fixed = ensure_size(base64.b64decode(img_b64), w, h)
        out = OUT_DIR / f"{v['id']}.png"
        out.write_bytes(fixed)
        assets.append({"id": v["id"], "png": str(out), "prompt": prompt})
    return assets

def edit_image(edit_path: Path, mask_path: Path | None, prompt: str,
               size: str, quality: str, bg: str, 
               style: str = DEFAULT_STYLE,
               seed: int | None = None) -> List[Dict[str, Any]]:
    w, h = parse_size(size)
    log(" → GPT edit")
    
    # Aplica o estilo ao prompt
    if style != "photorealistic":
        if "photorealistic" in prompt:
            prompt = prompt.replace("photorealistic", style)
        else:
            prompt = f"{prompt}. Generate in {style} style."
    
    res = client.images.edit(
        model=MODEL_IMAGE,
        image=open(edit_path, "rb"),
        mask=open(mask_path, "rb") if mask_path else None,
        prompt=prompt,
        size=size,
        quality=quality,
        background=bg,
        n=1,
        **({"seed": seed} if seed else {})
    )
    img_b64 = res.data[0].b64_json
    fixed = ensure_size(base64.b64decode(img_b64), w, h)
    out = OUT_DIR / f"edit_{edit_path.stem}.png"
    out.write_bytes(fixed)
    return [{"id": "edit", "png": str(out), "prompt": prompt}]

# ───────────────────────────── CLI ────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(
        description="Pipeline criativo com prompts externos e gpt-image-1")
    p.add_argument("-i", "--image", help="Imagem de referência (modo geração)")
    p.add_argument("-n", "--variants", type=int, default=3,
                   help="Qtd. de variações (máx 15)")
    p.add_argument("--size", default=DEFAULT_SIZE,
                   help="1024x1024 | 1536x1024 | 1024x1536 | auto")
    p.add_argument("--quality", default=DEFAULT_QUALITY,
                   choices=["low", "medium", "high", "auto"])
    p.add_argument("--background", default=DEFAULT_BG,
                   choices=["opaque", "transparent"])
    p.add_argument("--style", default=DEFAULT_STYLE,
                   choices=["photorealistic", "flat", "3d", "cartoon"],
                   help="Estilo visual das imagens geradas")
    p.add_argument("--seed", type=int, help="Seed para reprodutibilidade")

    # edição / inpainting
    p.add_argument("--edit-image", help="Imagem a ser editada")
    p.add_argument("--mask", help="Máscara PNG (opcional)")
    p.add_argument("--prompt", help="Prompt p/ edição")

    args = p.parse_args()
    OUT_DIR.mkdir(exist_ok=True)

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("❌  Defina OPENAI_API_KEY no ambiente")

    # MODO EDIÇÃO
    if args.edit_image:
        if not args.prompt:
            sys.exit("--prompt obrigatório no modo edição")
        edit_path = Path(args.edit_image)
        mask_path = Path(args.mask) if args.mask else None
        if not edit_path.exists():
            sys.exit(f"Arquivo não encontrado: {edit_path}")
        if mask_path and not mask_path.exists():
            sys.exit(f"Máscara não encontrada: {mask_path}")

        assets = edit_image(
            edit_path, mask_path, args.prompt,
            args.size, args.quality, args.background, args.style, args.seed)

    # MODO GERAÇÃO
    else:
        if not args.image:
            sys.exit("-i/--image obrigatório no modo geração")
        ref_path = Path(args.image)
        if not ref_path.exists():
            sys.exit(f"Arquivo não encontrado: {ref_path}")

        spec   = run_agent1(ref_path)
        pack   = run_agent2(spec)
        assets = generate_images(
            pack["creativeVariants"][:args.variants],
            pack, args.size, args.quality, args.background, args.style, args.seed)

    # Manifesto
    (OUT_DIR / "assets_manifest.json").write_text(
        json.dumps({"assets": assets}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log(f"🎉  Concluído! Resultados em {OUT_DIR}/")

if __name__ == "__main__":
    main()
