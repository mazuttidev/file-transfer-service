import socket
import os
import math

def send_file(filename, host, port, buffer_size=1024):
    print(filename)
    if not os.path.exists(filename):  # Verifica se o arquivo existe
        print(f"Erro: O arquivo {filename} não foi encontrado.")
        return

    # Calcula o número de pacotes a serem enviados
    file_size = os.path.getsize(filename)  # Tamanho do arquivo em bytes
    num_pacotes = math.ceil(file_size / buffer_size)  # Número total de pacotes

    print(f"Tamanho total do arquivo: {file_size} bytes")
    print(f"Número total de pacotes a serem enviados: {num_pacotes}")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # Envia o nome do arquivo primeiro
    client_socket.send(filename.encode('utf-8'))

    total_pacotes_enviados = 0
    total_bytes_enviados = 0

    with open(filename, 'rb') as file:
        while (chunk := file.read(buffer_size)):
            client_socket.send(chunk)
            total_pacotes_enviados += 1
            total_bytes_enviados += len(chunk)
            print(f'Enviado pacote {total_pacotes_enviados}/{num_pacotes} ({total_bytes_enviados} bytes)...')

    print(f'Arquivo enviado com sucesso!')
    print(f'Número total de pacotes enviados: {total_pacotes_enviados}')
    print(f'Tamanho total enviado: {total_bytes_enviados} bytes')

    client_socket.close()

if __name__ == "__main__":
    # Pergunta o IP e caminho do arquivo para o usuário
    ip_cliente = input("Digite o IP do cliente (máquina de envio): ")
    caminho_arquivo = input("Digite o caminho completo do arquivo: ")
    send_file(caminho_arquivo, ip_cliente, 12000, buffer_size=1024)
