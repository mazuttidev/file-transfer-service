import socket
import os

def start_server(host, port, buffer_size=1024):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f'Servidor ouvindo em {host}:{port}...')

    conn, addr = server_socket.accept()
    print(f'Conexão estabelecida com {addr}')

    # Recebe o nome do arquivo
    file_name = conn.recv(1024).decode('utf-8')
    print(f'Recebendo arquivo: {file_name}')

    # Cria o arquivo para salvar os dados recebidos
    with open(file_name, 'wb') as file:
        total_pacotes = 0
        total_bytes = 0

        while True:
            data = conn.recv(buffer_size)
            if not data:
                break  # Se não houver mais dados, termina
            file.write(data)
            total_pacotes += 1
            total_bytes += len(data)

    print(f'Arquivo {file_name} recebido com sucesso!')
    print(f'Número total de pacotes: {total_pacotes}')
    print(f'Tamanho total recebido: {total_bytes} bytes')

    conn.close()
    server_socket.close()

if __name__ == "__main__":
    start_server('192.168.101.147', 12000, buffer_size=1024)
