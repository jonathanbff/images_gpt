#!/usr/bin/env python3
"""
home.py
Página Inicial - Videomate Agentes Criativos
Sistema de automação de marketing digital com vibe marketing

Permite escolher entre:
- Agente Criativo V1: Composição por imagem de referência
- Agente Criativo V2: Composição por prompt

Executar:
  streamlit run home.py
"""

import streamlit as st
import base64
from pathlib import Path
import subprocess
import sys

# Configurações da página
st.set_page_config(
    page_title="Videomate - Agentes Criativos",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para uma interface moderna e atrativa
st.markdown("""
<style>
    /* Remover espaçamento superior */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Estilo do header principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        color: white;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        font-size: 1.3rem;
        color: #f0f0f0;
        margin-bottom: 1rem;
        font-weight: 300;
    }
    
    .main-description {
        font-size: 1.1rem;
        color: #e0e0e0;
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Cards dos agentes */
    .agent-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border: 1px solid #e0e6ed;
        transition: all 0.3s ease;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .agent-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }
    
    .agent-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .agent-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .agent-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .agent-subtitle {
        font-size: 1rem;
        color: #7f8c8d;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    
    .agent-description {
        color: #5a6c7d;
        line-height: 1.6;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
    }
    
    .agent-features {
        margin-bottom: 2rem;
    }
    
    .feature-item {
        display: flex;
        align-items: center;
        margin-bottom: 0.8rem;
        color: #34495e;
    }
    
    .feature-icon {
        color: #27ae60;
        margin-right: 0.8rem;
        font-weight: bold;
    }
    
    .cta-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        text-align: center;
    }
    
    .cta-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        color: white !important;
    }
    
    /* Seção de benefícios */
    .benefits-section {
        background: #f8f9fa;
        padding: 3rem 2rem;
        border-radius: 15px;
        margin: 3rem 0;
    }
    
    .benefits-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 2rem;
    }
    
    .benefit-item {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .benefit-icon {
        font-size: 2rem;
        margin-right: 1rem;
        width: 60px;
        text-align: center;
    }
    
    .benefit-text {
        flex: 1;
    }
    
    .benefit-title {
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.3rem;
    }
    
    .benefit-description {
        color: #7f8c8d;
        font-size: 0.9rem;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 4rem;
        padding: 2rem;
        color: #7f8c8d;
        border-top: 1px solid #e0e6ed;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.5rem;
        }
        
        .main-subtitle {
            font-size: 1.1rem;
        }
        
        .agent-card {
            margin-bottom: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

def load_image_as_base64(image_path):
    """Carrega uma imagem e converte para base64"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <div class="main-title">🎬 Videomate</div>
        <div class="main-subtitle">Agentes Criativos de Marketing Digital</div>
        <div class="main-description">
            Automatize sua criação de conteúdo com nossa plataforma de vibe marketing. 
            Escolha entre nossos agentes especializados para gerar criativos únicos e impactantes.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Seção de escolha dos agentes
    st.markdown("## Escolha seu Agente Criativo")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
        <div class="agent-card">
            <div class="agent-icon">🖼️</div>
            <div class="agent-title">Agente Criativo V1</div>
            <div class="agent-subtitle">Composição por Imagem de Referência</div>
            <div class="agent-description">
                Transforme suas imagens de referência em criativos profissionais. 
                Nosso agente analisa composição, cores e elementos visuais para 
                criar variações otimizadas para diferentes plataformas.
            </div>
            <div class="agent-features">
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Análise automática de composição
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Geração de múltiplas variações
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Otimização para plataformas
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Copy inteligente personalizado
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Editor integrado de designs
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Iniciar com V1 - Imagem", key="v1", use_container_width=True):
            st.switch_page("agentes_criativos.py")
    
    with col2:
        st.markdown("""
        <div class="agent-card">
            <div class="agent-icon">✨</div>
            <div class="agent-title">Agente Criativo V2</div>
            <div class="agent-subtitle">Composição por Prompt</div>
            <div class="agent-description">
                Crie criativos incríveis apenas descrevendo sua ideia. 
                Nosso agente avançado gera conceitos visuais completos, 
                textos e designs finalizados em múltiplos idiomas e formatos.
            </div>
            <div class="agent-features">
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Criação baseada em texto
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Múltiplos idiomas (PT/EN/ES)
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    5 esquemas de cores
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Formatos 1:1 e 9:16
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    Footer com logo automático
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Iniciar com V2 - Prompt", key="v2", use_container_width=True):
            st.switch_page("agentes_criativo_v2.py")
    
    # Seção de benefícios
    st.markdown("""
    <div class="benefits-section">
        <div class="benefits-title">Por que escolher a Videomate?</div>
        <div class="benefit-item">
            <div class="benefit-icon">🚀</div>
            <div class="benefit-text">
                <div class="benefit-title">Automação Inteligente</div>
                <div class="benefit-description">Reduza o tempo de criação de horas para minutos com nossa IA especializada</div>
            </div>
        </div>
        <div class="benefit-item">
            <div class="benefit-icon">🎯</div>
            <div class="benefit-text">
                <div class="benefit-title">Vibe Marketing</div>
                <div class="benefit-description">Capture a essência da sua marca e transmita a vibe certa para seu público</div>
            </div>
        </div>
        <div class="benefit-item">
            <div class="benefit-icon">📈</div>
            <div class="benefit-text">
                <div class="benefit-title">Resultados Comprovados</div>
                <div class="benefit-description">Criativos otimizados para conversão em múltiplas plataformas digitais</div>
            </div>
        </div>
        <div class="benefit-item">
            <div class="benefit-icon">🌍</div>
            <div class="benefit-text">
                <div class="benefit-title">Alcance Global</div>
                <div class="benefit-description">Criação automática em português, inglês e espanhol</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Comparação rápida
    st.markdown("## Comparação Rápida")
    
    comparison_data = {
        "Recurso": [
            "Entrada",
            "Idiomas",
            "Formatos",
            "Variações de Cor",
            "Edição",
            "Melhor Para"
        ],
        "Agente V1 - Imagem": [
            "Imagem de referência",
            "Português",
            "Múltiplos tamanhos",
            "4 esquemas",
            "Editor completo",
            "Adaptação de materiais existentes"
        ],
        "Agente V2 - Prompt": [
            "Descrição em texto",
            "PT/EN/ES",
            "1:1 e 9:16",
            "5 esquemas",
            "Automático",
            "Criação do zero"
        ]
    }
    
    st.table(comparison_data)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p><strong>Videomate</strong> - Transformando ideias em realidade através do poder da IA</p>
        <p>Desenvolvido com ❤️ para automatizar seu processo criativo</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 