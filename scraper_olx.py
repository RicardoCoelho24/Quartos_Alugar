import requests
from bs4 import BeautifulSoup
import psycopg2
import os

def configurar_bd():
    # Vai buscar o link secreto ao .env (local) ou ao Render (nuvem)
    DATABASE_URL = os.getenv("DATABASE_URL")
    conexao = psycopg2.connect(DATABASE_URL)
    cursor = conexao.cursor()
    
    # Cria a tabela na nuvem se ela ainda não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anuncios (
            id TEXT PRIMARY KEY
        )
    ''')
    conexao.commit()
    return conexao, cursor

def verificar_se_novo(cursor, id_anuncio):
    cursor.execute('SELECT id FROM anuncios WHERE id = %s', (id_anuncio,))
    return cursor.fetchone() is None

def guardar_id(conexao, cursor, id_anuncio):
    # Guarda o ID e ignora se por acaso já lá estiver (evita erros)
    cursor.execute('INSERT INTO anuncios (id) VALUES (%s) ON CONFLICT DO NOTHING', (id_anuncio,))
    conexao.commit()

# --- NOVA FUNÇÃO ---
def obter_descricao_anuncio(url, headers):
    """Abre a página do anúncio individual e extrai o texto da descrição."""
    try:
        resposta = requests.get(url, headers=headers)
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        descricao = sopa.find('div', {'data-cy': 'ad_description'})
        
        if descricao:
            return descricao.text
        return ""
    except Exception:
        return ""

# --- ATUALIZADO: Recebe o genero_escolhido ---
def procurar_quartos_olx(cidade, preco_maximo, genero_escolhido):
    conexao, cursor = configurar_bd()
    url = f"https://www.olx.pt/imoveis/quartos-para-aluguer/{cidade}/?search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D={preco_maximo}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    quartos_encontrados = [] 

    try:
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()
        
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        anuncios = sopa.find_all('div', {'data-cy': 'l-card'})
        
        if not anuncios:
            return quartos_encontrados

        for anuncio in anuncios:
            titulo_tag = anuncio.find(['h4', 'h5', 'h6'])
            titulo = titulo_tag.text.strip() if titulo_tag else "Sem título"
            
            preco_tag = anuncio.find('p', {'data-testid': 'ad-price'})
            preco = preco_tag.text.strip() if preco_tag else "Preço sob consulta"
            
            link_tag = anuncio.find('a')
            link = link_tag['href'] if link_tag else "Sem link"
            if link.startswith('/'):
                link = "https://www.olx.pt" + link

            id_anuncio = link
            
            if verificar_se_novo(cursor, id_anuncio):
                
                # 1. Extração da Descrição apenas para anúncios não registados
                descricao = obter_descricao_anuncio(link, headers)
                # Junta o título e a descrição e mete tudo em minúsculas
                texto_completo = (titulo + " " + descricao).lower()
                
                # 2. Definição das Listas de Palavras-Chave
                palavras_femininas = ["rapariga", "menina", "feminina", "feminino", "senhora", "so para meninas", "apenas meninas"]
                palavras_masculinas = ["rapaz", "menino", "masculino", "masculina", "senhor", "so para meninos", "apenas rapazes"]
                
                # 3. Categorização (Os 3 Baldes)
                apenas_raparigas = any(p in texto_completo for p in palavras_femininas)
                apenas_rapazes = any(p in texto_completo for p in palavras_masculinas)
                
                categoria_quarto = "misto" # Balde Neutro por omissão
                
                if apenas_raparigas and not apenas_rapazes:
                    categoria_quarto = "rapariga"
                elif apenas_rapazes and not apenas_raparigas:
                    categoria_quarto = "rapaz"
                    
                # 4. Cruzamento de Dados (Filtro do Utilizador vs Categoria do Quarto)
                serve_para_utilizador = False
                
                if genero_escolhido == "rapariga" and categoria_quarto in ["rapariga", "misto"]:
                    serve_para_utilizador = True
                elif genero_escolhido == "rapaz" and categoria_quarto in ["rapaz", "misto"]:
                    serve_para_utilizador = True
                elif genero_escolhido == "qualquer" and categoria_quarto == "misto":
                    serve_para_utilizador = True
                    
                # 5. Adiciona à lista de envios caso o filtro passe
                if serve_para_utilizador:
                    mensagem = f"🚨 *NOVO QUARTO DETETADO* 🚨\n🏷️ *Filtro:* {categoria_quarto.capitalize()}\n🏠 {titulo}\n💰 {preco}\n🔗 [Clica aqui para abrir o anúncio]({link})"
                    quartos_encontrados.append(mensagem)
                
                # 6. Guarda sempre o ID (Mesmo que não sirva para este utilizador, para não reprocessar no futuro)
                guardar_id(conexao, cursor, id_anuncio)

    except Exception as e:
        print(f"Erro a pesquisar no OLX: {e}")
    finally:
        cursor.close()
        conexao.close()

    return quartos_encontrados