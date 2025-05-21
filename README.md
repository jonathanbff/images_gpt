# Gerador Criativo de Marketing Digital

Aplicativo Streamlit que gera criativos otimizados para marketing digital, criando variações de imagens existentes com diferentes cores e textos.

## Funcionalidades

- **Análise de Imagem**: Reconhecimento detalhado de elementos visuais, cores e textos
- **Geração de Variações**: Criação de variações criativas com novas paletas de cores e textos alternativos
- **Renderização de Imagens**: Produção de criativos finais otimizados para diversas plataformas
- **Interface Amigável**: Apresentação dos resultados em interface web intuitiva

## Requisitos

- Python 3.8 ou superior
- API Key da OpenAI (para os modelos GPT-4o e DALL-E)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/gerador-criativo-marketing.git
cd gerador-criativo-marketing
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure a chave da API (opcional - pode ser inserida diretamente na interface):
```bash
echo "OPENAI_API_KEY=sua-chave-aqui" > .env
```

## Como Usar

### Método Fácil (Windows)

Simplesmente dê um duplo clique no arquivo `run_app.bat` para:
- Ativar automaticamente o ambiente virtual
- Instalar dependências se necessário
- Iniciar o aplicativo Streamlit

### Método Manual

1. Ative o ambiente virtual:
   ```bash
   # No Windows
   .\.venv\Scripts\activate
   
   # No Linux/Mac
   source .venv/bin/activate
   ```

2. Execute o aplicativo:
   ```bash
   # Usando o módulo Python (recomendado)
   python -m streamlit run app.py
   
   # Ou usando o comando streamlit diretamente 
   streamlit run app.py
   ```

3. Acesse a interface web no navegador (normalmente http://localhost:8501)

### Uso da Interface

1. Na barra lateral:
   - Insira sua API Key da OpenAI (se não configurada no arquivo .env)
   - Faça upload de uma imagem de referência
   - Ajuste as configurações de geração
   - Clique em "Gerar Criativos"

2. Navegue pelas abas para visualizar:
   - Análise da imagem original
   - Variações propostas
   - Imagens finais geradas
   - Logs de processamento

3. Faça o download dos criativos gerados para uso em suas campanhas

## Solução de Problemas

Se encontrar o erro `streamlit: command not found`:
1. Use o método de inicialização alternativo: `python -m streamlit run app.py`
2. Ou execute através do arquivo batch: `run_app.bat`

Se encontrar erros relacionados à interface gráfica:
1. Verifique os logs na aba "Logs" para identificar o problema
2. Certifique-se de que o ambiente virtual está ativado antes de executar o app

## Formatos Suportados

- **Tamanhos**: 1024x1024, 1024x1536, 1536x1024
- **Plataformas**: Facebook, Instagram, Google Ads, Stories
- **Estilos**: Fotorrealista, Flat Design, 3D, Cartoon

## Exemplos de Uso

1. **Banner de Produto**: Gere variações de um banner promocional com diferentes cores e textos
2. **Anúncios Sazonais**: Crie adaptações sazonais de um anúncio existente
3. **Testes A/B**: Gere múltiplas variações para testes de eficácia em marketing

## Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

---

Desenvolvido com ❤️ usando OpenAI e Streamlit 