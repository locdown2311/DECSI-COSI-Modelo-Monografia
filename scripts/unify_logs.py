import os
import shutil

def unify_files(input_files, output_file):
    first_file = True
    last_char_was_newline = True
    
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        for filepath in input_files:
            if not os.path.exists(filepath):
                print(f"Aviso: Arquivo nao encontrado: {filepath}")
                continue
            print(f"Processando {os.path.basename(filepath)}...")
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
                if first_file:
                    for line in infile:
                        # Limpa caracteres nulos
                        line_cleaned = line.replace('\x00', '')
                        outfile.write(line_cleaned)
                        if line_cleaned:
                            last_char_was_newline = line_cleaned.endswith('\n')
                    first_file = False
                else:
                    infile_iter = iter(infile)
                    try:
                        next(infile_iter) # Descarta cabecalho
                    except StopIteration:
                        continue
                    
                    # Se o arquivo anterior nao terminou com nova linha, adiciona agora
                    if not last_char_was_newline:
                        outfile.write('\n')
                        last_char_was_newline = True
                        
                    for line in infile_iter:
                        # Limpa caracteres nulos
                        line_cleaned = line.replace('\x00', '')
                        outfile.write(line_cleaned)
                        if line_cleaned:
                            last_char_was_newline = line_cleaned.endswith('\n')
                            
    print(f"Sucesso! Arquivo unificado criado em: {output_file}\n")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Configurar caminhos para Ruckus
    ruckus_dir = os.path.join(base_dir, 'ruckus')
    ruckus_inputs = [
        os.path.join(ruckus_dir, 'log-ruckus-23-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-24-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-25-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-26-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-29-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-30-06.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-01-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-02-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-03-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-06-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-07-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-08-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-09-07.csv'),
        os.path.join(ruckus_dir, 'log-ruckus-10-07.csv'),
    ]
    ruckus_output = os.path.join(ruckus_dir, 'log-ruckus-23-06-to-10-07.csv')
    # 2. Configurar caminhos para UniFi
    unifi_dir = os.path.join(base_dir, 'unifi')
    unifi_inputs = [
        os.path.join(unifi_dir, 'log-unifi-23-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-24-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-25-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-26-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-29-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-30-06.csv'),
        os.path.join(unifi_dir, 'log-unifi-01-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-02-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-03-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-06-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-07-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-08-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-09-07.csv'),
        os.path.join(unifi_dir, 'log-unifi-10-07.csv'),
    ]
    unifi_output = os.path.join(unifi_dir, 'log-unifi-23-06-to-10-07.csv')
    
    # Executar unificacao Ruckus
    print("==================================================")
    print("UNIFICANDO LOGS DA RUCKUS (23-06 ate 10-07)...")
    print("==================================================")
    unify_files(ruckus_inputs, ruckus_output)
    
    # Executar unificacao UniFi
    print("==================================================")
    print("UNIFICANDO LOGS DA UNIFI (23-06 ate 10-07)...")
    print("==================================================")
    unify_files(unifi_inputs, unifi_output)
    
    print("\nConcluido! Os arquivos unificados estao salvos como '23-06-to-10-07.csv' e prontos para execucao do pipeline.")

if __name__ == '__main__':
    main()
