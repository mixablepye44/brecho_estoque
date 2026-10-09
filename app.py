import sqlite3
import pandas as pd
import gradio as gr
import os

DB_PATH = 'brecho.db'

# 1. Inicializa o banco de dados e a tabela caso não existam
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

# Função para reorganizar os IDs em sequência (1, 2, 3...)
def reorganizar_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT produto, preco, quantidade FROM estoque ORDER BY id ASC')
    itens = cursor.fetchall()
    cursor.execute('DROP TABLE estoque')
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="estoque"')
    cursor.execute('''
        CREATE TABLE estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT NOT NULL,
            preco REAL NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
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

# 3. Adicionar item (Retorna campos vazios para limpar o formulário)
def adicionar_item(produto, preco, quantidade):
    if not produto.strip():
        return carregar_dados(), "⚠️ Por favor, insira o nome do produto.", "", 0, 1
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO estoque (produto, preco, quantidade)
            VALUES (?, ?, ?)
        ''', (produto, float(preco), int(quantidade)))
        conn.commit()
        conn.close()
        # Retorna: tabela atualizada, mensagem de sucesso, e limpa os campos (produto="", preco=0, qtd=1)
        return carregar_dados(), "✨ Item adicionado com sucesso!", "", 0, 1
    except Exception as e:
        return carregar_dados(), f"❌ Erro ao adicionar: {e}", produto, preco, quantidade

# 4. Remover múltiplos itens (Retorna o campo de IDs limpo)
def remover_multiplos(ids_texto):
    if not ids_texto.strip():
        return carregar_dados(), "⚠️ Digite os IDs separados por vírgula (ex: 1, 2, 3).", ""
    try:
        ids_para_remover = [int(i.strip()) for i in ids_texto.split(",") if i.strip().isdigit()]
        
        if not ids_para_remover:
            return carregar_dados(), "⚠️ Nenhum ID válido foi informado.", ""

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany('DELETE FROM estoque WHERE id = ?', [(i,) for i in ids_para_remover])
        conn.commit()
        conn.close()
        
        reorganizar_ids()
        
        # Retorna: tabela atualizada, mensagem de sucesso e limpa o campo de exclusão ("")
        return carregar_dados(), "🗑️ Itens removidos e IDs reorganizados com sucesso!", ""
    except Exception as e:
        return carregar_dados(), f"❌ Erro ao remover: {e}", ids_texto

# 5. Editar quantidade (Retorna os campos de edição limpos)
def editar_quantidade(id_item, nova_qtd):
    if not id_item:
        return carregar_dados(), "⚠️ Informe o ID do item a ser atualizado.", None, 1
    try:
        id_num = int(id_item)
        qtd_num = int(nova_qtd)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM estoque WHERE id = ?', (id_num,))
        if not cursor.fetchone():
            conn.close()
            return carregar_dados(), f"⚠️ ID {id_num} não encontrado no estoque.", id_item, nova_qtd
            
        cursor.execute('UPDATE estoque SET quantidade = ? WHERE id = ?', (qtd_num, id_num))
        conn.commit()
        conn.close()
        
        # Retorna: tabela atualizada, mensagem e limpa os campos de edição (ID=None, Qtd=1)
        return carregar_dados(), f"✅ Quantidade do ID {id_num} atualizada para {qtd_num}!", None, 1
    except Exception as e:
        return carregar_dados(), f"❌ Erro ao atualizar: {e}", id_item, nova_qtd

# 6. Filtro de pesquisa
def filtrar_estoque(termo):
    return carregar_dados(termo)

# 7. Construção da Interface Visual com Tema Estético (Soft)
with gr.Blocks(theme=gr.themes.Soft(primary_hue="rose", secondary_hue="pink")) as demo:
    gr.Markdown("# 👗 Gestão de Estoque — Brechó")
    gr.Markdown("Gerencie seus produtos, atualize quantidades e controle o estoque de forma simples e organizada.")
    
    with gr.Row():
        # Coluna Esquerda: Painel de Controle (Dividido em Abas ou Blocos limpos)
        with gr.Column(scale=1, min_width=320):
            
            with gr.Tabs():
                with gr.TabItem("➕ Adicionar"):
                    txt_produto = gr.Textbox(label="Nome do Produto / Calçado", placeholder="Ex: Vestido Floral Vintage")
                    num_preco = gr.Number(label="Preço (R$)", value=0.0)
                    num_qtd = gr.Number(label="Quantidade", value=1, precision=0)
                    btn_salvar = gr.Button("Adicionar ao Estoque", variant="primary")
                
                with gr.TabItem("✏️ Editar Qtd"):
                    num_id_editar = gr.Number(label="ID do Item", precision=0, placeholder="Ex: 1")
                    num_nova_qtd = gr.Number(label="Nova Quantidade", precision=0, value=1)
                    btn_editar = gr.Button("Atualizar Quantidade", variant="secondary")

                with gr.TabItem("🗑️ Excluir"):
                    txt_ids_remover = gr.Textbox(label="IDs para remover", placeholder="Ex: 1, 3, 5")
                    btn_remover_multi = gr.Button("Excluir Selecionados", variant="stop")
            
            gr.Markdown("---")
            lbl_status = gr.Textbox(label="Status do Sistema", interactive=False)
            
        # Coluna Direita: Visualização e Busca
        with gr.Column(scale=2):
            txt_busca = gr.Textbox(label="🔍 Pesquisar Produto", placeholder="Digite o nome para filtrar a tabela em tempo real...")
            
            tabela_estoque = gr.DataFrame(
                value=carregar_dados(), 
                interactive=False,
                wrap=True
            )

    # Ações e Eventos (com limpeza automática das caixas de entrada)
    btn_salvar.click(
        fn=adicionar_item,
        inputs=[txt_produto, num_preco, num_qtd],
        outputs=[tabela_estoque, lbl_status, txt_produto, num_preco, num_qtd]
    )
    
    btn_editar.click(
        fn=editar_quantidade,
        inputs=[num_id_editar, num_nova_qtd],
        outputs=[tabela_estoque, lbl_status, num_id_editar, num_nova_qtd]
    )

    btn_remover_multi.click(
        fn=remover_multiplos,
        inputs=[txt_ids_remover],
        outputs=[tabela_estoque, lbl_status, txt_ids_remover]
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