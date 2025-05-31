#!/usr/bin/env python3
"""
Script de teste para verificar se a API OpenAI está funcionando corretamente
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Carregar variáveis de ambiente
load_dotenv()

def test_openai_api():
    """Testa a API OpenAI"""
    print("🔍 Testando API OpenAI...")
    
    # Verificar API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ API Key não encontrada!")
        return False
    
    print(f"✓ API Key encontrada: {api_key[:20]}...")
    
    try:
        client = OpenAI()
        
        # Teste 1: Chat
        print("\n📝 Testando GPT-4o (chat)...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Diga olá em português"}],
            max_tokens=50
        )
        print(f"✓ Chat funcionando: {response.choices[0].message.content}")
        
        # Teste 2: Geração de imagem simples
        print("\n🎨 Testando GPT-image-1...")
        response = client.images.generate(
            model="gpt-image-1",
            prompt="A simple red circle on white background",
            size="1024x1024",
            quality="high",
            n=1
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            if image_url and image_url != "None" and image_url.startswith("http"):
                print(f"✓ Imagem gerada: {image_url[:50]}...")
                return True
            else:
                print(f"❌ URL inválida: {image_url}")
                return False
        else:
            print("❌ Resposta vazia da API de imagem")
            return False
            
    except Exception as e:
        print(f"❌ Erro na API: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_api()
    if success:
        print("\n🎉 API funcionando corretamente!")
    else:
        print("\n💥 Problemas na API detectados!") 