import sqlite3
import pandas as pd
import gradio as gr
import os

# Caminho do banco de dados (funciona bem localmente ou no Render)
DB_PATH = 'brecho.db'

# 1. Inicializa o banco de dados e a tabela caso não exijam
def inicializar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT NOT NULL,
            preco REAL NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

inicializar_banco()

# Função auxiliar para reorganizar os IDs em sequência (1, 2, 3...) preenchendo lacunas
def reorganizar_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Pega todos os dados atuais ordenados por ID antigo
    cursor.execute('SELECT produto, preco, quantidade FROM estoque ORDER BY id ASC')
    itens = cursor.fetchall()
    
    # 2. Apaga a tabela e limpa a sequência do autoincrement
    cursor.execute('DROP TABLE estoque')
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="estoque"')
    
    # 3. Recria a tabela limpa
    cursor.execute('''
        CREATE TABLE estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT NOT NULL,
            preco REAL NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    
    # 4. Insere os itens novamente, fazendo com que ganhem IDs sequenciais limpos (1, 2, 3...)
    for item in itens:
        cursor.execute('''
            INSERT INTO estoque (produto, preco, quantidade)
            VALUES (?, ?, ?)
        ''', (item[0], item[1], item[2]))
        
    conn.commit()
    conn.close()

# 2. Função para carregar os dados
def carregar_dados(termo_busca=""):
    conn = sqlite3.connect(DB_PATH)
    if termo_busca:
        query = "SELECT * FROM estoque WHERE produto LIKE ?"
        df = pd.read_sql_query(query, conn, params=(f"%{termo_busca}%",))
    else:
        df = pd.read_sql_query('SELECT * FROM estoque', conn)
    conn.close()
    return df

# 3. Função para adicionar item
def adicionar_item(produto, preco, quantidade):
    if not produto.strip():
        return carregar_dados(), "Por favor, insira o nome do produto."
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO estoque (produto, preco, quantidade)
            VALUES (?, ?, ?)
        ''', (produto, float(preco), int(quantidade)))
        conn.commit()
        conn.close()
        return carregar_dados(), "Item adicionado com sucesso!"
    except Exception as e:
        return carregar_dados(), f"Erro ao adicionar: {e}"

# 4. Função para remover múltiplos itens e reorganizar a sequência de IDs
def remover_multiplos(ids_texto):
    if not ids_texto.strip():
        return carregar_dados(), "Digite os IDs separados por vírgula (ex: 1, 2, 3)."
    try:
        ids_para_remover = [int(i.strip()) for i in ids_texto.split(",") if i.strip().isdigit()]
        
        if not ids_para_remover:
            return carregar_dados(), "Nenhum ID válido foi informado."

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany('DELETE FROM estoque WHERE id = ?', [(i,) for i in ids_para_remover])
        conn.commit()
        conn.close()
        
        # Reorganiza os IDs para que voltem a ficar em ordem sequencial (1, 2, 3...)
        reorganizar_ids()
        
        return carregar_dados(), f"Itens removidos e IDs reorganizados com sucesso!"
    except Exception as e:
        return carregar_dados(), f"Erro ao remover: {e}"

# 5. Função para atualizar/editar a quantidade de um item pelo ID
def editar_quantidade(id_item, nova_qtd):
    try:
        id_num = int(id_item)
        qtd_num = int(nova_qtd)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verifica se o ID existe
        cursor.execute('SELECT * FROM estoque WHERE id = ?', (id_num,))
        if not cursor.fetchone():
            conn.close()
            return carregar_dados(), f"ID {id_num} não encontrado no estoque."
            
        # Atualiza a quantidade
        cursor.execute('UPDATE estoque SET quantidade = ? WHERE id = ?', (qtd_num, id_num))
        conn.commit()
        conn.close()
        
        return carregar_dados(), f"Quantidade do ID {id_num} atualizada para {qtd_num}!"
    except Exception as e:
        return carregar_dados(), f"Erro ao atualizar quantidade: {e}"

# 6. Função de filtro para a barra de pesquisa
def filtrar_estoque(termo):
    return carregar_dados(termo)

# 7. Construção da Interface Visual com Gradio
with gr.Blocks() as demo:
    gr.Markdown("## 👗 Gestão de Estoque - Brechó")
    
    with gr.Row():
        # Coluna da Esquerda: Ações (Adicionar, Editar e Remover)
        with gr.Column(scale=1):
            gr.Markdown("### ➕ Adicionar Item")
            txt_produto = gr.Textbox(label="Nome do Produto / Calçado")
            num_preco = gr.Number(label="Preço (R$)")
            num_qtd = gr.Number(label="Quantidade", value=1)
            btn_salvar = gr.Button("Adicionar ao Estoque", variant="primary")
            
            gr.Markdown("---")
            gr.Markdown("### ✏️ Atualizar Quantidade")
            num_id_editar = gr.Number(label="ID do Item", precision=0)
            num_nova_qtd = gr.Number(label="Nova Quantidade", precision=0, value=1)
            btn_editar = gr.Button("Atualizar Quantidade")

            gr.Markdown("---")
            gr.Markdown("### 🗑️ Excluir Vários Itens")
            txt_ids_remover = gr.Textbox(label="IDs para remover", placeholder="Ex: 1, 3, 5")
            btn_remover_multi = gr.Button("Remover Selecionados", variant="stop")
            
            lbl_status = gr.Textbox(label="Status do Sistema", interactive=False)
            
        # Coluna da Direita: Pesquisa e Tabela
        with gr.Column(scale=2):
            gr.Markdown("### 🔍 Pesquisa e Estoque Atual")
            txt_busca = gr.Textbox(label="Pesquisar por Nome do Produto", placeholder="Escreva para filtrar a tabela...")
            
            tabela_estoque = gr.DataFrame(
                value=carregar_dados(), 
                interactive=False
            )

    # Associações dos Botões e Eventos
    btn_salvar.click(
        fn=adicionar_item,
        inputs=[txt_produto, num_preco, num_qtd],
        outputs=[tabela_estoque, lbl_status]
    )
    
    btn_editar.click(
        fn=editar_quantidade,
        inputs=[num_id_editar, num_nova_qtd],
        outputs=[tabela_estoque, lbl_status]
    )

    btn_remover_multi.click(
        fn=remover_multiplos,
        inputs=[txt_ids_remover],
        outputs=[tabela_estoque, lbl_status]
    )
    
    txt_busca.change(
        fn=filtrar_estoque,
        inputs=[txt_busca],
        outputs=[tabela_estoque]
    )

# Execução compatível com Render e Colab
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    try:
        demo.launch(server_name="0.0.0.0", server_port=port)
    except:
        demo.launch()