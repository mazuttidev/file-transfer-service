import socket
import struct

def start_server(host, port, buffer_size=1024):
    # Adiciona 4 bytes para o cabeçalho (número de sequência)
    packet_size = buffer_size + 4
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f'Servidor ouvindo em {host}:{port}...')
    print("-" * 50)

    conn, addr = server_socket.accept()
    print(f'Conexão estabelecida com {addr}')

    # Recebe o nome do arquivo
    file_name = conn.recv(1024).decode('utf-8')
    print(f'Recebendo arquivo: {file_name}')
    print("-" * 50)

    # Cria o arquivo para salvar os dados recebidos
    received_sequences = []
    
    with open(file_name, 'wb') as file:
        total_pacotes = 0
        total_bytes = 0

        while True:
            # Recebe o pacote completo (cabeçalho + dados)
            data = conn.recv(packet_size)
            if not data:
                break
            
            # Extrai número de sequência (4 primeiros bytes)
            if len(data) >= 4:
                seq_number = struct.unpack('!I', data[:4])[0]
                payload = data[4:]  # Dados reais do arquivo
                
                received_sequences.append(seq_number)
                file.write(payload)
                total_pacotes += 1
                total_bytes += len(payload)
                print(f'Pacote {seq_number} recebido ({len(payload)} bytes)')

    print("-" * 50)
    print(f'Arquivo {file_name} recebido!')
    print(f'Total de pacotes recebidos: {total_pacotes}')
    print(f'Tamanho total recebido: {total_bytes} bytes')
    
    # Detecta pacotes perdidos
    if received_sequences:
        expected_range = range(1, max(received_sequences) + 1)
        missing = sorted(set(expected_range) - set(received_sequences))
        if missing:
            print(f'Pacotes perdidos detectados: {missing}')
            print(f'Total de pacotes perdidos: {len(missing)}')
        else:
            print('Nenhum pacote perdido detectado')

    conn.close()
    server_socket.close()

if __name__ == "__main__":
    # Pergunta o IP do servidor
    ip_servidor = input("Digite o IP deste servidor: ")
    start_server(ip_servidor, 12000, buffer_size=128)
