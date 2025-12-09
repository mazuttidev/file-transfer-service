import socket
import os
import math
import random
import struct

def send_file(filename, host, port, buffer_size=1024, loss_rate=0.0, error_rate=0.0):
    print(f"Arquivo: {filename}")
    if not os.path.exists(filename):
        print(f"Erro: O arquivo {filename} não foi encontrado.")
        return

    # Calcula o número de pacotes a serem enviados
    file_size = os.path.getsize(filename)
    num_pacotes = math.ceil(file_size / buffer_size)

    print(f"Tamanho total do arquivo: {file_size} bytes")
    print(f"Número total de pacotes a serem enviados: {num_pacotes}")
    print(f"Taxa de perda configurada: {loss_rate*100}%")
    print(f"Taxa de erro configurada: {error_rate*100}%")
    print("-" * 50)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # Envia o nome do arquivo primeiro
    client_socket.send(filename.encode('utf-8'))

    total_pacotes_enviados = 0
    pacotes_perdidos = 0
    pacotes_com_erro = 0
    total_bytes_enviados = 0
    seq_number = 0

    with open(filename, 'rb') as file:
        while (chunk := file.read(buffer_size)):
            seq_number += 1
            
            # Simula perda de pacote
            if random.random() < loss_rate:
                pacotes_perdidos += 1
                print(f'[PERDIDO] Pacote {seq_number}/{num_pacotes} não foi enviado')
                continue
            
            # Simula erro no pacote
            if random.random() < error_rate:
                # Corrompe alguns bytes do pacote
                chunk_list = bytearray(chunk)
                num_corrupcoes = random.randint(1, min(5, len(chunk_list)))
                for _ in range(num_corrupcoes):
                    pos = random.randint(0, len(chunk_list) - 1)
                    chunk_list[pos] = random.randint(0, 255)
                chunk = bytes(chunk_list)
                pacotes_com_erro += 1
                print(f'[ERRO] Pacote {seq_number}/{num_pacotes} enviado com dados corrompidos')
            else:
                print(f'[OK] Pacote {seq_number}/{num_pacotes} enviado corretamente')
            
            # Envia cabeçalho (número de sequência) + dados
            header = struct.pack('!I', seq_number)  # 4 bytes para número de sequência
            client_socket.send(header + chunk)
            total_pacotes_enviados += 1
            total_bytes_enviados += len(chunk)

    print("-" * 50)
    print(f'Transferência concluída!')
    print(f'Pacotes processados: {seq_number}')
    print(f'Pacotes enviados: {total_pacotes_enviados}')
    print(f'Pacotes perdidos (simulados): {pacotes_perdidos}')
    print(f'Pacotes com erro (simulados): {pacotes_com_erro}')
    print(f'Tamanho total enviado: {total_bytes_enviados} bytes')

    client_socket.close()

if __name__ == "__main__":
    # Pergunta o IP e caminho do arquivo para o usuário
    ip_cliente = input("Digite o IP do servidor: ")
    caminho_arquivo = input("Digite o caminho completo do arquivo: ")
    
    # Pergunta taxas de perda e erro
    try:
        taxa_perda = float(input("Digite a taxa de perda (0.0 a 1.0, ex: 0.1 para 10%): ") or "0.0")
        taxa_erro = float(input("Digite a taxa de erro (0.0 a 1.0, ex: 0.1 para 10%): ") or "0.0")
    except ValueError:
        print("Valores inválidos! Usando taxas padrão 0.0")
        taxa_perda = 0.0
        taxa_erro = 0.0
    
    send_file(caminho_arquivo, ip_cliente, 12000, buffer_size=128, 
              loss_rate=taxa_perda, error_rate=taxa_erro)
