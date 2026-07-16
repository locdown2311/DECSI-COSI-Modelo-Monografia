import os
import re
import shutil

def escape_latex(text):
    # Não escapar se estiver em modo matemático (começa e termina com $)
    # Vamos separar o texto em partes matemáticas e normais
    parts = re.split(r'(\$.*?\$)', text)
    for i in range(len(parts)):
        if not parts[i].startswith('$'):
            # Escapar caracteres especiais do LaTeX fora do modo matemático
            p = parts[i]
            p = p.replace('\\', '\\textbackslash ')
            p = p.replace('&', '\\&')
            p = p.replace('%', '\\%')
            p = p.replace('_', '\\_')
            p = p.replace('#', '\\#')
            p = p.replace('{', '\\{')
            p = p.replace('}', '\\}')
            p = p.replace('~', '\\textasciitilde ')
            p = p.replace('^', '\\textasciicircum ')
            parts[i] = p
    return ''.join(parts)

def clean_label(text):
    text = text.lower()
    text = text.replace('á', 'a').replace('à', 'a').replace('â', 'a').replace('ã', 'a')
    text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
    text = text.replace('í', 'i').replace('ì', 'i')
    text = text.replace('ó', 'o').replace('ò', 'o').replace('ô', 'o').replace('õ', 'o')
    text = text.replace('ú', 'u').replace('ù', 'u')
    text = text.replace('ç', 'c')
    text = re.sub(r'[^a-z0-9_]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def clean_heading_title(title):
    # Remover (Etapa X) ou (Etapa_X) ou similares
    title = re.sub(r'\s*\(\s*Etapa\s*[0-9A-Za-z_]+\s*\)', '', title, flags=re.IGNORECASE)
    # Remover numeração no início (ex: "1. ", "1.1. ", "1.1.1. ")
    title = re.sub(r'^\d+(\.\d+)*\.?\s+', '', title)
    return title.strip()

def format_number_br(text):
    # 1. Substituir milhares formatados com vírgula americana: ex: 285,181 -> 285.181
    text = re.sub(r'\b(\d+),(\d{3})\b', r'\1.\2', text)
    
    # 2. Substituir decimais formatados com ponto: ex: -67.4 -> -67,4
    text = re.sub(r'(\d+)\.(\d+)', r'\1,\2', text)
    
    # 3. Restaurar nomes próprios como 802.11
    text = text.replace('802,11', '802.11')
    
    return text

def convert_md_line_to_tex(line):
    # 1. Substituir significâncias por marcadores temporários sem asteriscos
    line = line.replace('(***)', 'TEMP_SIG_THREE_P')
    line = line.replace('(**)', 'TEMP_SIG_TWO_P')
    line = line.replace('(*)', 'TEMP_SIG_ONE_P')
    line = line.replace('***', 'TEMP_SIG_THREE')
    line = line.replace('**', 'TEMP_SIG_TWO')
    line = line.replace('*', 'TEMP_SIG_ONE')
    line = line.replace('(n.s.)', '(n.s.)')
    
    # 2. Negrito: TEMP_SIG_TWO text TEMP_SIG_TWO -> \textbf{text}
    line = re.sub(r'TEMP_SIG_TWO(.*?)TEMP_SIG_TWO', r'\\textbf{\1}', line)
    
    # 3. Itálico: TEMP_SIG_ONE text TEMP_SIG_ONE -> \textit{text}
    line = re.sub(r'TEMP_SIG_ONE(.*?)TEMP_SIG_ONE', r'\\textit{\1}', line)
    
    # 4. Restaurar os marcadores de significância para a sintaxe LaTeX correta
    line = line.replace('TEMP_SIG_THREE_P', '(\\textsuperscript{***})')
    line = line.replace('TEMP_SIG_TWO_P', '(\\textsuperscript{**})')
    line = line.replace('TEMP_SIG_ONE_P', '(\\textsuperscript{*})')
    line = line.replace('TEMP_SIG_THREE', '\\textsuperscript{***}')
    line = line.replace('TEMP_SIG_TWO', '\\textsuperscript{**}')
    line = line.replace('TEMP_SIG_ONE', '\\textsuperscript{*}')
    
    # 5. Formatar números no padrão brasileiro e converter backticks para \texttt{}
    # Vamos separar o texto em partes dentro de backticks e fora
    parts = re.split(r'(`[^`]+`)', line)
    for i in range(len(parts)):
        if parts[i].startswith('`') and parts[i].endswith('`'):
            # É código inline: remover as crases e colocar \texttt{}
            code_content = parts[i][1:-1]
            parts[i] = f"\\texttt{{{code_content}}}"
        else:
            # É texto normal: formatar números
            parts[i] = format_number_br(parts[i])
            
    line = ''.join(parts)
    
    # 6. Converter expressões de p-valor para modo matemático
    # Ex: p < 0,05 -> $p < 0,05$
    # Ex: p = 0,1234 -> $p = 0,1234$
    line = re.sub(r'\bp\s*(<|=)\s*(\d+,\d+)\b', r'$p \1 \2$', line)
    
    return line

def parse_markdown_to_tex(md_content, section_title_default=""):
    lines = md_content.split('\n')
    tex_lines = []
    
    list_stack = []  # Pilha para rastrear os ambientes abertos (ex: ['enumerate', 'itemize'])
    in_table = False
    table_headers = []
    table_rows = []
    in_code = False
    table_counter = 0
    skip_section = False
    last_heading_title = ""  # Rastreia o último título de seção visto
    
    def close_all_lists():
        while list_stack:
            l_type = list_stack.pop()
            tex_lines.append(f"\\end{{{l_type}}}")
            
    def close_table():
        nonlocal in_table, table_headers, table_rows, table_counter
        if not in_table:
            return
        in_table = False
        num_cols = len(table_headers)
        align_str = "l" + "c" * (num_cols - 1)
        
        table_counter += 1
        if last_heading_title:
            cap = convert_md_line_to_tex(escape_latex(last_heading_title))
        else:
            cap = f"Dados comparativos da análise - {escape_latex(section_title_default)}"
        lbl = clean_label(f"data_{section_title_default}_{table_counter}")
        
        tex_lines.append("\\begin{table}[H]")
        tex_lines.append("\\IBGEtab{%")
        tex_lines.append(f"  \\caption{{{cap}}}%")
        tex_lines.append(f"  \\label{{tab:{lbl}}}%")
        tex_lines.append("}{%")
        tex_lines.append("  \\resizebox{\\textwidth}{!}{%")
        tex_lines.append(f"    \\begin{{tabular}}{{{align_str}}}")
        tex_lines.append("      \\toprule")
        
        # Header
        header_str = " & ".join([convert_md_line_to_tex(escape_latex(h)) for h in table_headers])
        tex_lines.append(f"      {header_str} \\\\")
        tex_lines.append("      \\midrule")
        
        # Rows
        for row in table_rows:
            row_str = " & ".join([convert_md_line_to_tex(escape_latex(c)) for c in row])
            tex_lines.append(f"      {row_str} \\\\")
            
        tex_lines.append("      \\bottomrule")
        tex_lines.append("    \\end{tabular}%")
        tex_lines.append("  }%")
        tex_lines.append("}{%")
        tex_lines.append("  \\fonte{Produzido pelos autores.}%")
        tex_lines.append("}")
        tex_lines.append("\\end{table}")
            
    for line_idx, line in enumerate(lines):
        striped = line.strip()
        
        # Ignorar se for uma seção de desenvolvedor listando arquivos de imagem gerados
        if striped.startswith('#'):
            clean_str = striped.lower()
            if 'gráfico' in clean_str and ('gerado' in clean_str or 'diagnóstico' in clean_str or 'diagnostico' in clean_str):
                skip_section = True
                continue
            else:
                skip_section = False
                
        if skip_section:
            continue
            
        # Ignorar linhas contendo apenas traços (horizontal rules do markdown '---')
        if re.match(r'^---+$', striped):
            continue
            
        # Ignorar alerts do GitHub
        if striped.startswith('> [!'):
            continue
        if striped.startswith('>') and (striped.startswith('> **') or len(striped) <= 2):
            striped = striped[1:].strip()
            line = line[1:].strip()
            
        # Ignorar linhas de rodapé com metadados de geração
        if 'gerado em:' in line.lower() or 'gerado em *etapa_' in line.lower() or 'relatório de' in line.lower() and 'gerado em' in line.lower():
            continue
            
        # Se a linha não começar com '|', fecha tabela se estiver ativa
        if not striped.startswith('|'):
            close_table()

        # Code blocks
        if striped.startswith('```'):
            if in_code:
                tex_lines.append("\\end{verbatim}")
                in_code = False
            else:
                tex_lines.append("\\begin{verbatim}")
                in_code = True
            continue
            
        if in_code:
            tex_lines.append(line)
            continue
            
        # Headers
        if striped.startswith('# '):
            close_all_lists()
            title = striped[2:].strip()
            if title.lower().startswith('relatório de '):
                title = title[13:] # Remover "Relatório de "
            title = clean_heading_title(title)
            title = convert_md_line_to_tex(escape_latex(title))
            tex_lines.append(f"\\section{{{title}}}")
            continue
        elif striped.startswith('## '):
            close_all_lists()
            title = striped[3:].strip()
            title = clean_heading_title(title)
            last_heading_title = title
            title = convert_md_line_to_tex(escape_latex(title))
            tex_lines.append(f"\\subsection{{{title}}}")
            continue
        elif striped.startswith('### '):
            close_all_lists()
            title = striped[4:].strip()
            title = clean_heading_title(title)
            last_heading_title = title
            title = convert_md_line_to_tex(escape_latex(title))
            tex_lines.append(f"\\subsubsection{{{title}}}")
            continue
        elif striped.startswith('#### '):
            close_all_lists()
            title = striped[5:].strip()
            title = clean_heading_title(title)
            title = convert_md_line_to_tex(escape_latex(title))
            tex_lines.append(f"\\paragraph{{{title}}}")
            continue
            
        # Images: ![Caption](path)
        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', striped)
        if img_match:
            close_all_lists()
            caption = img_match.group(1)
            img_path = img_match.group(2)
            # Extrair nome do arquivo de imagem
            img_filename = os.path.basename(img_path)
            # LaTeX figure include
            tex_lines.append("\\begin{figure}[H]")
            tex_lines.append("  \\centering")
            tex_lines.append(f"  \\includegraphics[width=0.85\\textwidth]{{img/{img_filename}}}")
            tex_lines.append(f"  \\caption{{{escape_latex(caption)}}}")
            label = img_filename.replace('.', '_').replace('-', '_')
            tex_lines.append(f"  \\label{{fig:{label}}}")
            tex_lines.append("\\end{figure}")
            continue
            
        # Detectar recuo para listas aninhadas
        leading_spaces = len(line) - len(line.lstrip())
        is_indented = leading_spaces >= 2

        # Bullet list
        if striped.startswith('* ') or striped.startswith('- '):
            current_type = 'itemize'
            item_text = striped[2:].strip()
            item_text = convert_md_line_to_tex(escape_latex(item_text))
            
            if not is_indented:
                # Nível 1: Fechar qualquer nível 2 e qualquer nível 1 de tipo diferente
                while len(list_stack) > 1 or (list_stack and list_stack[0] != current_type):
                    l_type = list_stack.pop()
                    tex_lines.append(f"\\end{{{l_type}}}")
                if not list_stack:
                    tex_lines.append(f"\\begin{{{current_type}}}")
                    list_stack.append(current_type)
                tex_lines.append(f"  \\item {item_text}")
            else:
                # Nível 2
                if not list_stack:
                    # Tratar como Nível 1 se não houver lista pai
                    tex_lines.append(f"\\begin{{{current_type}}}")
                    list_stack.append(current_type)
                    tex_lines.append(f"  \\item {item_text}")
                elif len(list_stack) == 1:
                    # Abrir lista nível 2
                    tex_lines.append(f"  \\begin{{{current_type}}}")
                    list_stack.append(current_type)
                    tex_lines.append(f"    \\item {item_text}")
                else:
                    # Se tipo do nível 2 for diferente, fecha e abre novo
                    if list_stack[-1] != current_type:
                        l_type = list_stack.pop()
                        tex_lines.append(f"  \\end{{{l_type}}}")
                        tex_lines.append(f"  \\begin{{{current_type}}}")
                        list_stack.append(current_type)
                    tex_lines.append(f"    \\item {item_text}")
            continue
            
        # Numbered list: e.g. 1. Item
        num_match = re.match(r'^\d+\.\s+(.*)', striped)
        if num_match:
            current_type = 'enumerate'
            item_text = num_match.group(1).strip()
            item_text = convert_md_line_to_tex(escape_latex(item_text))
            
            if not is_indented:
                # Nível 1: Fechar qualquer nível 2 e qualquer nível 1 de tipo diferente
                while len(list_stack) > 1 or (list_stack and list_stack[0] != current_type):
                    l_type = list_stack.pop()
                    tex_lines.append(f"\\end{{{l_type}}}")
                if not list_stack:
                    tex_lines.append(f"\\begin{{{current_type}}}")
                    list_stack.append(current_type)
                tex_lines.append(f"  \\item {item_text}")
            else:
                # Nível 2
                if not list_stack:
                    tex_lines.append(f"\\begin{{{current_type}}}")
                    list_stack.append(current_type)
                    tex_lines.append(f"  \\item {item_text}")
                elif len(list_stack) == 1:
                    tex_lines.append(f"  \\begin{{{current_type}}}")
                    list_stack.append(current_type)
                    tex_lines.append(f"    \\item {item_text}")
                else:
                    if list_stack[-1] != current_type:
                        l_type = list_stack.pop()
                        tex_lines.append(f"  \\end{{{l_type}}}")
                        tex_lines.append(f"  \\begin{{{current_type}}}")
                        list_stack.append(current_type)
                    tex_lines.append(f"    \\item {item_text}")
            continue
            
        # Ignorar linhas vazias no meio da lista sem fechar a lista
        if not striped:
            tex_lines.append("")
            continue
            
        # Table parsing
        if striped.startswith('|'):
            table_headers_row = [c.strip() for c in striped.split('|')[1:-1]]
            # Se for a linha separadora de cabeçalho |---|---|, apenas ignoramos
            if striped.replace(' ', '').replace('-', '').replace(':', '').replace('|', '') == '':
                continue
            
            if not in_table:
                in_table = True
                table_headers = table_headers_row
                table_rows = []
            else:
                table_rows.append(table_headers_row)
            continue
            
        # Linha normal de texto
        if striped:
            # Se for texto normal não recuado, fecha as listas
            if leading_spaces < 2:
                close_all_lists()
            processed_line = convert_md_line_to_tex(escape_latex(line))
            tex_lines.append(processed_line)
        else:
            tex_lines.append("")
            
    # Garantir fechamento se arquivo terminar com lista ou tabela aberta
    close_all_lists()
    close_table()
    return "\n".join(tex_lines)

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    monografia_dir = os.path.join(base_dir, 'monografia')
    img_dir = os.path.join(monografia_dir, 'img')
    textuais_dir = os.path.join(monografia_dir, 'textuais')
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(textuais_dir, exist_ok=True)
    
    stages = [
        ('Etapa_0_Validacao', 'relatorio_validacao.md', 'resultados_validacao.tex', 'Validação de Dados'),
        ('Etapa_1_Estatistica_Descritiva', 'relatorio_estatistica.md', 'resultados_estatistica.tex', 'Estatística Descritiva'),
        ('Etapa_2_Visualizacao', 'relatorio_visualizacao.md', 'resultados_visualizacao.tex', 'Análise Temporal'),
        ('Etapa_3_Correlacoes', 'relatorio_correlacoes.md', 'resultados_correlacoes.tex', 'Análise de Correlações'),
        ('Etapa_4_Testes_Estatisticos', 'relatorio_testes.md', 'resultados_testes.tex', 'Testes Hipótese'),
        ('Etapa_5_Classificacao_Gargalos', 'relatorio_gargalos.md', 'resultados_gargalos.tex', 'Classificação Gargalos')
    ]
    
    # 1. Processar relatórios, copiar imagens referenciadas e converter para LaTeX
    for stage_folder, md_file, tex_file, title in stages:
        stage_path = os.path.join(base_dir, stage_folder)
        md_path = os.path.join(stage_path, md_file)
        
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Encontrar e copiar todas as imagens referenciadas no markdown
            img_links = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for img_link in img_links:
                # Pode conter caminhos relativos como 'graficos_dispersao/filename.png'
                src_file = os.path.join(stage_path, img_link)
                if os.path.exists(src_file):
                    dest_file = os.path.join(img_dir, os.path.basename(img_link))
                    shutil.copy2(src_file, dest_file)
                    print(f"Copiada imagem referenciada: {os.path.basename(img_link)} para monografia/img/")
                else:
                    # Tentar procurar no diretório 'graficos' ou 'graficos_dispersao' como fallback
                    fallback_filename = os.path.basename(img_link)
                    found = False
                    for sub in ['graficos', 'graficos_dispersao']:
                        sub_path = os.path.join(stage_path, sub, fallback_filename)
                        if os.path.exists(sub_path):
                            shutil.copy2(sub_path, os.path.join(img_dir, fallback_filename))
                            print(f"Copiada imagem (fallback): {fallback_filename} para monografia/img/")
                            found = True
                            break
                    if not found:
                        print(f"Aviso: Imagem não encontrada: {img_link} em {stage_folder}")
            
            # Converter relatórios para LaTeX
            tex_content = parse_markdown_to_tex(content, title)
            
            tex_dest_path = os.path.join(textuais_dir, tex_file)
            with open(tex_dest_path, 'w', encoding='utf-8') as f:
                f.write(tex_content)
            print(f"Convertido {md_file} -> textuais/{tex_file}")
            
    # 3. Criar arquivo geral de inclusão em monografia/textuais/resultados.tex
    include_content = """% ----------------------------------------------------------
% Resultados e Discussões (Gerado Automaticamente do Pipeline)
% ----------------------------------------------------------
\chapter{Resultados e Discussão}
\label{cap:resultados}

Este capítulo apresenta os resultados práticos obtidos a partir do pipeline de análise de telemetria de rede Wi-Fi, divididos em etapas que cobrem a validação de dados, análise descritiva, representações temporais, correlação linear, testes formais de hipótese e classificação operativa dos Access Points.

\\input{./textuais/resultados_validacao}
\\input{./textuais/resultados_estatistica}
\\input{./textuais/resultados_visualizacao}
\\input{./textuais/resultados_correlacoes}
\\input{./textuais/resultados_testes}
\\input{./textuais/resultados_gargalos}
"""
    
    with open(os.path.join(textuais_dir, 'resultados.tex'), 'w', encoding='utf-8') as f:
        f.write(include_content)
    print("Regerado arquivo de entrada principal: textuais/resultados.tex")

if __name__ == '__main__':
    main()
