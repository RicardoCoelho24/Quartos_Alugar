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

def procurar_quartos_olx(cidade, preco_maximo):
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
                mensagem = f"🚨 *NOVO QUARTO DETETADO* 🚨\n🏠 {titulo}\n💰 {preco}\n🔗 [Clica aqui para abrir o anúncio]({link})"
                quartos_encontrados.append(mensagem)
                
                guardar_id(conexao, cursor, id_anuncio)

    except Exception as e:
        print(f"Erro a pesquisar no OLX: {e}")
    finally:
        cursor.close()
        conexao.close()

    return quartos_encontrados