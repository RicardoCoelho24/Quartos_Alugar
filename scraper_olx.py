import requests
from bs4 import BeautifulSoup
import psycopg2
import os
import re  # Nova biblioteca para extrair apenas os números do preço

def configurar_bd():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conexao = psycopg2.connect(DATABASE_URL)
    cursor = conexao.cursor()
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
    cursor.execute('INSERT INTO anuncios (id) VALUES (%s) ON CONFLICT DO NOTHING', (id_anuncio,))
    conexao.commit()

def obter_descricao_anuncio(url, headers):
    try:
        resposta = requests.get(url, headers=headers)
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        descricao = sopa.find('div', {'data-cy': 'ad_description'})
        if descricao:
            return descricao.text
        return ""
    except Exception:
        return ""

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
            # 🛡️ ESCUDO 1: Ignorar anúncios "Destaque" (Patrocinados)
            if "Destaque" in anuncio.text:
                continue

            titulo_tag = anuncio.find(['h4', 'h5', 'h6'])
            titulo = titulo_tag.text.strip() if titulo_tag else "Sem título"
            
            # 🛡️ ESCUDO 2: Filtro Semântico (Remover lixo que não é quarto)
            titulo_lower = titulo.lower()
            palavras_lixo = ["garagem", "vendo", "carro", "mota", "volvo", "bmw", "cama", "colchão", "armário", "arrecadação", "loja"]
            
            if any(palavra in titulo_lower for palavra in palavras_lixo) and "quarto" not in titulo_lower:
                continue

            preco_tag = anuncio.find('p', {'data-testid': 'ad-price'})
            preco = preco_tag.text.strip() if preco_tag else "0"
            
            # 🛡️ ESCUDO 3: Guilhotina de Preço Matemática
            # Limpa espaços e pontos (ex: "1.250 €" -> "1250", "8 000 €" -> "8000")
            numeros_preco = re.findall(r'\d+', preco.replace(' ', '').replace('.', ''))
            if numeros_preco:
                valor_inteiro = int(numeros_preco[0])
                if valor_inteiro > int(preco_maximo):
                    continue # Custa mais do que o limite, ignorar!

            link_tag = anuncio.find('a')
            link = link_tag['href'] if link_tag else "Sem link"
            if link.startswith('/'):
                link = "https://www.olx.pt" + link

            id_anuncio = link
            
            if verificar_se_novo(cursor, id_anuncio):
                descricao = obter_descricao_anuncio(link, headers)
                texto_completo = (titulo + " " + descricao).lower()
                
                palavras_femininas = ["rapariga", "menina", "feminina", "feminino", "senhora", "so para meninas", "apenas meninas"]
                palavras_masculinas = ["rapaz", "menino", "masculino", "masculina", "senhor", "so para meninos", "apenas rapazes"]
                
                apenas_raparigas = any(p in texto_completo for p in palavras_femininas)
                apenas_rapazes = any(p in texto_completo for p in palavras_masculinas)
                
                categoria_quarto = "misto" 
                
                if apenas_raparigas and not apenas_rapazes:
                    categoria_quarto = "rapariga"
                elif apenas_rapazes and not apenas_raparigas:
                    categoria_quarto = "rapaz"
                    
                serve_para_utilizador = False
                
                if genero_escolhido == "rapariga" and categoria_quarto in ["rapariga", "misto"]:
                    serve_para_utilizador = True
                elif genero_escolhido == "rapaz" and categoria_quarto in ["rapaz", "misto"]:
                    serve_para_utilizador = True
                elif genero_escolhido == "qualquer" and categoria_quarto == "misto":
                    serve_para_utilizador = True
                    
                if serve_para_utilizador:
                    mensagem = f"🚨 *NOVO QUARTO DETETADO* 🚨\n🏷️ *Filtro:* {categoria_quarto.capitalize()}\n🏠 {titulo}\n💰 {preco}\n🔗 [Clica aqui para abrir o anúncio]({link})"
                    quartos_encontrados.append(mensagem)
                
                guardar_id(conexao, cursor, id_anuncio)

    except Exception as e:
        print(f"Erro a pesquisar no OLX: {e}")
    finally:
        cursor.close()
        conexao.close()

    return quartos_encontrados